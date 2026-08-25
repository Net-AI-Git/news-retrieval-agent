import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from local_logging_audit.local_logging_audit_client import export_audit_logs
from src.conts import RETRIEVAL_EVIDENCE_STORE_CORPUS, RETRIEVAL_EVIDENCE_STORE_FACTS
from src.orchestration.grounded_answering_workflow import GroundedAnsweringState, gather_node, route_after_gather, tools_node
from src.repositories.local_logging_repository import LocalLoggingRepository
from src.schemas.agent import SearchEvidenceOutput
from src.services.retrieval_service import run_retrieval
from src.tools.retrieval_tools import RetrievalTools


EVALUATION_TOP_K = 5
UNANSWERABLE_QUESTION_IDS = {"Q04", "Q09"}
CSV_FIELDNAMES = ["question_id", "question", "unanswerable", "gt_answer", "flow_id", "trace_id", "agent_tool_call_count", "agent_tool_names", "gt_required_tools", "facts_precision_at_5", "facts_recall_at_5", "facts_success_at_5", "facts_missing_urls", "corpus_precision_at_5", "corpus_recall_at_5", "corpus_success_at_5", "corpus_missing_urls", "agent_facts_url_recall", "agent_corpus_url_recall", "gt_intents", "gt_sub_questions", "gt_expected_tool_calls", "gt_facts", "gt_corpus_articles", "agent_tool_calls", "agent_tool_results", "isolated_facts_top5", "isolated_corpus_top5"]


def json_cell(payload):
    return json.dumps(payload, ensure_ascii=False)


def gold_fact_records(ground_truth):
    records = []
    for item in ground_truth.get("facts") or []:
        records.append({"fact": item.get("fact"), "article_title": item.get("article_title"), "source": item.get("source"), "category": item.get("category"), "published_at": item.get("published_at"), "url": item.get("url")})
    return records


def gold_corpus_articles(ground_truth):
    articles = []
    for item in ground_truth.get("corpus") or []:
        articles.append({"title": item.get("title"), "author": item.get("author"), "source": item.get("source"), "published_at": item.get("published_at"), "category": item.get("category"), "url": item.get("url")})
    return articles


def gold_urls(ground_truth, bucket_name):
    return list(dict.fromkeys(item["url"] for item in ground_truth.get(bucket_name) or [] if item.get("url")))


def compact_hits(hits):
    compacted = []
    for hit in hits:
        compacted.append({"article_title": hit.get("article_title"), "url": hit.get("url"), "snippet": hit.get("snippet"), "match_percentage": hit.get("match_percentage"), "published_at": hit.get("published_at")})
    return compacted


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
        if tool_call_id and getattr(message, "content", None):
            payload = parse_tool_payload(message.content)
            result_slot = result_by_id.get(tool_call_id)
            if result_slot is not None:
                result_slot["status"] = payload.get("status")
                result_slot["hits"] = compact_hits(payload.get("results") or [])
    return calls, results


def urls_from_agent_results(results, tool_name):
    urls = []
    for result in results:
        if result.get("tool") != tool_name:
            continue
        for hit in result.get("hits") or []:
            url = hit.get("url")
            if url and url not in urls:
                urls.append(url)
    return urls


def url_recall(retrieved_urls, expected_urls, unanswerable):
    if unanswerable:
        return ""
    if not expected_urls:
        return 0.0
    matched = [url for url in expected_urls if url in set(retrieved_urls)]
    return round(len(matched) / len(expected_urls), 4)


def merge_hit(merged, hit, sub_question):
    key = (hit.get("url") or "", hit.get("snippet") or "")
    current = merged.get(key)
    if current is None:
        merged[key] = {"article_title": hit["article_title"], "snippet": hit["snippet"], "url": hit.get("url"), "published_at": hit.get("published_at"), "match_percentage": hit["match_percentage"], "source_sub_questions": [sub_question]}
        return
    if hit["match_percentage"] > current["match_percentage"]:
        current["match_percentage"] = hit["match_percentage"]
        current["article_title"] = hit["article_title"]
        current["published_at"] = hit.get("published_at")
    if sub_question not in current["source_sub_questions"]:
        current["source_sub_questions"].append(sub_question)


def select_top_hits(merged):
    ranked = sorted(merged.values(), key=lambda hit: (-hit["match_percentage"], hit.get("url") or "", hit.get("snippet") or ""))
    return ranked[:EVALUATION_TOP_K]


def annotate_hits(top_hits, expected_urls):
    annotated = []
    for hit in top_hits:
        annotated.append({**hit, "is_hit": bool(hit.get("url") and hit["url"] in expected_urls)})
    return annotated


def store_metrics(unanswerable, expected_urls, top_hits):
    matched_urls = list(dict.fromkeys(hit["url"] for hit in top_hits if hit.get("is_hit")))
    returned = len(top_hits)
    hit_count = sum(1 for hit in top_hits if hit["is_hit"])
    if unanswerable:
        return {"precision_at_5": "", "recall_at_5": "", "success_at_5": "", "missing_urls": []}
    precision = round(hit_count / returned, 4) if returned else 0.0
    recall = round(len(matched_urls) / len(expected_urls), 4) if expected_urls else 0.0
    return {"precision_at_5": precision, "recall_at_5": recall, "success_at_5": 1 if recall == 1.0 else 0, "missing_urls": [url for url in expected_urls if url not in matched_urls]}


