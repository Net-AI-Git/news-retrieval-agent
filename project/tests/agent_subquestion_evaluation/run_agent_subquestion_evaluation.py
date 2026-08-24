import csv
import json
import math
import os
import socket
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


UNANSWERABLE_QUESTION_IDS = {"Q04", "Q09"}
DECOMPOSITION_FIELDNAMES = ["question_id", "agent_call_index", "agent_question", "gt_index", "gt_sub_question", "cosine", "is_best_gt_for_this_agent_row", "best_gt_index", "best_cosine"]
RETRIEVAL_SUBQUESTION_FIELDNAMES = ["question_id", "agent_call_index", "agent_question", "unanswerable", "returned_url_count", "false_positives", "document_precision_at_10", "document_recall_at_10", "mrr_at_10"]
RETRIEVAL_QUESTION_FIELDNAMES = ["question_id", "agent_search_call_count", "unique_agent_question_count", "unanswerable", "returned_url_count", "false_positives", "document_precision_at_10", "document_recall_at_10", "mrr_at_10"]


def port_is_open(port):
    connection = socket.socket()
    connection.settimeout(1)
    try:
        connection.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        connection.close()


PORT_STATUS = {"otlp_4317": port_is_open(4317), "opensearch_9200": port_is_open(9200)}
if not PORT_STATUS["otlp_4317"]:
    os.environ["OTEL_SDK_DISABLED"] = "true"

from src.conts import RETRIEVAL_TOP_K
from src.orchestration.grounded_answering_workflow import GroundedAnsweringState, gather_node, route_after_gather, tools_node
from src.repositories.embeddings_repository import OpenAIEmbeddingsRepository
from src.services.retrieval_service import run_retrieval
from src.tools.retrieval_tools import RetrievalTools


def cosine_similarity(left_vector, right_vector):
    left_norm = math.sqrt(sum(value * value for value in left_vector))
    right_norm = math.sqrt(sum(value * value for value in right_vector))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left_vector, right_vector)) / (left_norm * right_norm)


def collect_agent_search_calls(messages):
    agent_rows = []
    for message in messages:
        for tool_call in getattr(message, "tool_calls", None) or []:
            arguments = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
            if not isinstance(arguments, dict):
                continue
            agent_question = str(arguments.get("question") or "").strip()
            if not agent_question:
                continue
            agent_rows.append({"agent_call_index": len(agent_rows), "agent_question": agent_question})
    return agent_rows


def expected_urls_from_ground_truth(ground_truth):
    urls = []
    seen = set()
    for bucket_name in ("facts", "corpus"):
        for item in ground_truth.get(bucket_name) or []:
            url = str(item.get("url") or "").strip()
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def ranked_urls_from_retrieval(retrieval_result):
    urls = []
    seen = set()
    for hit in retrieval_result["facts"] + retrieval_result["corpus"]:
        url = str(hit.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def union_ranked_urls(url_lists):
    ranked = []
    seen = set()
    for urls in url_lists:
        for url in urls:
            if url not in seen:
                seen.add(url)
                ranked.append(url)
    return ranked


def document_metrics(ranked_urls, expected_urls, unanswerable):
    ranked = ranked_urls[:RETRIEVAL_TOP_K]
    if unanswerable:
        return {"unanswerable": 1, "returned_url_count": len(ranked), "false_positives": len(ranked), "document_precision_at_10": "", "document_recall_at_10": "", "mrr_at_10": ""}
    matched = [url for url in ranked if url in set(expected_urls)]
    relevant_ranks = [rank for rank, url in enumerate(ranked, start=1) if url in set(expected_urls)]
    return {"unanswerable": 0, "returned_url_count": len(ranked), "false_positives": len(ranked) - len(matched), "document_precision_at_10": round(len(matched) / len(ranked), 4) if ranked else 0.0, "document_recall_at_10": round(len(matched) / len(expected_urls), 4) if expected_urls else 0.0, "mrr_at_10": round(1 / min(relevant_ranks), 4) if relevant_ranks else 0.0}


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


def gather_one_question(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    task_data = {"question": question_data["question"], "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma")}
    graph_state = build_gather_only_graph(task_data, str(uuid4())).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "gather_count": 0, "tool_count": 0, "answer_result": None}, {"recursion_limit": 32})
    return {"question_id": question_data["id"], "question": question_data["question"], "ground_truth": ground_truth, "agent_rows": collect_agent_search_calls(graph_state["messages"])}


def embed_gathered_texts(gathered, flow_id):
    texts = []
    for item in gathered:
        for agent_row in item["agent_rows"]:
            texts.append(agent_row["agent_question"])
        for gt_sub_question in item["ground_truth"].get("sub_questions") or []:
            texts.append(gt_sub_question)
    unique_texts = list(dict.fromkeys(texts))
    if not unique_texts:
        return {}
    vectors = OpenAIEmbeddingsRepository.generate_embeddings({"texts": unique_texts}, flow_id)
    if len(vectors) != len(unique_texts):
        raise ValueError("Embedding generation failed")
    return dict(zip(unique_texts, vectors))


def all_decomposition_rows(gathered, embedding_by_text):
    rows = []
    for item in gathered:
        gt_sub_questions = item["ground_truth"].get("sub_questions") or []
        for agent_row in item["agent_rows"]:
            scored_pairs = []
            for gt_index, gt_sub_question in enumerate(gt_sub_questions):
                scored_pairs.append((gt_index, gt_sub_question, cosine_similarity(embedding_by_text[agent_row["agent_question"]], embedding_by_text[gt_sub_question])))
            if not scored_pairs:
                continue
            best_pair = max(scored_pairs, key=lambda scored: scored[2])
            for gt_index, gt_sub_question, cosine in scored_pairs:
                rows.append({"question_id": item["question_id"], "agent_call_index": agent_row["agent_call_index"], "agent_question": agent_row["agent_question"], "gt_index": gt_index, "gt_sub_question": gt_sub_question, "cosine": cosine, "is_best_gt_for_this_agent_row": 1 if cosine == best_pair[2] else 0, "best_gt_index": best_pair[0], "best_cosine": best_pair[2]})
    rows.sort(key=lambda row: (row["question_id"], int(row["agent_call_index"]), -float(row["cosine"])))
    return rows


