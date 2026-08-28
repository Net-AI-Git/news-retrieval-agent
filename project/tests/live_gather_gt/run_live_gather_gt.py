import csv
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.agents.retrieve_agent import build_retrieve_tools
from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, GROUNDED_ANSWERING_RECURSION_LIMIT
from src.orchestration.grounded_answering_workflow import GroundedAnsweringState, gather_node, grade_node, retrieve_node, route_after_gather, route_after_grade, route_after_retrieve, tools_node


METRIC_FIELDNAMES = ["question_id", "unanswerable", "required_facts_calls", "facts_call_count", "gold_url_count", "url_recall", "snippet_recall", "gold_complete", "stop_verdict", "gather_count", "tool_count", "gt_dated_required_count", "agent_dated_call_count", "gt_source_required_count", "agent_source_call_count", "extra_turn_after_gold", "prompt_leak_hit", "gather_success", "missing_urls", "missing_titles", "agent_queries", "runtime_error"]
HOP_FIELDNAMES = ["question_id", "hop_index", "gold_title", "gold_url", "url_in_evidence", "snippet_in_evidence"]
CALL_FIELDNAMES = ["question_id", "call_index", "gather_turn", "question", "source", "published_from", "published_to"]
LIVE_GATHER_PAUSE_SECONDS = 8
LEAK_SKIP_ANSWERS = {"yes", "no", "insufficient information"}
LEAK_MIN_CHARS = 24


def add_exam_needle(needles, text):
    value = " ".join((text or "").split())
    if len(value) < LEAK_MIN_CHARS or value.lower() in LEAK_SKIP_ANSWERS:
        return
    if value not in needles:
        needles.append(value)


def exam_needles_from_ground_truth(question_data, ground_truth):
    needles = []
    add_exam_needle(needles, question_data.get("question"))
    add_exam_needle(needles, ground_truth.get("answer"))
    for item in (ground_truth.get("facts") or []) + (ground_truth.get("citations") or []):
        add_exam_needle(needles, item.get("fact") or item.get("snippet"))
        add_exam_needle(needles, item.get("article_title"))
        add_exam_needle(needles, item.get("url"))
    for sub_question in ground_truth.get("sub_questions") or []:
        add_exam_needle(needles, sub_question)
    for call in ground_truth.get("expected_tool_calls") or []:
        add_exam_needle(needles, (call.get("arguments") or {}).get("question"))
    return needles


def collect_exam_needles(project_root, questions):
    needles = []
    for question_data in questions:
        for needle in exam_needles_from_ground_truth(question_data, load_ground_truth(project_root, question_data)):
            add_exam_needle(needles, needle)
    return needles


def prompt_leak_hit(prompt_text, needles):
    for needle in needles:
        if needle in prompt_text:
            return 1
    return 0


def normalize_text(text):
    return " ".join((text or "").lower().split())


def snippet_matches(gold_fact, snippet):
    needle = normalize_text(gold_fact)
    haystack = normalize_text(snippet)
    if not needle or not haystack:
        return False
    return needle == haystack or needle in haystack or haystack in needle


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


def required_facts_calls(ground_truth):
    calls = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("tool") == "search_facts" and item.get("expectation") == "required":
            calls.append(item)
    return calls


def gold_items(ground_truth):
    items = []
    for item in ground_truth.get("facts") or []:
        if item.get("url") or item.get("fact"):
            items.append(item)
    return items


def filter_counts(calls):
    dated_count = 0
    source_count = 0
    for call in calls:
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else call
        if arguments.get("published_from") or arguments.get("published_to"):
            dated_count += 1
        if arguments.get("source"):
            source_count += 1
    return dated_count, source_count


def build_gather_only_graph(task_data, flow_id):
    tool_node = ToolNode(build_retrieve_tools(task_data, flow_id))
    graph = StateGraph(GroundedAnsweringState)
    graph.add_node("gather", lambda state: gather_node(state, task_data, flow_id))
    graph.add_node("retrieve", lambda state: retrieve_node(state, task_data, flow_id))
    graph.add_node("tools", lambda state: tools_node(state, tool_node, task_data, flow_id))
    graph.add_node("grade", lambda state: grade_node(state, task_data, flow_id))
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", route_after_gather, {"retrieve": "retrieve", "answer": END})
    graph.add_conditional_edges("retrieve", route_after_retrieve, {"tools": "tools", "answer": END})
    graph.add_edge("tools", "grade")
    graph.add_conditional_edges("grade", route_after_grade, {"gather": "gather", "answer": END})
    return graph.compile()


