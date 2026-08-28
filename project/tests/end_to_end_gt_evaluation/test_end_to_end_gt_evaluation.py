import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, GROUNDED_ANSWERING_RECURSION_LIMIT, RETRIEVAL_EVIDENCE_STORE_FACTS
from src.orchestration import grounded_answering_workflow as workflow
from src.schemas.agent import SearchEvidenceOutput
from src.services.retrieval_service import run_retrieval


CSV_FIELDNAMES = ["question_id", "e2e_success", "tool_calls", "wasted_tool_calls", "rag_gold_recall", "answer_vs_gt", "gather_missing", "decomposition", "citations_vs_gt", "failure_stage", "answer_error_type"]
JSON_COLUMNS = ["tool_calls", "wasted_tool_calls", "rag_gold_recall", "answer_vs_gt", "gather_missing", "decomposition", "citations_vs_gt"]
SUBQUESTION_MATCH_THRESHOLD = 0.4


def json_cell(payload):
    return json.dumps(payload, ensure_ascii=False)


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
    for item in items:
        url = item.get("url") if isinstance(item, dict) else ""
        if url and url not in urls:
            urls.append(url)
    return urls


def gold_urls(ground_truth, bucket_name):
    return unique_urls(ground_truth.get(bucket_name) or [])


def gold_facts(ground_truth):
    facts = []
    for item in ground_truth.get("facts") or []:
        fact = item.get("fact")
        if fact:
            facts.append(fact)
    return facts


def is_unanswerable(ground_truth):
    return "unanswerable" in (ground_truth.get("intents") or [])


def ratio(matched_count, expected_count):
    if not expected_count:
        return 1.0
    return round(matched_count / expected_count, 4)