def retrieval_rows_for_item(item, project_root, cache):
    unanswerable = item["question_id"] in UNANSWERABLE_QUESTION_IDS
    expected_urls = expected_urls_from_ground_truth(item["ground_truth"])
    per_call_rows = []
    per_call_url_lists = []
    for agent_row in item["agent_rows"]:
        if agent_row["agent_question"] not in cache:
            cache[agent_row["agent_question"]] = ranked_urls_from_retrieval(run_retrieval({"question": agent_row["agent_question"], "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma")}, str(uuid4())))
        ranked_urls = cache[agent_row["agent_question"]]
        metrics = document_metrics(ranked_urls, expected_urls, unanswerable)
        per_call_rows.append({"question_id": item["question_id"], "agent_call_index": agent_row["agent_call_index"], "agent_question": agent_row["agent_question"], "unanswerable": metrics["unanswerable"], "returned_url_count": metrics["returned_url_count"], "false_positives": metrics["false_positives"], "document_precision_at_10": metrics["document_precision_at_10"], "document_recall_at_10": metrics["document_recall_at_10"], "mrr_at_10": metrics["mrr_at_10"]})
        per_call_url_lists.append(ranked_urls)
    question_metrics = document_metrics(union_ranked_urls(per_call_url_lists), expected_urls, unanswerable)
    unique_agent_questions = list(dict.fromkeys(agent_row["agent_question"] for agent_row in item["agent_rows"]))
    return per_call_rows, {"question_id": item["question_id"], "agent_search_call_count": len(item["agent_rows"]), "unique_agent_question_count": len(unique_agent_questions), "unanswerable": question_metrics["unanswerable"], "returned_url_count": question_metrics["returned_url_count"], "false_positives": question_metrics["false_positives"], "document_precision_at_10": question_metrics["document_precision_at_10"], "document_recall_at_10": question_metrics["document_recall_at_10"], "mrr_at_10": question_metrics["mrr_at_10"]}


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary_markdown(port_status, gathered, pair_rows, question_rows, timestamp):
    seen = {}
    for row in pair_rows:
        key = (row["question_id"], row["agent_call_index"])
        if key not in seen:
            seen[key] = row["best_cosine"]
    mean_value = round(sum(seen.values()) / len(seen), 6) if seen else ""
    lines = ["# Agent Sub-question Evaluation", "", f"- Timestamp: {timestamp.isoformat(timespec='seconds')}", f"- OTLP :4317: {'open' if port_status['otlp_4317'] else 'closed'}", f"- OpenSearch :9200: {'open' if port_status['opensearch_9200'] else 'closed'}", f"- Questions: {len(gathered)}", f"- Agent search calls: {sum(len(item['agent_rows']) for item in gathered)}", f"- Decomposition pair rows: {len(pair_rows)}", f"- Mean best cosine: {mean_value}", "", "## Retrieval per question", ""]
    for question_row in question_rows:
        lines.append(f"- {question_row['question_id']}: unanswerable={question_row['unanswerable']} returned={question_row['returned_url_count']} false_positives={question_row['false_positives']} P@10={question_row['document_precision_at_10']} R@10={question_row['document_recall_at_10']} MRR@10={question_row['mrr_at_10']}")
    return "\n".join(lines) + "\n"


def write_outputs(output_directory, timestamp, port_status, gathered, pair_rows, retrieval_rows, question_rows):
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    formatted_pairs = []
    for row in pair_rows:
        formatted_pairs.append({**row, "cosine": f"{row['cosine']:.6f}", "best_cosine": f"{row['best_cosine']:.6f}"})
    write_csv(output_directory / f"decomposition_pairs_{stamp}.csv", DECOMPOSITION_FIELDNAMES, formatted_pairs)
    write_csv(output_directory / f"retrieval_per_subquestion_{stamp}.csv", RETRIEVAL_SUBQUESTION_FIELDNAMES, retrieval_rows)
    write_csv(output_directory / f"retrieval_per_question_{stamp}.csv", RETRIEVAL_QUESTION_FIELDNAMES, question_rows)
    (output_directory / f"summary_{stamp}.md").write_text(build_summary_markdown(port_status, gathered, pair_rows, question_rows, timestamp), encoding="utf-8")


def run_agent_subquestion_evaluation(project_root, questions):
    gathered = []
    for question_data in questions:
        gathered.append(gather_one_question(project_root, question_data))
    embedding_by_text = embed_gathered_texts(gathered, str(uuid4()))
    pair_rows = all_decomposition_rows(gathered, embedding_by_text)
    retrieval_cache = {}
    retrieval_rows = []
    question_rows = []
    for item in gathered:
        per_call_rows, question_row = retrieval_rows_for_item(item, project_root, retrieval_cache)
        retrieval_rows.extend(per_call_rows)
        question_rows.append(question_row)
    return gathered, pair_rows, retrieval_rows, question_rows


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    timestamp = datetime.now().astimezone()
    gathered, pair_rows, retrieval_rows, question_rows = run_agent_subquestion_evaluation(project_root, questions)
    write_outputs(Path(__file__).resolve().parent / "outputs", timestamp, PORT_STATUS, gathered, pair_rows, retrieval_rows, question_rows)


if __name__ == "__main__":
    main()