def run_gather_only(question):
    task_data = {"question": question, "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}
    graph_state = build_gather_only_graph(task_data, str(uuid4())).invoke({"question": question, "messages": [HumanMessage(question)], "evidence": [], "prior_queries": [], "sub_questions": [], "gather_count": 0, "tool_count": 0, "grade_verdict": None, "grade_note": None, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT})
    return task_data, graph_state


def call_arguments(tool_call):
    arguments = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
    if not isinstance(arguments, dict):
        arguments = {}
    name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
    return {"tool": name or "", "question": arguments.get("question") or "", "source": arguments.get("source") or "", "published_from": arguments.get("published_from") or "", "published_to": arguments.get("published_to") or ""}


def flatten_calls(transcript_turns):
    calls = []
    for turn in transcript_turns or []:
        if turn.get("stage") != "retrieve":
            continue
        for tool_call in turn.get("tool_calls") or []:
            record = call_arguments(tool_call)
            record["gather_turn"] = turn.get("gather_count") or 0
            calls.append(record)
    return calls


def extra_tools_turn_after_gold(transcript_turns, gold_url_set):
    collected = set()
    gold_already_complete = False
    for turn in transcript_turns or []:
        if turn.get("stage") == "retrieve" and gold_already_complete and (turn.get("tool_calls") or []):
            return True
        if turn.get("stage") != "tools":
            continue
        collected |= set(unique_urls(turn.get("evidence") or [])) & gold_url_set
        if gold_url_set and gold_url_set <= collected:
            gold_already_complete = True
    return False


def any_snippet_match(gold_fact, snippets):
    for snippet in snippets:
        if snippet_matches(gold_fact, snippet):
            return True
    return False


def missing_gold_facts(gold_fact_items, evidence):
    missing = []
    snippets = []
    for item in evidence or []:
        snippets.append(item.get("snippet") or "")
    for gold_item in gold_fact_items:
        if not any_snippet_match(gold_item.get("fact") or "", snippets):
            missing.append(gold_item)
    return missing


def recall_ratio(matched_count, expected_count, unanswerable):
    if unanswerable or not expected_count:
        return 1.0
    return round(matched_count / expected_count, 4)


def stop_verdict(unanswerable, gold_complete, extra_turn, facts_call_count, required_count, gather_count, tool_count):
    budget_forced = gather_count >= GATHER_MAX_LLM_TURNS or tool_count >= GATHER_MAX_TOOL_CALLS
    if unanswerable:
        if facts_call_count < required_count:
            if budget_forced:
                return "budget_forced"
            return "too_early"
        if facts_call_count > required_count:
            return "too_late"
        return "on_time"
    if extra_turn:
        return "too_late"
    if gold_complete:
        return "on_time"
    if budget_forced:
        return "budget_forced"
    return "too_early"


def gather_success(unanswerable, gold_complete, snippet_recall, verdict, facts_call_count, required_count, leak_hit):
    if leak_hit:
        return 0
    if unanswerable:
        return int(facts_call_count == required_count and verdict == "on_time")
    return int(gold_complete and snippet_recall == 1.0 and verdict == "on_time")


def empty_score(question_id, ground_truth, leak_hit, runtime_error):
    unanswerable = int("unanswerable" in (ground_truth.get("intents") or []))
    required_count = len(required_facts_calls(ground_truth))
    dated_required, source_required = filter_counts(required_facts_calls(ground_truth))
    return {"question_id": question_id, "unanswerable": unanswerable, "required_facts_calls": required_count, "facts_call_count": 0, "gold_url_count": len(unique_urls(gold_items(ground_truth))), "url_recall": 0.0 if not unanswerable else 1.0, "snippet_recall": 0.0 if not unanswerable else 1.0, "gold_complete": 0, "stop_verdict": "runtime_error", "gather_count": 0, "tool_count": 0, "gt_dated_required_count": dated_required, "agent_dated_call_count": 0, "gt_source_required_count": source_required, "agent_source_call_count": 0, "extra_turn_after_gold": 0, "prompt_leak_hit": leak_hit, "gather_success": 0, "missing_urls": unique_urls(gold_items(ground_truth)), "missing_titles": [item.get("article_title") or "" for item in gold_items(ground_truth)], "agent_queries": [], "runtime_error": runtime_error, "evidence": [], "calls": [], "gold_fact_items": gold_items(ground_truth)}


def score_question(question_id, ground_truth, task_data, graph_state, leak_hit):
    unanswerable = int("unanswerable" in (ground_truth.get("intents") or []))
    gold_fact_items = gold_items(ground_truth)
    gold_url_list = unique_urls(gold_fact_items)
    gold_url_set = set(gold_url_list)
    evidence = graph_state.get("evidence") or []
    calls = flatten_calls(task_data.get("transcript_turns") or [])
    evidence_urls = unique_urls(evidence)
    missing_urls = [url for url in gold_url_list if url not in evidence_urls]
    missing_facts = missing_gold_facts(gold_fact_items, evidence)
    required_count = len(required_facts_calls(ground_truth))
    dated_required, source_required = filter_counts(required_facts_calls(ground_truth))
    dated_agent, source_agent = filter_counts(calls)
    extra_turn = int(extra_tools_turn_after_gold(task_data.get("transcript_turns") or [], gold_url_set))
    gold_complete = int(bool(gold_url_set) and gold_url_set <= set(evidence_urls))
    url_recall = recall_ratio(len(gold_url_list) - len(missing_urls), len(gold_url_list), unanswerable)
    snippet_recall = recall_ratio(len(gold_fact_items) - len(missing_facts), len(gold_fact_items), unanswerable)
    gather_count = graph_state.get("gather_count") or 0
    tool_count = graph_state.get("tool_count") or 0
    verdict = stop_verdict(unanswerable, gold_complete, extra_turn, len(calls), required_count, gather_count, tool_count)
    return {"question_id": question_id, "unanswerable": unanswerable, "required_facts_calls": required_count, "facts_call_count": len(calls), "gold_url_count": len(gold_url_list), "url_recall": url_recall, "snippet_recall": snippet_recall, "gold_complete": gold_complete if not unanswerable else 1, "stop_verdict": verdict, "gather_count": gather_count, "tool_count": tool_count, "gt_dated_required_count": dated_required, "agent_dated_call_count": dated_agent, "gt_source_required_count": source_required, "agent_source_call_count": source_agent, "extra_turn_after_gold": extra_turn, "prompt_leak_hit": leak_hit, "gather_success": gather_success(unanswerable, gold_complete if not unanswerable else True, snippet_recall, verdict, len(calls), required_count, leak_hit), "missing_urls": missing_urls, "missing_titles": [item.get("article_title") or "" for item in missing_facts], "agent_queries": [call.get("question") or "" for call in calls], "runtime_error": "", "evidence": evidence, "calls": calls, "gold_fact_items": gold_fact_items}


def evaluate_question(project_root, question_data, leak_hit):
    ground_truth = load_ground_truth(project_root, question_data)
    try:
        task_data, graph_state = run_gather_only(question_data["question"])
        return score_question(question_data["id"], ground_truth, task_data, graph_state, leak_hit)
    except Exception as err:
        if isinstance(err, GraphInterrupt):
            raise
        return empty_score(question_data["id"], ground_truth, leak_hit, repr(err))


def evaluate_all_questions(project_root, questions, leak_hit):
    rows = []
    for question_data in questions:
        if rows:
            sleep(LIVE_GATHER_PAUSE_SECONDS)
        rows.append(evaluate_question(project_root, question_data, leak_hit))
    return rows


def hop_csv_rows(rows):
    csv_rows = []
    for row in rows:
        evidence_urls = unique_urls(row.get("evidence") or [])
        snippets = [item.get("snippet") or "" for item in row.get("evidence") or []]
        for hop_index, gold_item in enumerate(row.get("gold_fact_items") or [], start=1):
            csv_rows.append({"question_id": row["question_id"], "hop_index": hop_index, "gold_title": gold_item.get("article_title") or "", "gold_url": gold_item.get("url") or "", "url_in_evidence": int(bool(gold_item.get("url")) and gold_item.get("url") in evidence_urls), "snippet_in_evidence": int(any_snippet_match(gold_item.get("fact") or "", snippets))})
    return csv_rows


def call_csv_rows(rows):
    csv_rows = []
    for row in rows:
        for call_index, call in enumerate(row.get("calls") or [], start=1):
            csv_rows.append({"question_id": row["question_id"], "call_index": call_index, "gather_turn": call.get("gather_turn") or "", "question": call.get("question") or "", "source": call.get("source") or "", "published_from": call.get("published_from") or "", "published_to": call.get("published_to") or ""})
    return csv_rows


def metric_csv_row(row):
    return {"question_id": row["question_id"], "unanswerable": row["unanswerable"], "required_facts_calls": row["required_facts_calls"], "facts_call_count": row["facts_call_count"], "gold_url_count": row["gold_url_count"], "url_recall": row["url_recall"], "snippet_recall": row["snippet_recall"], "gold_complete": row["gold_complete"], "stop_verdict": row["stop_verdict"], "gather_count": row["gather_count"], "tool_count": row["tool_count"], "gt_dated_required_count": row["gt_dated_required_count"], "agent_dated_call_count": row["agent_dated_call_count"], "gt_source_required_count": row["gt_source_required_count"], "agent_source_call_count": row["agent_source_call_count"], "extra_turn_after_gold": row["extra_turn_after_gold"], "prompt_leak_hit": row["prompt_leak_hit"], "gather_success": row["gather_success"], "missing_urls": " | ".join(row["missing_urls"]), "missing_titles": " | ".join(row["missing_titles"]), "agent_queries": " | ".join(row["agent_queries"]), "runtime_error": row["runtime_error"]}


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_directory, timestamp, rows):
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    write_csv(output_directory / f"metrics_{stamp}.csv", METRIC_FIELDNAMES, [metric_csv_row(row) for row in rows])
    write_csv(output_directory / f"hops_{stamp}.csv", HOP_FIELDNAMES, hop_csv_rows(rows))
    write_csv(output_directory / f"calls_{stamp}.csv", CALL_FIELDNAMES, call_csv_rows(rows))


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    leak_hit = prompt_leak_hit((project_root / "src" / "prompts" / "gather_agent.md").read_text(encoding="utf-8") + (project_root / "src" / "prompts" / "retrieve_agent.md").read_text(encoding="utf-8") + (project_root / "src" / "prompts" / "grade_agent.md").read_text(encoding="utf-8"), collect_exam_needles(project_root, questions))
    write_outputs(Path(__file__).resolve().parent / "outputs", datetime.now().astimezone(), evaluate_all_questions(project_root, questions, leak_hit))


if __name__ == "__main__":
    main()
