import csv
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.agents.answer_agent import run_answer
from src.conts import ANSWER_STATUS_REFUSED, RETRIEVAL_PERCENT_SCALE
from src.orchestration.grounded_answering_workflow import filter_answer_citations


METRIC_FIELDNAMES = ["question_id", "unanswerable", "expected_answer", "predicted_status", "predicted_answer", "answer_match", "citation_title_recall", "citations_empty", "injected_evidence_count", "oracle_success", "expected_citation_titles", "predicted_citation_titles", "missing_citation_titles"]
ORACLE_ANSWER_PAUSE_SECONDS = 4


def evidence_from_facts(facts):
    items = []
    for fact in facts:
        items.append({"article_title": fact.get("article_title") or "", "snippet": fact.get("fact") or "", "url": fact.get("url") or "", "published_at": fact.get("published_at") or "", "match_percentage": float(RETRIEVAL_PERCENT_SCALE)})
    return items


def load_ground_truth(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    return ground_truth


def dump_answer(answer_result):
    if hasattr(answer_result, "model_dump"):
        return answer_result.model_dump()
    return answer_result


def normalize_text(text):
    return " ".join((text or "").lower().split())


def normalize_answer(text):
    return normalize_text(text).strip(" .!?,;:'\"")


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


def citation_titles(items):
    titles = []
    for item in items or []:
        title = item.get("article_title") or ""
        if title and title not in titles:
            titles.append(title)
    return titles


def missing_citation_titles(expected_titles, predicted_titles):
    missing = []
    for title in expected_titles:
        if title not in predicted_titles:
            missing.append(title)
    return missing


def citation_title_recall(expected_titles, missing_titles, unanswerable):
    if unanswerable or not expected_titles:
        return 1.0
    return round((len(expected_titles) - len(missing_titles)) / len(expected_titles), 4)


def oracle_success(unanswerable, answer_ok, missing_titles, predicted_citations):
    if unanswerable:
        return int(answer_ok and not predicted_citations)
    return int(answer_ok and not missing_titles)


def score_question(question_id, ground_truth, evidence, answer_result):
    unanswerable = int("unanswerable" in (ground_truth.get("intents") or []))
    expected_titles = citation_titles(ground_truth.get("citations") or [])
    predicted_titles = citation_titles(answer_result.get("citations") or [])
    missing_titles = missing_citation_titles(expected_titles, predicted_titles)
    answer_ok = answers_match(answer_result, ground_truth.get("answer") or "", unanswerable)
    return {"question_id": question_id, "unanswerable": unanswerable, "expected_answer": ground_truth.get("answer") or "", "predicted_status": answer_result.get("status") or "", "predicted_answer": answer_result.get("answer") or "", "answer_match": int(answer_ok), "expected_citation_titles": expected_titles, "predicted_citation_titles": predicted_titles, "missing_citation_titles": missing_titles, "citation_title_recall": citation_title_recall(expected_titles, missing_titles, unanswerable), "citations_empty": int(not (answer_result.get("citations") or [])), "injected_evidence_count": len(evidence), "oracle_success": oracle_success(unanswerable, answer_ok, missing_titles, answer_result.get("citations") or [])}


def evaluate_question(project_root, question_data):
    ground_truth = load_ground_truth(project_root, question_data)
    evidence = evidence_from_facts(ground_truth.get("facts") or [])
    return score_question(question_data["id"], ground_truth, evidence, dump_answer(filter_answer_citations(run_answer({"question": question_data["question"], "evidence": evidence}, str(uuid4())), evidence)))


def evaluate_all_questions(project_root, questions):
    rows = []
    for question_data in questions:
        if rows:
            sleep(ORACLE_ANSWER_PAUSE_SECONDS)
        rows.append(evaluate_question(project_root, question_data))
    return rows


def metric_csv_row(row):
    return {"question_id": row["question_id"], "unanswerable": row["unanswerable"], "expected_answer": row["expected_answer"], "predicted_status": row["predicted_status"], "predicted_answer": row["predicted_answer"], "answer_match": row["answer_match"], "citation_title_recall": row["citation_title_recall"], "citations_empty": row["citations_empty"], "injected_evidence_count": row["injected_evidence_count"], "oracle_success": row["oracle_success"], "expected_citation_titles": " | ".join(row["expected_citation_titles"]), "predicted_citation_titles": " | ".join(row["predicted_citation_titles"]), "missing_citation_titles": " | ".join(row["missing_citation_titles"])}


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_directory, timestamp, rows):
    write_csv(output_directory / f"metrics_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv", METRIC_FIELDNAMES, [metric_csv_row(row) for row in rows])


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    write_outputs(Path(__file__).resolve().parent / "outputs", datetime.now().astimezone(), evaluate_all_questions(project_root, questions))


if __name__ == "__main__":
    main()
