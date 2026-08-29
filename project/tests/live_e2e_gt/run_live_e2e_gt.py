import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from observability.logging_dashboard.build_dashboard import build_dashboard
from src.conts import ANSWER_STATUS_REFUSED, DATA_DIR, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, LOG_FILE_PATH, TELEMETRY_DIRECTORY_PATH, TELEMETRY_FILE_PREFIX, TELEMETRY_FLOW_ID_ATTRIBUTE, TELEMETRY_WORKFLOW_NAME, TELEMETRY_WORKFLOW_OPERATION_NAME


CSV_FIELDNAMES = ["question_id", "http_status", "flow_id", "trace_id", "task_success", "failure_agent", "gather_success", "retrieve_success", "retrieval_success", "grade_success", "answer_success", "citation_success", "orchestration_success", "gold_url_recall_pct", "gold_snippet_recall_pct", "citation_title_recall_pct", "hop_coverage_pct", "source_fill_pct", "date_fill_pct", "wasted_call_pct", "stop_verdict", "answer_error_type", "gather_turns", "tool_count", "span_count", "duration_ms", "gt_answer", "predicted_answer", "missing_urls", "runtime_error"]
SUBQUESTION_MATCH_THRESHOLD = 0.4
WORKFLOW_SPAN_NAME = f"{TELEMETRY_WORKFLOW_OPERATION_NAME} {TELEMETRY_WORKFLOW_NAME}"
WORKFLOW_LOG_PROCESS = "execute_grounded_answering"


def percent(matched_count, expected_count, empty_is_full):
    if empty_is_full or not expected_count:
        return 100.0
    return round(100.0 * matched_count / expected_count, 2)


def flag_percent(passed):
    return 100.0 if passed else 0.0


def normalize_text(text):
    return " ".join((text or "").lower().split())


def normalize_answer(text):
    return normalize_text(text).strip(" .!?,;:'\"")


def tokens(text):
    cleaned_words = ["".join(character for character in raw_word if character.isalnum()) for raw_word in normalize_text(text).split()]
    return [word for word in cleaned_words if len(word) >= 2]


def overlap_score(left_text, right_text):
    left_tokens = tokens(left_text)
    right_tokens = tokens(right_text)
    if not left_tokens or not right_tokens:
        return 0.0
    left_set = set(left_tokens)
    right_set = set(right_tokens)
    intersection = left_set & right_set
    jaccard = len(intersection) / len(left_set | right_set)
    coverage = len(intersection) / len(left_set)
    if jaccard > coverage:
        return jaccard
    return coverage


def unique_urls(items):
    urls = []
    for item in items or []:
        url = item.get("url") if isinstance(item, dict) else ""
        if url and url not in urls:
            urls.append(url)
    return urls


