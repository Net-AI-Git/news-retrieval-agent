import csv
import json
import os
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.agents.retrieve_agent import build_retrieve_tools
from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH, GATHER_MAX_TOOL_CALLS, GROUNDED_ANSWERING_RECURSION_LIMIT
from src.orchestration.grounded_answering_workflow import GroundedAnsweringState, cleaned_sub_questions, extract_tool_calls, route_after_gather, route_after_retrieve, tools_node
from src.repositories.local_telemetry_repository import LocalTelemetryRepository
from src.schemas.agent import GatherResult


METRIC_FIELDNAMES = ["question_id", "unanswerable", "required_facts_calls", "facts_call_count", "gold_url_count", "url_recall", "snippet_recall", "first_hop_gold_complete", "gt_dated_required_count", "agent_dated_call_count", "gt_source_required_count", "agent_source_call_count", "prompt_leak_hit", "first_hop_success", "missing_urls", "missing_titles", "agent_queries", "runtime_error"]
HOP_FIELDNAMES = ["question_id", "hop_index", "gold_title", "gold_url", "url_in_evidence", "snippet_in_evidence"]
CALL_FIELDNAMES = ["question_id", "call_index", "gather_turn", "question", "source", "published_from", "published_to"]
LIVE_GATHER_PAUSE_SECONDS = 20
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


