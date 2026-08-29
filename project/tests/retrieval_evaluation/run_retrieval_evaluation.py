import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.conts import FACTS_CHROMA_PATH, RETRIEVAL_TOP_K
from src.services.retrieval_service import run_retrieval


def normalize_text(text):
    return " ".join(text.split())


def evaluate_documents(results, expected_items):
    expected_urls = {item["url"] for item in expected_items}
    retrieved_urls = list(dict.fromkeys(result["url"] for result in results if result["url"]))
    matched_urls = expected_urls.intersection(retrieved_urls)
    relevant_ranks = [rank for rank, result in enumerate(results, start=1) if result["url"] in expected_urls]
    return {"expected_document_count": len(expected_urls), "retrieved_document_count": len(retrieved_urls), "relevant_document_count": len(matched_urls), "document_precision_at_10": round(len(matched_urls) / len(retrieved_urls), 4) if retrieved_urls else 0.0, "document_recall_at_10": round(len(matched_urls) / len(expected_urls), 4), "mrr_at_10": round(1 / min(relevant_ranks), 4) if relevant_ranks else 0.0, "matched_urls": sorted(matched_urls), "missing_urls": sorted(expected_urls - matched_urls)}


def evaluate_facts(results, expected_facts):
    metrics = evaluate_documents(results, expected_facts)
    expected_texts = {normalize_text(item["fact"]) for item in expected_facts}
    retrieved_texts = {normalize_text(result["snippet"]) for result in results}
    metrics["exact_fact_recall_at_10"] = round(len(expected_texts.intersection(retrieved_texts)) / len(expected_texts), 4)
    return metrics


def evaluate_question(question_data, ground_truth, retrieval_result):
    if not ground_truth["facts"] and not ground_truth["corpus"]:
        correct_empty = retrieval_result["status"] == "empty" and not retrieval_result["facts"] and not retrieval_result["corpus"]
        return {"id": question_data["id"], "status": retrieval_result["status"], "answerable": False, "passed": correct_empty, "correct_empty": correct_empty, "facts": None, "corpus": None}
    facts_metrics = evaluate_facts(retrieval_result["facts"], ground_truth["facts"])
    corpus_metrics = evaluate_documents(retrieval_result["corpus"], ground_truth["corpus"])
    passed = facts_metrics["document_recall_at_10"] == 1.0 and facts_metrics["exact_fact_recall_at_10"] == 1.0 and corpus_metrics["document_recall_at_10"] == 1.0
    return {"id": question_data["id"], "status": retrieval_result["status"], "answerable": True, "passed": passed, "correct_empty": None, "facts": facts_metrics, "corpus": corpus_metrics}


def average_metric(evaluations, source_name, metric_name):
    values = [evaluation[source_name][metric_name] for evaluation in evaluations if evaluation["answerable"]]
    return round(sum(values) / len(values), 4)


def build_summary(evaluations):
    unsupported = [evaluation for evaluation in evaluations if not evaluation["answerable"]]
    return {"question_pass_rate": round(sum(evaluation["passed"] for evaluation in evaluations) / len(evaluations), 4), "facts_macro_document_precision_at_10": average_metric(evaluations, "facts", "document_precision_at_10"), "facts_macro_document_recall_at_10": average_metric(evaluations, "facts", "document_recall_at_10"), "facts_macro_mrr_at_10": average_metric(evaluations, "facts", "mrr_at_10"), "facts_macro_exact_fact_recall_at_10": average_metric(evaluations, "facts", "exact_fact_recall_at_10"), "corpus_macro_document_precision_at_10": average_metric(evaluations, "corpus", "document_precision_at_10"), "corpus_macro_document_recall_at_10": average_metric(evaluations, "corpus", "document_recall_at_10"), "corpus_macro_mrr_at_10": average_metric(evaluations, "corpus", "mrr_at_10"), "unsupported_correct_empty_rate": round(sum(evaluation["correct_empty"] for evaluation in unsupported) / len(unsupported), 4)}


def format_source_metrics(source_name, metrics):
    lines = [f"#### {source_name}", "", f"- Document Precision@10: {metrics['document_precision_at_10']:.2%}", f"- Document Recall@10: {metrics['document_recall_at_10']:.2%}", f"- MRR@10: {metrics['mrr_at_10']:.4f}"]
    if source_name == "Facts":
        lines.append(f"- Exact Fact Recall@10: {metrics['exact_fact_recall_at_10']:.2%}")
    lines.extend([f"- Matched URLs: {', '.join(metrics['matched_urls']) or 'None'}", f"- Missing URLs: {', '.join(metrics['missing_urls']) or 'None'}", ""])
    return lines


def build_markdown(report):
    summary = report["summary"]
    lines = ["# Retrieval Evaluation", "", f"- Timestamp: {report['timestamp']}", f"- Top K: {report['top_k']}", f"- Question Pass Rate: {summary['question_pass_rate']:.2%}", f"- Facts Macro Document Precision@10: {summary['facts_macro_document_precision_at_10']:.2%}", f"- Facts Macro Document Recall@10: {summary['facts_macro_document_recall_at_10']:.2%}", f"- Facts Macro MRR@10: {summary['facts_macro_mrr_at_10']:.4f}", f"- Facts Macro Exact Fact Recall@10: {summary['facts_macro_exact_fact_recall_at_10']:.2%}", f"- Corpus Macro Document Precision@10: {summary['corpus_macro_document_precision_at_10']:.2%}", f"- Corpus Macro Document Recall@10: {summary['corpus_macro_document_recall_at_10']:.2%}", f"- Corpus Macro MRR@10: {summary['corpus_macro_mrr_at_10']:.4f}", f"- Unsupported Correct Empty Rate: {summary['unsupported_correct_empty_rate']:.2%}", "", "## Per Question", ""]
    for evaluation in report["questions"]:
        lines.extend([f"### {evaluation['id']} — {'PASS' if evaluation['passed'] else 'FAIL'}", "", f"- Retrieval status: {evaluation['status']}"])
        if not evaluation["answerable"]:
            lines.extend([f"- Correct Empty: {evaluation['correct_empty']}", ""])
            continue
        lines.append("")
        lines.extend(format_source_metrics("Facts", evaluation["facts"]))
        lines.extend(format_source_metrics("Corpus", evaluation["corpus"]))
    return "\n".join(lines)


def run_evaluation(project_root, questions, timestamp):
    evaluations = []
    for question_data in questions:
        ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
        if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
            raise ValueError(f"Ground truth mismatch for {question_data['id']}")
        task_data = {"question": question_data["question"], "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma")}
        evaluations.append(evaluate_question(question_data, ground_truth, run_retrieval(task_data, str(uuid4()))))
    return {"timestamp": timestamp.isoformat(timespec="seconds"), "top_k": RETRIEVAL_TOP_K, "summary": build_summary(evaluations), "questions": evaluations}


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    timestamp = datetime.now().astimezone()
    report = run_evaluation(project_root, questions, timestamp)
    output_directory = Path(__file__).resolve().parent / "outputs"
    output_directory.mkdir(parents=True, exist_ok=True)
    output_stem = output_directory / f"retrieval_evaluation_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"
    output_stem.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    output_stem.with_suffix(".md").write_text(build_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