def load_ground_truth(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    return ground_truth


def is_unanswerable(ground_truth):
    return "unanswerable" in (ground_truth.get("intents") or [])


def gold_fact_items(ground_truth):
    items = []
    for item in ground_truth.get("facts") or []:
        if item.get("url") or item.get("fact"):
            items.append(item)
    return items


def required_retrieve_calls(ground_truth):
    calls = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("agent") == "retrieve" and item.get("tool") == "search_facts" and item.get("expectation") == "required":
            calls.append(item)
    return calls


def snippet_matches(gold_fact, snippet):
    needle = normalize_text(gold_fact)
    haystack = normalize_text(snippet)
    if not needle or not haystack:
        return False
    return needle == haystack or needle in haystack or haystack in needle


def any_snippet_match(gold_fact, snippets):
    for snippet in snippets:
        if snippet_matches(gold_fact, snippet):
            return True
    return False


def is_refusal(answer_result):
    if (answer_result or {}).get("status") == ANSWER_STATUS_REFUSED:
        return True
    normalized = normalize_answer((answer_result or {}).get("answer") or "")
    if not normalized:
        return True
    return "insufficient information" in normalized


def answers_match(answer_result, expected_answer, unanswerable):
    predicted_refusal = is_refusal(answer_result)
    if unanswerable:
        return predicted_refusal
    if predicted_refusal:
        return False
    predicted = normalize_answer(answer_result.get("answer") or "")
    expected = normalize_answer(expected_answer)
    return predicted == expected or bool(expected) and expected in predicted


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def flatten_spans(payload):
    spans = []
    for resource_span in payload.get("resourceSpans") or []:
        for scope_span in resource_span.get("scopeSpans") or []:
            for span in scope_span.get("spans") or []:
                spans.append(span)
    return spans


def otel_attribute_value(attribute):
    value = attribute.get("value") or {}
    if "stringValue" in value:
        return value.get("stringValue") or ""
    if "intValue" in value:
        return str(value.get("intValue"))
    return ""


def span_flow_id(span):
    for attribute in span.get("attributes") or []:
        if attribute.get("key") == TELEMETRY_FLOW_ID_ATTRIBUTE:
            return otel_attribute_value(attribute)
    return ""


def load_new_spans(existing_names):
    spans = []
    for path in sorted(Path(TELEMETRY_DIRECTORY_PATH).glob(f"{TELEMETRY_FILE_PREFIX}-*.jsonl")):
        if path.name in existing_names:
            continue
        for payload in load_jsonl(path):
            spans.extend(flatten_spans(payload))
    return spans


def spans_for_flow(spans, flow_id):
    matched = []
    for span in spans:
        if span_flow_id(span) == flow_id:
            matched.append(span)
    return matched


def workflow_duration_ms(spans):
    for span in spans:
        if span.get("name") != WORKFLOW_SPAN_NAME:
            continue
        start = int(span.get("startTimeUnixNano") or 0)
        end = int(span.get("endTimeUnixNano") or 0)
        if end > start:
            return round((end - start) / 1_000_000, 2)
    return ""


def flatten_calls(transcript_turns):
    calls = []
    for turn in transcript_turns or []:
        if turn.get("stage") != "retrieve":
            continue
        for tool_call in turn.get("tool_calls") or []:
            arguments = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}
            calls.append({"tool": tool_call.get("name") or "", "question": arguments.get("question") or "", "source": arguments.get("source") or "", "published_from": arguments.get("published_from") or "", "published_to": arguments.get("published_to") or ""})
    return calls


def match_required_calls(gt_calls, agent_calls):
    used = set()
    pairs = []
    for gt_call in gt_calls:
        best_index = -1
        best_score = 0.0
        gt_question = (gt_call.get("arguments") or {}).get("question") or ""
        for agent_index, agent_call in enumerate(agent_calls):
            if agent_index in used:
                continue
            score = overlap_score(gt_question, agent_call.get("question") or "")
            if score > best_score:
                best_score = score
                best_index = agent_index
        if best_index >= 0 and best_score >= SUBQUESTION_MATCH_THRESHOLD:
            used.add(best_index)
            pairs.append((gt_call, agent_calls[best_index]))
            continue
        pairs.append((gt_call, None))
    return pairs


def fill_percent(pairs, required_key):
    required_count = 0
    filled_count = 0
    for gt_call, agent_call in pairs:
        arguments = gt_call.get("arguments") or {}
        if required_key == "source" and not arguments.get("source"):
            continue
        if required_key == "dates" and not (arguments.get("published_from") or arguments.get("published_to")):
            continue
        required_count += 1
        if not agent_call:
            continue
        if required_key == "source" and agent_call.get("source"):
            filled_count += 1
        if required_key == "dates" and agent_call.get("published_from") and agent_call.get("published_to"):
            filled_count += 1
    return percent(filled_count, required_count, False)


def hop_coverage_pct(gt_sub_questions, agent_calls):
    used = set()
    matched = 0
    for gt_sub_question in gt_sub_questions or []:
        best_index = -1
        best_score = 0.0
        for agent_index, agent_call in enumerate(agent_calls):
            if agent_index in used:
                continue
            score = overlap_score(gt_sub_question, agent_call.get("question") or "")
            if score > best_score:
                best_score = score
                best_index = agent_index
        if best_index >= 0 and best_score >= SUBQUESTION_MATCH_THRESHOLD:
            used.add(best_index)
            matched += 1
    return percent(matched, len(gt_sub_questions or []), False)


def wasted_call_pct(agent_calls):
    if not agent_calls:
        return 0.0
    seen = []
    wasted = 0
    for call in agent_calls:
        key = (normalize_text(call.get("question") or ""), call.get("source") or "", call.get("published_from") or "", call.get("published_to") or "")
        if key in seen:
            wasted += 1
        seen.append(key)
    return round(100.0 * wasted / len(agent_calls), 2)