def run_experiment_gather(task_data, gather_prompt):
    return ChatOpenAI(model=os.getenv("OPENAI_GATHER_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0, seed=151).with_structured_output(GatherResult).invoke([SystemMessage(gather_prompt), HumanMessage(json.dumps({"question": task_data["question"], "prior_queries": task_data.get("prior_queries") or [], "grade_note": task_data.get("grade_note") or ""}, ensure_ascii=False))])


def gather_experiment_node(state, task_data, gather_prompt):
    sub_questions = cleaned_sub_questions(run_experiment_gather({**task_data, "question": state["question"], "prior_queries": state.get("prior_queries") or [], "grade_note": state.get("grade_note") or ""}, gather_prompt).sub_questions, GATHER_MAX_TOOL_CALLS - state.get("tool_count", 0))
    task_data["gather_count"] = state.get("gather_count", 0) + 1
    task_data["sub_questions"] = sub_questions
    task_data["next_route"] = route_after_gather({"sub_questions": sub_questions, "gather_count": task_data["gather_count"], "tool_count": state.get("tool_count", 0)})
    task_data.setdefault("transcript_turns", []).append({"stage": "gather", "gather_count": task_data["gather_count"], "sub_questions": sub_questions, "tool_calls": [], "next_route": task_data["next_route"]})
    LocalTelemetryRepository.add_event("routing_decision", {"stage": "gather", "route": task_data["next_route"], "gather_count": task_data["gather_count"], "tool_count": state.get("tool_count", 0)})
    return {"sub_questions": sub_questions, "gather_count": task_data["gather_count"]}


def retrieve_once_node(state, task_data, flow_id, retrieve_prompt):
    limit = GATHER_MAX_TOOL_CALLS - state.get("tool_count", 0)
    sub_questions = cleaned_sub_questions(state.get("sub_questions"), limit)
    message = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0, seed=151).bind_tools(build_retrieve_tools(task_data, flow_id)).invoke([SystemMessage(retrieve_prompt), HumanMessage(json.dumps({"question": state["question"], "sub_questions": sub_questions}, ensure_ascii=False))])
    tool_calls = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        if len(tool_calls) >= limit:
            break
        tool_calls.append(tool_call)
    retrieve_message = AIMessage(content="", tool_calls=tool_calls)
    task_data["tool_calls"] = extract_tool_calls(retrieve_message)
    task_data["next_route"] = route_after_retrieve({"messages": [retrieve_message], "gather_count": state.get("gather_count", 0), "tool_count": state.get("tool_count", 0)})
    task_data.setdefault("transcript_turns", []).append({"stage": "retrieve", "gather_count": state.get("gather_count", 0), "tool_calls": task_data["tool_calls"], "next_route": task_data["next_route"]})
    LocalTelemetryRepository.add_event("routing_decision", {"stage": "retrieve", "route": task_data["next_route"], "tool_count": state.get("tool_count", 0)})
    return {"messages": [retrieve_message]}


def build_once_graph(task_data, flow_id, gather_prompt, retrieve_prompt):
    tool_node = ToolNode(build_retrieve_tools(task_data, flow_id))
    graph = StateGraph(GroundedAnsweringState)
    graph.add_node("gather", lambda state: gather_experiment_node(state, task_data, gather_prompt))
    graph.add_node("retrieve", lambda state: retrieve_once_node(state, task_data, flow_id, retrieve_prompt))
    graph.add_node("tools", lambda state: tools_node(state, tool_node, task_data, flow_id))
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", route_after_gather, {"retrieve": "retrieve", "answer": END})
    graph.add_conditional_edges("retrieve", route_after_retrieve, {"tools": "tools", "answer": END})
    graph.add_edge("tools", END)
    return graph.compile()


def run_once(question, gather_prompt, retrieve_prompt):
    task_data = {"question": question, "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}
    graph_state = build_once_graph(task_data, str(uuid4()), gather_prompt, retrieve_prompt).invoke({"question": question, "messages": [HumanMessage(question)], "evidence": [], "prior_queries": [], "sub_questions": [], "gather_count": 0, "tool_count": 0, "grade_verdict": None, "grade_note": None, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT})
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


def first_hop_success(unanswerable, gold_complete, source_required, source_agent, dated_required, dated_agent, leak_hit):
    if leak_hit:
        return 0
    if dated_required and dated_agent < dated_required:
        return 0
    if unanswerable:
        return int(source_agent >= source_required)
    if source_required and source_agent < source_required:
        return 0
    return int(gold_complete)


def empty_score(question_id, ground_truth, leak_hit, runtime_error):
    unanswerable = int("unanswerable" in (ground_truth.get("intents") or []))
    required_count = len(required_facts_calls(ground_truth))
    dated_required, source_required = filter_counts(required_facts_calls(ground_truth))
    return {"question_id": question_id, "unanswerable": unanswerable, "required_facts_calls": required_count, "facts_call_count": 0, "gold_url_count": len(unique_urls(gold_items(ground_truth))), "url_recall": 0.0 if not unanswerable else 1.0, "snippet_recall": 0.0 if not unanswerable else 1.0, "first_hop_gold_complete": 0 if not unanswerable else 1, "gt_dated_required_count": dated_required, "agent_dated_call_count": 0, "gt_source_required_count": source_required, "agent_source_call_count": 0, "prompt_leak_hit": leak_hit, "first_hop_success": 0, "missing_urls": unique_urls(gold_items(ground_truth)), "missing_titles": [item.get("article_title") or "" for item in gold_items(ground_truth)], "agent_queries": [], "runtime_error": runtime_error, "evidence": [], "calls": [], "gold_fact_items": gold_items(ground_truth)}


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
    gold_complete = 1 if unanswerable else int(bool(gold_url_set) and gold_url_set <= set(evidence_urls) and not missing_facts)
    url_recall = recall_ratio(len(gold_url_list) - len(missing_urls), len(gold_url_list), unanswerable)
    snippet_recall = recall_ratio(len(gold_fact_items) - len(missing_facts), len(gold_fact_items), unanswerable)
    return {"question_id": question_id, "unanswerable": unanswerable, "required_facts_calls": required_count, "facts_call_count": len(calls), "gold_url_count": len(gold_url_list), "url_recall": url_recall, "snippet_recall": snippet_recall, "first_hop_gold_complete": gold_complete, "gt_dated_required_count": dated_required, "agent_dated_call_count": dated_agent, "gt_source_required_count": source_required, "agent_source_call_count": source_agent, "prompt_leak_hit": leak_hit, "first_hop_success": first_hop_success(unanswerable, gold_complete, source_required, source_agent, dated_required, dated_agent, leak_hit), "missing_urls": missing_urls, "missing_titles": [item.get("article_title") or "" for item in missing_facts], "agent_queries": [call.get("question") or "" for call in calls], "runtime_error": "", "evidence": evidence, "calls": calls, "gold_fact_items": gold_fact_items}


def evaluate_question(project_root, question_data, leak_hit, gather_prompt, retrieve_prompt):
    ground_truth = load_ground_truth(project_root, question_data)
    try:
        task_data, graph_state = run_once(question_data["question"], gather_prompt, retrieve_prompt)
        return score_question(question_data["id"], ground_truth, task_data, graph_state, leak_hit)
    except Exception as err:
        if isinstance(err, GraphInterrupt):
            raise
        return empty_score(question_data["id"], ground_truth, leak_hit, repr(err))


def evaluate_all_questions(project_root, questions, leak_hit, gather_prompt, retrieve_prompt):
    rows = []
    for question_data in questions:
        if rows:
            sleep(LIVE_GATHER_PAUSE_SECONDS)
        rows.append(evaluate_question(project_root, question_data, leak_hit, gather_prompt, retrieve_prompt))
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
    return {"question_id": row["question_id"], "unanswerable": row["unanswerable"], "required_facts_calls": row["required_facts_calls"], "facts_call_count": row["facts_call_count"], "gold_url_count": row["gold_url_count"], "url_recall": row["url_recall"], "snippet_recall": row["snippet_recall"], "first_hop_gold_complete": row["first_hop_gold_complete"], "gt_dated_required_count": row["gt_dated_required_count"], "agent_dated_call_count": row["agent_dated_call_count"], "gt_source_required_count": row["gt_source_required_count"], "agent_source_call_count": row["agent_source_call_count"], "prompt_leak_hit": row["prompt_leak_hit"], "first_hop_success": row["first_hop_success"], "missing_urls": " | ".join(row["missing_urls"]), "missing_titles": " | ".join(row["missing_titles"]), "agent_queries": " | ".join(row["agent_queries"]), "runtime_error": row["runtime_error"]}


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
    experiment_dir = Path(__file__).resolve().parent
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    gather_prompt = (experiment_dir / "inputs" / "gather_prompt.md").read_text(encoding="utf-8")
    retrieve_prompt = (experiment_dir / "inputs" / "candidate_batch_copy.md").read_text(encoding="utf-8")
    leak_hit = prompt_leak_hit(gather_prompt + retrieve_prompt, collect_exam_needles(project_root, questions))
    write_outputs(experiment_dir / "outputs", datetime.now().astimezone(), evaluate_all_questions(project_root, questions, leak_hit, gather_prompt, retrieve_prompt))


if __name__ == "__main__":
    main()