def load_ground_truth(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    return ground_truth


def dump_answer(answer_result):
    if answer_result is None:
        return {"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}
    if hasattr(answer_result, "model_dump"):
        return answer_result.model_dump()
    return answer_result


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
    if expected in {"yes", "no"}:
        return predicted == expected
    return predicted == expected or bool(expected) and expected in predicted


def fact_found(fact, snippets):
    needle = normalize_text(fact)
    if not needle:
        return False
    for snippet in snippets:
        if not snippet:
            continue
        if needle == snippet or needle in snippet or snippet in needle:
            return True
    return False


def expected_tool_names(ground_truth):
    names = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("expectation") in {"required", "conditional"} and item.get("tool") and item["tool"] not in names:
            names.append(item["tool"])
    return names


def required_tool_names(ground_truth):
    names = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("expectation") == "required" and item.get("tool") and item["tool"] not in names:
            names.append(item["tool"])
    return names


def oracle_queries(ground_truth):
    queries = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("tool") == "search_facts" and item.get("expectation") == "required":
            queries.append(item.get("arguments") or {})
    if queries:
        return queries
    return [{"question": sub_question} for sub_question in ground_truth.get("sub_questions") or []]


def retrieve_facts(question, published_from, published_to):
    task_data = {"question": question, "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH, "evidence_store": RETRIEVAL_EVIDENCE_STORE_FACTS, "published_from": published_from, "published_to": published_to}
    return run_retrieval(task_data, str(uuid4())).get("facts") or []


def oracle_rag_metrics(ground_truth, unanswerable):
    hits = []
    for query in oracle_queries(ground_truth):
        hits.extend(retrieve_facts(query.get("question") or "", query.get("published_from"), query.get("published_to")))
    gold_url_list = gold_urls(ground_truth, "facts")
    gold_fact_list = gold_facts(ground_truth)
    hit_urls = unique_urls(hits)
    snippets = [normalize_text(item.get("snippet") or "") for item in hits]
    if unanswerable:
        return {"unanswerable": 1, "url_recall": "", "snippet_recall": "", "missing_urls": [], "missing_facts": [], "false_positive_url_count": len(hit_urls), "hit_count": len(hits)}
    missing_urls = [url for url in gold_url_list if url not in hit_urls]
    missing_facts = [fact for fact in gold_fact_list if not fact_found(fact, snippets)]
    return {"unanswerable": 0, "url_recall": ratio(len(gold_url_list) - len(missing_urls), len(gold_url_list)), "snippet_recall": ratio(len(gold_fact_list) - len(missing_facts), len(gold_fact_list)), "missing_urls": missing_urls, "missing_facts": missing_facts, "false_positive_url_count": len([url for url in hit_urls if url not in gold_url_list]), "hit_count": len(hits)}


def tool_call_record(tool_call):
    arguments = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
    if not isinstance(arguments, dict):
        arguments = {}
    name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
    call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
    return call_id, {"tool": name, "question": arguments.get("question") or "", "published_from": arguments.get("published_from"), "published_to": arguments.get("published_to")}


def parse_tool_payload(content):
    if isinstance(content, dict):
        return SearchEvidenceOutput.model_validate(content).model_dump()
    return SearchEvidenceOutput.model_validate_json(content).model_dump()


def collect_agent_tool_trace(messages):
    calls = []
    results = []
    result_by_id = {}
    for message in messages:
        for tool_call in getattr(message, "tool_calls", None) or []:
            call_id, record = tool_call_record(tool_call)
            calls.append(record)
            result_slot = {"tool": record["tool"], "question": record["question"], "published_from": record["published_from"], "published_to": record["published_to"], "status": "", "hits": []}
            results.append(result_slot)
            if call_id:
                result_by_id[call_id] = result_slot
        tool_call_id = getattr(message, "tool_call_id", None)
        if tool_call_id and getattr(message, "content", None) and tool_call_id in result_by_id:
            payload = parse_tool_payload(message.content)
            result_by_id[tool_call_id]["status"] = payload.get("status")
            result_by_id[tool_call_id]["hits"] = payload.get("results") or []
    return calls, results


def annotate_gold_hits(results, gold_url_set):
    for result in results:
        gold_hit_count = 0
        for hit in result.get("hits") or []:
            hit["is_gold"] = bool(hit.get("url") and hit["url"] in gold_url_set)
            if hit["is_gold"]:
                gold_hit_count += 1
        result["gold_hit_count"] = gold_hit_count


def compact_calls(results):
    compacted = []
    for result in results:
        compacted.append({"tool": result.get("tool"), "question": result.get("question"), "published_from": result.get("published_from"), "published_to": result.get("published_to"), "status": result.get("status"), "hit_count": len(result.get("hits") or []), "gold_hit_count": result.get("gold_hit_count", 0), "empty": int(not (result.get("hits") or []))})
    return compacted


def required_facts_call_count(ground_truth):
    count = 0
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("tool") == "search_facts" and item.get("expectation") == "required":
            count += 1
    return count


def last_gather_turn(transcript_turns):
    last_gather = {}
    for turn in transcript_turns or []:
        if turn.get("stage") == "gather":
            last_gather = turn
    return last_gather


def gold_is_complete(gold_url_set, collected_gold):
    return bool(gold_url_set) and gold_url_set <= collected_gold


def gold_progress(transcript_turns, gold_url_set):
    progress = []
    collected = set()
    for turn in transcript_turns or []:
        if turn.get("stage") != "tools":
            continue
        new_gold = set(unique_urls(turn.get("evidence") or [])) & gold_url_set
        collected |= new_gold
        progress.append({"tool_count": turn.get("tool_count"), "new_gold_count": len(new_gold), "collected_gold_count": len(collected), "complete": int(gold_is_complete(gold_url_set, collected))})
    return progress, collected


def compact_transcript_turns(transcript_turns):
    turns = []
    for turn in transcript_turns or []:
        if turn.get("stage") == "gather":
            turns.append({"stage": "gather", "gather_count": turn.get("gather_count"), "next_route": turn.get("next_route"), "tool_calls": turn.get("tool_calls") or []})
            continue
        if turn.get("stage") == "tools":
            turns.append({"stage": "tools", "tool_count": turn.get("tool_count"), "tool_calls": turn.get("tool_calls") or [], "hit_count": len(turn.get("evidence") or []), "urls": unique_urls(turn.get("evidence") or [])})
    return turns


def tool_call_pattern(turns):
    batches = [len(turn.get("tool_calls") or []) for turn in turns if turn.get("stage") == "gather" and turn.get("tool_calls")]
    if not batches:
        return "no_tools"
    if len(batches) == 1 and batches[0] > 1:
        return "parallel"
    if all(size == 1 for size in batches):
        return "sequential"
    return "mixed"


def tool_calls_payload(results, transcript_turns, gather_count, tool_count):
    turns = compact_transcript_turns(transcript_turns)
    return {"pattern": tool_call_pattern(turns), "gather_count": gather_count, "tool_count": tool_count, "parallel_batch_sizes": [len(turn.get("tool_calls") or []) for turn in turns if turn.get("stage") == "gather" and turn.get("tool_calls")], "turns": turns, "calls": compact_calls(results)}


def hop_coverage(gt_sub_questions, results):
    hops = []
    used_indexes = set()
    for gt_sub_question in gt_sub_questions:
        best_index = -1
        best_score = 0.0
        for result_index, result in enumerate(results):
            if result_index in used_indexes:
                continue
            score = overlap_score(gt_sub_question, result.get("question") or "")
            if score > best_score:
                best_score = score
                best_index = result_index
        matched = best_index >= 0 and best_score >= SUBQUESTION_MATCH_THRESHOLD
        if matched:
            used_indexes.add(best_index)
        hops.append({"gt_sub_question": gt_sub_question, "attempted": int(matched), "gold_hit_count": results[best_index].get("gold_hit_count", 0) if matched else 0, "agent_query": results[best_index].get("question") if matched else "", "score": round(best_score, 4) if matched else 0.0})
    return hops


def continued_after_gold(progress):
    seen_complete = False
    for item in progress:
        if seen_complete:
            return True
        if item.get("complete"):
            seen_complete = True
    return False


def stop_verdict(unanswerable, gold_url_set, collected_gold, progress, gather_count, tool_count, last_called_tools, results, required_facts_calls):
    budget_forced = gather_count >= GATHER_MAX_LLM_TURNS or tool_count >= GATHER_MAX_TOOL_CALLS
    facts_calls = len([item for item in results if item.get("tool") == "search_facts"])
    if unanswerable:
        if facts_calls == 0 or facts_calls < required_facts_calls:
            return "too_early"
        if facts_calls > required_facts_calls:
            return "too_late"
        if last_called_tools and budget_forced:
            return "budget_forced"
        return "on_time"
    if continued_after_gold(progress) or gold_is_complete(gold_url_set, collected_gold) and last_called_tools:
        return "too_late"
    if gold_is_complete(gold_url_set, collected_gold):
        return "on_time"
    if budget_forced:
        return "budget_forced"
    return "too_early"


def stop_payload(unanswerable, gold_url_set, transcript_turns, gather_count, tool_count, results, required_facts_calls):
    progress, collected = gold_progress(transcript_turns, gold_url_set)
    last_gather = last_gather_turn(transcript_turns)
    last_called_tools = bool(last_gather.get("tool_calls"))
    return {"verdict": stop_verdict(unanswerable, gold_url_set, collected, progress, gather_count, tool_count, last_called_tools, results, required_facts_calls), "gather_count": gather_count, "tool_count": tool_count, "budget_exhausted": int(gather_count >= GATHER_MAX_LLM_TURNS or tool_count >= GATHER_MAX_TOOL_CALLS), "last_gather_called_tools": int(last_called_tools), "last_gather_route": last_gather.get("next_route") or "answer", "gold_complete": int(gold_is_complete(gold_url_set, collected)), "progress": progress}


def match_subquestions(gt_sub_questions, agent_queries):
    unmatched_agent = list(agent_queries)
    unmatched_gt = []
    matched = []
    for gt_sub_question in gt_sub_questions:
        best_query = ""
        best_score = 0.0
        for agent_query in unmatched_agent:
            score = overlap_score(gt_sub_question, agent_query)
            if score > best_score:
                best_score = score
                best_query = agent_query
        if best_score >= SUBQUESTION_MATCH_THRESHOLD and best_query in unmatched_agent:
            unmatched_agent.remove(best_query)
            matched.append({"gt_sub_question": gt_sub_question, "agent_query": best_query, "score": round(best_score, 4)})
            continue
        unmatched_gt.append(gt_sub_question)
    return {"coverage": ratio(len(matched), len(gt_sub_questions)), "gt_sub_questions": gt_sub_questions, "agent_queries": agent_queries, "matched_pairs": matched, "unmatched_gt_sub_questions": unmatched_gt, "extra_agent_queries": unmatched_agent}


def date_filter_payload(ground_truth, calls):
    required_dated = 0
    for item in ground_truth.get("expected_tool_calls") or []:
        arguments = item.get("arguments") or {}
        if item.get("expectation") == "required" and (arguments.get("published_from") or arguments.get("published_to")):
            required_dated += 1
    return {"gt_dated_required_count": required_dated, "agent_dated_call_count": sum(1 for call in calls if call.get("published_from") or call.get("published_to"))}


def decomposition_payload(ground_truth, calls):
    decomposition = match_subquestions(ground_truth.get("sub_questions") or [], [item.get("question") or "" for item in calls])
    required_tools = required_tool_names(ground_truth)
    agent_tools = [item.get("tool") for item in calls]
    missing_required = [name for name in required_tools if name not in agent_tools]
    decomposition["required_tools"] = required_tools
    decomposition["required_tool_coverage"] = ratio(len(required_tools) - len(missing_required), len(required_tools))
    decomposition["missing_required_tools"] = missing_required
    decomposition.update(date_filter_payload(ground_truth, calls))
    return decomposition


def wasted_reason(call_key, seen_keys, collected_gold, gold_url_set, tool_name, allowed_tools, unanswerable):
    if call_key in seen_keys:
        return "duplicate"
    if not unanswerable and gold_url_set and gold_url_set <= collected_gold:
        return "after_gold_complete"
    if tool_name not in allowed_tools:
        return "extra_tool"
    return ""


def wasted_tool_calls(results, gold_url_set, allowed_tools, unanswerable):
    wasted = []
    seen_keys = []
    collected_gold = set()
    for result in results:
        call_key = (result.get("tool"), normalize_text(result.get("question") or ""), result.get("published_from"), result.get("published_to"))
        new_gold = set(unique_urls(result.get("hits") or [])) & gold_url_set
        reason = wasted_reason(call_key, seen_keys, collected_gold, gold_url_set, result.get("tool"), allowed_tools, unanswerable)
        if reason:
            wasted.append({"tool": result.get("tool"), "question": result.get("question"), "reason": reason})
        seen_keys.append(call_key)
        collected_gold |= new_gold
    return wasted


def gather_missing_payload(gold_url_list, gold_fact_list, evidence, unanswerable):
    evidence_urls = unique_urls(evidence)
    snippets = [normalize_text(item.get("snippet") or "") for item in evidence]
    if unanswerable:
        return {"unanswerable": 1, "url_recall": "", "snippet_recall": "", "missing_urls": [], "missing_facts": [], "false_positive_urls": evidence_urls}
    missing_urls = [url for url in gold_url_list if url not in evidence_urls]
    missing_facts = [fact for fact in gold_fact_list if not fact_found(fact, snippets)]
    return {"unanswerable": 0, "url_recall": ratio(len(gold_url_list) - len(missing_urls), len(gold_url_list)), "snippet_recall": ratio(len(gold_fact_list) - len(missing_facts), len(gold_fact_list)), "missing_urls": missing_urls, "missing_facts": missing_facts, "false_positive_urls": [url for url in evidence_urls if url not in gold_url_list]}


def hop_unsatisfied(hops, unanswerable):
    for hop in hops:
        if not hop["attempted"] or (not unanswerable and hop["gold_hit_count"] == 0):
            return 1
    return 0


def gather_payload(gold_url_list, gold_fact_list, evidence, unanswerable, results, ground_truth, transcript_turns, gather_count, tool_count, wasted):
    payload = gather_missing_payload(gold_url_list, gold_fact_list, evidence, unanswerable)
    payload["hops"] = hop_coverage(ground_truth.get("sub_questions") or [], results)
    payload["stop"] = stop_payload(unanswerable, set(gold_url_list), transcript_turns, gather_count, tool_count, results, required_facts_call_count(ground_truth))
    payload["stopped_with_missing_hop"] = hop_unsatisfied(payload["hops"], unanswerable)
    return payload


def compact_citations(citations):
    compacted = []
    for item in citations or []:
        compacted.append({"article_title": item.get("article_title"), "url": item.get("url"), "snippet": item.get("snippet")})
    return compacted


def citation_metrics(ground_truth, answer_result, unanswerable):
    gt_citations = ground_truth.get("citations") or []
    predicted = compact_citations((answer_result or {}).get("citations") or [])
    gt_titles = [item.get("article_title") for item in gt_citations]
    predicted_titles = [item.get("article_title") for item in predicted]
    gt_snippets = [normalize_text(item.get("snippet") or "") for item in gt_citations]
    predicted_snippets = [normalize_text(item.get("snippet") or "") for item in predicted]
    if unanswerable:
        return {"unanswerable": 1, "title_recall": 1.0 if not predicted else 0.0, "snippet_recall": 1.0 if not predicted else 0.0, "gt_citations": compact_citations(gt_citations), "predicted_citations": predicted, "missing_titles": []}
    missing_titles = [title for title in gt_titles if title not in predicted_titles]
    missing_snippets = [item.get("snippet") for item in gt_citations if normalize_text(item.get("snippet") or "") not in predicted_snippets]
    return {"unanswerable": 0, "title_recall": ratio(len(gt_titles) - len(missing_titles), len(gt_titles)), "snippet_recall": ratio(len(gt_snippets) - len(missing_snippets), len(gt_snippets)), "gt_citations": compact_citations(gt_citations), "predicted_citations": predicted, "missing_titles": missing_titles, "missing_snippets": missing_snippets}


def answer_vs_gt_payload(ground_truth, raw_answer, filtered_answer, answer_correct):
    return {"gt_answer": ground_truth.get("answer"), "predicted_answer": (filtered_answer or {}).get("answer") or "", "predicted_status": (filtered_answer or {}).get("status"), "raw_answer": (raw_answer or {}).get("answer") or "", "raw_status": (raw_answer or {}).get("status"), "correct": answer_correct}


def e2e_success_flag(unanswerable, answer_correct, citation_title_recall):
    if not answer_correct:
        return 0
    if unanswerable:
        return 1
    return 1 if citation_title_recall == 1 else 0


def is_partial_recall(value):
    return isinstance(value, (int, float)) and value < 1


def failure_stage(unanswerable, e2e_success, subquestion_coverage, oracle_url_recall, gather_url_recall, answer_correct, citation_recall):
    if e2e_success:
        return "none"
    if unanswerable:
        return "answer"
    if is_partial_recall(oracle_url_recall):
        return "rag"
    if is_partial_recall(gather_url_recall) and is_partial_recall(subquestion_coverage):
        return "decompose"
    if is_partial_recall(gather_url_recall):
        return "gather"
    if not answer_correct:
        return "answer"
    if is_partial_recall(citation_recall):
        return "citation"
    return "e2e"


def answer_error_type(unanswerable, answer_correct, predicted_refusal, raw_answer, filtered_answer, citation_recall, e2e_success):
    if e2e_success:
        return "none"
    if unanswerable and not predicted_refusal:
        return "false_answer"
    if not unanswerable and predicted_refusal:
        if (raw_answer or {}).get("status") == ANSWER_STATUS_ANSWERED and (filtered_answer or {}).get("status") == ANSWER_STATUS_REFUSED:
            return "citation_stripped"
        return "false_refusal"
    if not answer_correct:
        return "wrong_answer"
    if is_partial_recall(citation_recall):
        return "missing_citations"
    return "other"


def capturing_run_answer(original_run_answer, captured):
    def run_answer(task_data, flow_id):
        result = original_run_answer(task_data, flow_id)
        captured["raw_answer"] = result.model_dump()
        return result
    return run_answer


def invoke_question(question_data, flow_id):
    captured = {}
    original_run_answer = workflow.run_answer
    workflow.run_answer = capturing_run_answer(original_run_answer, captured)
    task_data = {"question_id": question_data["id"], "question": question_data["question"], "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}
    try:
        graph_state = workflow.build_grounded_answering_graph(task_data, flow_id).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "prior_queries": [], "sub_questions": [], "gather_count": 0, "tool_count": 0, "grade_verdict": None, "grade_note": None, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT})
    finally:
        workflow.run_answer = original_run_answer
    return {"question_id": question_data["id"], "question": question_data["question"], "flow_id": flow_id, "graph_state": graph_state, "raw_answer": captured.get("raw_answer"), "transcript_turns": task_data.get("transcript_turns") or [], "gather_count": graph_state.get("gather_count", 0), "tool_count": graph_state.get("tool_count", 0)}


def assemble_nested(ground_truth, unanswerable, calls, results, evidence, raw_answer, filtered_answer, oracle, transcript_turns, gather_count, tool_count):
    gold_url_list = gold_urls(ground_truth, "facts")
    annotate_gold_hits(results, set(gold_url_list))
    wasted = wasted_tool_calls(results, set(gold_url_list), expected_tool_names(ground_truth), unanswerable)
    gather = gather_payload(gold_url_list, gold_facts(ground_truth), evidence, unanswerable, results, ground_truth, transcript_turns, gather_count, tool_count, wasted)
    citations = citation_metrics(ground_truth, filtered_answer, unanswerable)
    decomposition = decomposition_payload(ground_truth, calls)
    answer_correct = int(answers_match(filtered_answer, ground_truth.get("answer") or "", unanswerable))
    e2e_success = e2e_success_flag(unanswerable, answer_correct, citations["title_recall"])
    error_type = answer_error_type(unanswerable, answer_correct, is_refusal(filtered_answer), raw_answer, filtered_answer, citations["title_recall"], e2e_success)
    stage = failure_stage(unanswerable, e2e_success, decomposition["coverage"], oracle.get("url_recall"), gather.get("url_recall"), answer_correct, citations["title_recall"])
    return {"question_id": ground_truth["id"], "e2e_success": e2e_success, "tool_calls": tool_calls_payload(results, transcript_turns, gather_count, tool_count), "wasted_tool_calls": wasted, "rag_gold_recall": oracle, "answer_vs_gt": answer_vs_gt_payload(ground_truth, raw_answer, filtered_answer, answer_correct), "gather_missing": gather, "decomposition": decomposition, "citations_vs_gt": citations, "failure_stage": stage, "answer_error_type": error_type}


def error_nested(question_id, error_text):
    empty_metrics = {"error": error_text}
    empty_tools = {"pattern": "no_tools", "gather_count": 0, "tool_count": 0, "parallel_batch_sizes": [], "turns": [], "calls": []}
    return {"question_id": question_id, "e2e_success": 0, "tool_calls": empty_tools, "wasted_tool_calls": [], "rag_gold_recall": empty_metrics, "answer_vs_gt": empty_metrics, "gather_missing": empty_metrics, "decomposition": empty_metrics, "citations_vs_gt": empty_metrics, "failure_stage": "runtime_error", "answer_error_type": "runtime_error"}


def score_run(ground_truth, run_result):
    unanswerable = is_unanswerable(ground_truth)
    calls, results = collect_agent_tool_trace(run_result["graph_state"]["messages"])
    evidence = run_result["graph_state"].get("evidence") or []
    filtered_answer = dump_answer(run_result["graph_state"].get("answer_result"))
    raw_answer = run_result.get("raw_answer") or filtered_answer
    return assemble_nested(ground_truth, unanswerable, calls, results, evidence, raw_answer, filtered_answer, oracle_rag_metrics(ground_truth, unanswerable), run_result.get("transcript_turns") or [], run_result.get("gather_count", 0), run_result.get("tool_count", 0))


def evaluate_one(project_root, question_data):
    ground_truth = load_ground_truth(project_root, question_data)
    try:
        return score_run(ground_truth, invoke_question(question_data, str(uuid4())))
    except Exception as err:
        return error_nested(question_data["id"], repr(err))


def csv_row_from_nested(nested):
    row = {}
    for field_name in CSV_FIELDNAMES:
        value = nested[field_name]
        if field_name in JSON_COLUMNS:
            row[field_name] = json_cell(value)
            continue
        row[field_name] = value
    return row


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_traces(path, traces):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")


def selected_questions(questions):
    if "--smoke" in sys.argv:
        return [item for item in questions if item["id"] == "Q01"]
    return questions


def run_end_to_end_gt_evaluation(project_root, questions):
    traces = []
    for question_data in questions:
        traces.append(evaluate_one(project_root, question_data))
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(__file__).resolve().parent / "outputs"
    write_csv(output_dir / f"stage_eval_{timestamp}.csv", [csv_row_from_nested(item) for item in traces])
    write_traces(output_dir / f"traces_{timestamp}.json", traces)


def main():
    project_root = Path(__file__).resolve().parents[2]
    run_end_to_end_gt_evaluation(project_root, selected_questions(json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