def gold_progress(transcript_turns, gold_url_set):
    progress = []
    collected = set()
    for turn in transcript_turns or []:
        if turn.get("stage") != "tools":
            continue
        collected |= set(unique_urls(turn.get("evidence") or [])) & gold_url_set
        progress.append(int(bool(gold_url_set) and gold_url_set <= collected))
    return progress, collected


def continued_after_gold(progress):
    seen_complete = False
    for complete in progress:
        if seen_complete:
            return True
        if complete:
            seen_complete = True
    return False


def stop_verdict(unanswerable, gold_url_set, collected, progress, gather_count, tool_count, facts_calls, required_facts):
    budget_forced = gather_count >= GATHER_MAX_LLM_TURNS or tool_count >= GATHER_MAX_TOOL_CALLS
    if unanswerable:
        if facts_calls < required_facts:
            return "too_early"
        if facts_calls > required_facts:
            return "too_late"
        if budget_forced:
            return "budget_forced"
        return "on_time"
    if continued_after_gold(progress):
        return "too_late"
    if gold_url_set and gold_url_set <= collected:
        return "on_time"
    if budget_forced:
        return "budget_forced"
    return "too_early"


def citation_title_recall_pct(ground_truth, answer_result, unanswerable):
    gt_titles = [item.get("article_title") for item in ground_truth.get("citations") or [] if item.get("article_title")]
    predicted_titles = [item.get("article_title") for item in (answer_result or {}).get("citations") or []]
    if unanswerable:
        return 100.0
    missing = 0
    for title in gt_titles:
        if title not in predicted_titles:
            missing += 1
    return percent(len(gt_titles) - missing, len(gt_titles), False)


def gold_metrics(ground_truth, evidence, unanswerable):
    gold_items = gold_fact_items(ground_truth)
    gold_url_list = unique_urls(gold_items)
    evidence_urls = unique_urls(evidence)
    missing_urls = []
    for url in gold_url_list:
        if url not in evidence_urls:
            missing_urls.append(url)
    snippets = []
    for entry in evidence:
        snippets.append(entry.get("snippet") or "")
    missing_facts = []
    for item in gold_items:
        if not any_snippet_match(item.get("fact") or "", snippets):
            missing_facts.append(item)
    url_recall = percent(len(gold_url_list) - len(missing_urls), len(gold_url_list), unanswerable)
    snippet_recall = percent(len(gold_items) - len(missing_facts), len(gold_items), unanswerable)
    gold_complete = True if unanswerable else bool(gold_url_list) and set(gold_url_list) <= set(evidence_urls) and not missing_facts
    return url_recall, snippet_recall, gold_complete, missing_urls, set(gold_url_list)


def gather_success_value(unanswerable, gold_complete, hop_coverage, source_fill):
    if unanswerable:
        return flag_percent(source_fill == 100)
    if gold_complete:
        return 100.0
    return flag_percent(hop_coverage == 100)


def retrieve_success_value(source_fill, date_fill, facts_call_count, required_count):
    if facts_call_count < required_count:
        return 0.0
    if source_fill < 100 or date_fill < 100:
        return 0.0
    return 100.0


def answer_error_type(unanswerable, answer_correct, predicted_refusal, citation_recall, task_success):
    if task_success == 100:
        return "none"
    if unanswerable and not predicted_refusal:
        return "false_answer"
    if not unanswerable and predicted_refusal:
        return "false_refusal"
    if not answer_correct:
        return "wrong_answer"
    if citation_recall < 100:
        return "missing_citations"
    return "other"


def failure_agent(row):
    if row["task_success"] == 100:
        return "none"
    if row["runtime_error"]:
        return "runtime"
    if row["gather_success"] != 100:
        return "gather"
    if row["retrieve_success"] != 100:
        return "retrieve"
    if row["retrieval_success"] != 100:
        return "retrieval"
    if row["grade_success"] != 100:
        return "grade"
    if row["answer_success"] != 100:
        return "answer"
    if row["citation_success"] != 100:
        return "citation"
    return "orchestration"


def content_question(content):
    if not isinstance(content, dict):
        return ""
    if content.get("question"):
        return content.get("question")
    task_data = content.get("task_data")
    if isinstance(task_data, dict):
        return task_data.get("question") or ""
    return ""