def isolated_store_retrieval(project_root, ground_truth, evidence_store, flow_id):
    merged = {}
    for sub_question in ground_truth.get("sub_questions") or []:
        for hit in run_retrieval({"question": sub_question, "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma"), "evidence_store": evidence_store}, flow_id)[evidence_store]:
            merge_hit(merged, hit, sub_question)
    expected_urls = gold_urls(ground_truth, evidence_store)
    unanswerable = ground_truth["id"] in UNANSWERABLE_QUESTION_IDS or not expected_urls
    annotated = annotate_hits(select_top_hits(merged), set(expected_urls))
    return annotated, store_metrics(unanswerable, expected_urls, annotated)


def build_gather_only_graph(task_data, flow_id):
    langchain_tools = RetrievalTools(task_data, flow_id).as_langchain_tools()
    tool_node = ToolNode(langchain_tools)
    graph = StateGraph(GroundedAnsweringState)
    graph.add_node("gather", lambda state: gather_node(state, langchain_tools, flow_id))
    graph.add_node("tools", lambda state: tools_node(state, tool_node))
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", route_after_gather, {"tools": "tools", "answer": END})
    graph.add_edge("tools", "gather")
    return graph.compile()


def gather_one_question(project_root, question_data, flow_id):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    task_data = {"question": question_data["question"], "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma")}
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    graph_state = build_gather_only_graph(task_data, flow_id).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "gather_count": 0, "tool_count": 0, "answer_result": None}, {"recursion_limit": 32})
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    calls, results = collect_agent_tool_trace(graph_state["messages"])
    return {"question_id": question_data["id"], "question": question_data["question"], "ground_truth": ground_truth, "flow_id": flow_id, "trace_id": LocalLoggingRepository.active_trace_id.get(), "agent_tool_calls": calls, "agent_tool_results": results}


def build_inspect_row(project_root, gathered_item):
    ground_truth = gathered_item["ground_truth"]
    unanswerable = 1 if gathered_item["question_id"] in UNANSWERABLE_QUESTION_IDS else 0
    facts_hits, facts_metrics = isolated_store_retrieval(project_root, ground_truth, RETRIEVAL_EVIDENCE_STORE_FACTS, gathered_item["flow_id"])
    corpus_hits, corpus_metrics = isolated_store_retrieval(project_root, ground_truth, RETRIEVAL_EVIDENCE_STORE_CORPUS, gathered_item["flow_id"])
    required_tools = [item["tool"] for item in ground_truth.get("expected_tool_calls") or [] if item.get("expectation") == "required"]
    return {"question_id": gathered_item["question_id"], "question": gathered_item["question"], "unanswerable": unanswerable, "gt_answer": ground_truth.get("answer"), "flow_id": gathered_item["flow_id"], "trace_id": gathered_item["trace_id"], "agent_tool_call_count": len(gathered_item["agent_tool_calls"]), "agent_tool_names": ",".join(call["tool"] for call in gathered_item["agent_tool_calls"]), "gt_required_tools": ",".join(required_tools), "facts_precision_at_5": facts_metrics["precision_at_5"], "facts_recall_at_5": facts_metrics["recall_at_5"], "facts_success_at_5": facts_metrics["success_at_5"], "facts_missing_urls": " | ".join(facts_metrics["missing_urls"]), "corpus_precision_at_5": corpus_metrics["precision_at_5"], "corpus_recall_at_5": corpus_metrics["recall_at_5"], "corpus_success_at_5": corpus_metrics["success_at_5"], "corpus_missing_urls": " | ".join(corpus_metrics["missing_urls"]), "agent_facts_url_recall": url_recall(urls_from_agent_results(gathered_item["agent_tool_results"], "search_facts"), gold_urls(ground_truth, "facts"), unanswerable), "agent_corpus_url_recall": url_recall(urls_from_agent_results(gathered_item["agent_tool_results"], "search_corpus"), gold_urls(ground_truth, "corpus"), unanswerable), "gt_intents": json_cell(ground_truth.get("intents") or []), "gt_sub_questions": json_cell(ground_truth.get("sub_questions") or []), "gt_expected_tool_calls": json_cell(ground_truth.get("expected_tool_calls") or []), "gt_facts": json_cell(gold_fact_records(ground_truth)), "gt_corpus_articles": json_cell(gold_corpus_articles(ground_truth)), "agent_tool_calls": json_cell(gathered_item["agent_tool_calls"]), "agent_tool_results": json_cell(gathered_item["agent_tool_results"]), "isolated_facts_top5": json_cell(facts_hits), "isolated_corpus_top5": json_cell(corpus_hits)}


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pull_run_audit(trace_id):
    audit_path = export_audit_logs(f"SELECT * FROM local_logs WHERE trace_id = '{trace_id}' ORDER BY time")
    if audit_path is None:
        raise RuntimeError("Audit pull failed")
    if not json.loads(audit_path.read_text(encoding="utf-8")):
        raise RuntimeError(f"Audit log empty: {audit_path}")


def run_gather_inspect(project_root, questions):
    rows = []
    for question_data in questions:
        rows.append(build_inspect_row(project_root, gather_one_question(project_root, question_data, str(uuid4()))))
    return rows


def selected_questions(questions):
    if "--smoke" in sys.argv:
        return [item for item in questions if item["id"] == "Q01"]
    return questions


def run_agent_subquestion_evaluation(project_root, questions):
    timestamp = datetime.now().astimezone()
    run_trace_id = str(uuid4())
    trace_token = LocalLoggingRepository.active_trace_id.set(run_trace_id)
    try:
        rows = run_gather_inspect(project_root, questions)
        write_csv(Path(__file__).resolve().parent / "outputs" / f"gather_inspect_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv", CSV_FIELDNAMES, rows)
        pull_run_audit(run_trace_id)
    finally:
        LocalLoggingRepository.active_trace_id.reset(trace_token)


def main():
    project_root = Path(__file__).resolve().parents[2]
    run_agent_subquestion_evaluation(project_root, selected_questions(json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