def workflow_for_question(events, question):
    finished = {}
    error_text = ""
    flow_id = ""
    for item in events:
        event = item.get("event") or {}
        if event.get("process") != WORKFLOW_LOG_PROCESS or content_question(event.get("content") or {}) != question:
            continue
        flow_id = event.get("flow_id") or flow_id
        if event.get("status") == "FINISHED":
            finished = event.get("content") or {}
        if event.get("status") == "ERROR":
            error_text = str((event.get("content") or {}).get("error") or "")
    return finished, error_text, flow_id


def run_solution(questions):
    from solution import answer, build_index
    index = build_index(DATA_DIR)
    results = []
    for question_data in questions:
        try:
            results.append({"id": question_data["id"], "public": answer(index, question_data["id"], question_data["question"]), "runtime_error": ""})
        except Exception as err:
            results.append({"id": question_data["id"], "public": {}, "runtime_error": repr(err)})
    return results


def empty_row(question_id, ground_truth, http_status, flow_id, trace_id, runtime_error):
    return {"question_id": question_id, "http_status": http_status, "flow_id": flow_id, "trace_id": trace_id, "task_success": 0.0, "failure_agent": "runtime", "gather_success": 0.0, "retrieve_success": 0.0, "retrieval_success": 0.0, "grade_success": 0.0, "answer_success": 0.0, "citation_success": 0.0, "orchestration_success": 0.0, "gold_url_recall_pct": 0.0, "gold_snippet_recall_pct": 0.0, "citation_title_recall_pct": 0.0, "hop_coverage_pct": 0.0, "source_fill_pct": 0.0, "date_fill_pct": 0.0, "wasted_call_pct": 0.0, "stop_verdict": "", "answer_error_type": "runtime_error", "gather_turns": 0, "tool_count": 0, "span_count": 0, "duration_ms": "", "gt_answer": ground_truth.get("answer") or "", "predicted_answer": "", "missing_urls": " | ".join(unique_urls(gold_fact_items(ground_truth))), "runtime_error": runtime_error}


def score_question(question_id, ground_truth, http_status, flow_id, trace_id, http_answer, log_content, spans, runtime_error):
    unanswerable = is_unanswerable(ground_truth)
    agent_calls = flatten_calls(log_content.get("transcript_turns") or [])
    required_count = len(required_retrieve_calls(ground_truth))
    pairs = match_required_calls(required_retrieve_calls(ground_truth), agent_calls)
    url_recall, snippet_recall, gold_complete, missing_urls, gold_url_set = gold_metrics(ground_truth, log_content.get("evidence") or [], unanswerable)
    source_fill = fill_percent(pairs, "source")
    date_fill = fill_percent(pairs, "dates")
    hop_coverage = hop_coverage_pct(ground_truth.get("sub_questions") or [], agent_calls)
    answer_result = http_answer or log_content.get("answer_result") or {}
    answer_correct = answers_match(answer_result, ground_truth.get("answer") or "", unanswerable)
    citation_recall = citation_title_recall_pct(ground_truth, answer_result, unanswerable)
    progress, collected = gold_progress(log_content.get("transcript_turns") or [], gold_url_set)
    gather_count = log_content.get("gather_count") or 0
    tool_count = log_content.get("tool_count") or 0
    verdict = stop_verdict(unanswerable, gold_url_set, collected, progress, gather_count, tool_count, len(agent_calls), required_count)
    task_success = flag_percent(not runtime_error and answer_correct and (unanswerable or citation_recall == 100))
    row = {"question_id": question_id, "http_status": http_status, "flow_id": flow_id, "trace_id": trace_id or log_content.get("trace_id") or "", "task_success": task_success, "gather_success": gather_success_value(unanswerable, gold_complete, hop_coverage, source_fill), "retrieve_success": retrieve_success_value(source_fill, date_fill, len(agent_calls), required_count), "retrieval_success": flag_percent(url_recall == 100 and snippet_recall == 100), "grade_success": flag_percent(verdict == "on_time"), "answer_success": flag_percent(answer_correct), "citation_success": flag_percent(citation_recall == 100), "orchestration_success": flag_percent(not runtime_error), "gold_url_recall_pct": url_recall, "gold_snippet_recall_pct": snippet_recall, "citation_title_recall_pct": citation_recall, "hop_coverage_pct": hop_coverage, "source_fill_pct": source_fill, "date_fill_pct": date_fill, "wasted_call_pct": wasted_call_pct(agent_calls), "stop_verdict": verdict, "answer_error_type": answer_error_type(unanswerable, answer_correct, is_refusal(answer_result), citation_recall, task_success), "gather_turns": gather_count, "tool_count": tool_count, "span_count": len(spans), "duration_ms": workflow_duration_ms(spans), "gt_answer": ground_truth.get("answer") or "", "predicted_answer": (answer_result or {}).get("answer") or "", "missing_urls": " | ".join(missing_urls), "runtime_error": runtime_error}
    row["failure_agent"] = failure_agent(row)
    return row


def evaluate_question(project_root, question_data, result, events, all_spans):
    ground_truth = load_ground_truth(project_root, question_data)
    public = (result or {}).get("public") or {}
    try:
        log_content, log_error, flow_id = workflow_for_question(events, question_data["question"])
        runtime_error = (result or {}).get("runtime_error") or log_error
        spans = spans_for_flow(all_spans, flow_id)
        if runtime_error:
            return empty_row(question_data["id"], ground_truth, "", flow_id, log_content.get("trace_id") or "", runtime_error)
        return score_question(question_data["id"], ground_truth, "", flow_id, log_content.get("trace_id") or "", public, log_content, spans, runtime_error)
    except Exception as err:
        return empty_row(question_data["id"], ground_truth, "", "", "", repr(err))


def evaluate_all(project_root, questions, results, events, all_spans):
    by_id = {}
    for result in results or []:
        by_id[result.get("id")] = result
    rows = []
    for question_data in questions:
        rows.append(evaluate_question(project_root, question_data, by_id.get(question_data["id"]) or {}, events, all_spans))
    return rows


def mean_pct(rows, field_name):
    values = [row[field_name] for row in rows if row[field_name] != ""]
    if not values:
        return ""
    return round(sum(values) / len(values), 2)


def total_row(rows):
    return {"question_id": "TOTAL", "http_status": "", "flow_id": "", "trace_id": "", "task_success": mean_pct(rows, "task_success"), "failure_agent": "", "gather_success": mean_pct(rows, "gather_success"), "retrieve_success": mean_pct(rows, "retrieve_success"), "retrieval_success": mean_pct(rows, "retrieval_success"), "grade_success": mean_pct(rows, "grade_success"), "answer_success": mean_pct(rows, "answer_success"), "citation_success": mean_pct(rows, "citation_success"), "orchestration_success": mean_pct(rows, "orchestration_success"), "gold_url_recall_pct": mean_pct(rows, "gold_url_recall_pct"), "gold_snippet_recall_pct": mean_pct(rows, "gold_snippet_recall_pct"), "citation_title_recall_pct": mean_pct(rows, "citation_title_recall_pct"), "hop_coverage_pct": mean_pct(rows, "hop_coverage_pct"), "source_fill_pct": mean_pct(rows, "source_fill_pct"), "date_fill_pct": mean_pct(rows, "date_fill_pct"), "wasted_call_pct": mean_pct(rows, "wasted_call_pct"), "stop_verdict": "", "answer_error_type": "", "gather_turns": mean_pct(rows, "gather_turns"), "tool_count": mean_pct(rows, "tool_count"), "span_count": mean_pct(rows, "span_count"), "duration_ms": mean_pct(rows, "duration_ms"), "gt_answer": "", "predicted_answer": "", "missing_urls": "", "runtime_error": ""}


def csv_row(row):
    output = {}
    for field_name in CSV_FIELDNAMES:
        output[field_name] = row.get(field_name)
    return output


def write_metrics(output_directory, rows):
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / f"metrics_{datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows([csv_row(row) for row in rows] + [total_row(rows)])


def selected_questions(questions):
    if "--smoke" in sys.argv:
        return [item for item in questions if item["id"] == "Q01"]
    return questions


def existing_span_names():
    names = set()
    for path in Path(TELEMETRY_DIRECTORY_PATH).glob(f"{TELEMETRY_FILE_PREFIX}-*.jsonl"):
        names.add(path.name)
    return names


def main():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    os.environ["OTEL_SDK_DISABLED"] = "false"
    span_names = existing_span_names()
    questions = selected_questions(json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8")))
    results = run_solution(questions)
    rows = evaluate_all(project_root, questions, results, load_jsonl(Path(LOG_FILE_PATH)), load_new_spans(span_names))
    write_metrics(Path(__file__).resolve().parent / "outputs", rows)
    build_dashboard()


if __name__ == "__main__":
    main()
