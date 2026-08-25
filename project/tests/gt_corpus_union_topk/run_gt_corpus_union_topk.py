import csv
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


EVALUATION_TOP_K = 5
UNANSWERABLE_QUESTION_IDS = {"Q04", "Q09"}
METRIC_FIELDNAMES = ["question_id", "unanswerable", "gold_article_count", "returned_chunk_count", "hit_chunk_count", "false_positives", "precision_at_5", "recall_at_5", "success_at_5", "matched_url_count", "missing_urls"]
CHUNK_FIELDNAMES = ["question_id", "rank", "is_hit", "match_percentage", "article_title", "url", "source_sub_questions", "snippet"]


from src.conts import RETRIEVAL_EVIDENCE_STORE_CORPUS
from src.services.retrieval_service import run_retrieval


def retrieve_corpus_hits(project_root, question):
    task_data = {"question": question, "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma"), "evidence_store": RETRIEVAL_EVIDENCE_STORE_CORPUS}
    return run_retrieval(task_data, str(uuid4()))["corpus"]


def merge_corpus_hit(merged, hit, sub_question):
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


def annotate_hits(top_hits, gold_urls):
    annotated = []
    for hit in top_hits:
        annotated.append({**hit, "is_hit": bool(hit.get("url") and hit["url"] in gold_urls)})
    return annotated


def question_metrics(unanswerable, gold_urls, top_hits, matched_urls):
    returned = len(top_hits)
    hit_count = sum(1 for hit in top_hits if hit["is_hit"])
    if unanswerable:
        return {"unanswerable": 1, "gold_article_count": 0, "returned_chunk_count": returned, "hit_chunk_count": 0, "false_positives": returned, "precision_at_5": "", "recall_at_5": "", "success_at_5": "", "matched_url_count": 0, "missing_urls": []}
    precision = round(hit_count / returned, 4) if returned else 0.0
    recall = round(len(matched_urls) / len(gold_urls), 4) if gold_urls else 0.0
    return {"unanswerable": 0, "gold_article_count": len(gold_urls), "returned_chunk_count": returned, "hit_chunk_count": hit_count, "false_positives": returned - hit_count, "precision_at_5": precision, "recall_at_5": recall, "success_at_5": 1 if recall == 1.0 else 0, "matched_url_count": len(matched_urls), "missing_urls": [url for url in gold_urls if url not in matched_urls]}


def score_question(question_data, ground_truth, top_hits):
    gold_urls = list(dict.fromkeys(item["url"] for item in ground_truth.get("corpus") or [] if item.get("url")))
    unanswerable = question_data["id"] in UNANSWERABLE_QUESTION_IDS or not gold_urls
    annotated = annotate_hits(top_hits, gold_urls)
    matched_urls = list(dict.fromkeys(hit["url"] for hit in annotated if hit["is_hit"]))
    return {"question_id": question_data["id"], "question": question_data["question"], "answer": ground_truth.get("answer"), "gold_urls": gold_urls, "top_hits": annotated, **question_metrics(unanswerable, gold_urls, annotated, matched_urls)}


def evaluate_one_question(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    merged = {}
    for sub_question in ground_truth.get("sub_questions") or []:
        for hit in retrieve_corpus_hits(project_root, sub_question):
            merge_corpus_hit(merged, hit, sub_question)
    return score_question(question_data, ground_truth, select_top_hits(merged))


def evaluate_all_questions(project_root, questions):
    rows = []
    for question_data in questions:
        rows.append(evaluate_one_question(project_root, question_data))
    return rows


def metric_csv_row(row):
    return {"question_id": row["question_id"], "unanswerable": row["unanswerable"], "gold_article_count": row["gold_article_count"], "returned_chunk_count": row["returned_chunk_count"], "hit_chunk_count": row["hit_chunk_count"], "false_positives": row["false_positives"], "precision_at_5": row["precision_at_5"], "recall_at_5": row["recall_at_5"], "success_at_5": row["success_at_5"], "matched_url_count": row["matched_url_count"], "missing_urls": " | ".join(row["missing_urls"])}


def chunk_csv_rows(row):
    rows = []
    for rank, hit in enumerate(row["top_hits"], start=1):
        rows.append({"question_id": row["question_id"], "rank": rank, "is_hit": int(hit["is_hit"]), "match_percentage": hit["match_percentage"], "article_title": hit.get("article_title"), "url": hit.get("url"), "source_sub_questions": " | ".join(hit.get("source_sub_questions") or []), "snippet": hit.get("snippet") or ""})
    return rows


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summary_lines(rows):
    scored = [row for row in rows if not row["unanswerable"]]
    success_rate = round(sum(row["success_at_5"] for row in scored) / len(scored), 4) if scored else ""
    mean_recall = round(sum(row["recall_at_5"] for row in scored) / len(scored), 4) if scored else ""
    mean_precision = round(sum(row["precision_at_5"] for row in scored) / len(scored), 4) if scored else ""
    return ["## Summary", "", f"- Answerable questions: {len(scored)}", f"- Success@5 (every gold article has a chunk in top 5): {success_rate}", f"- Macro Recall@5: {mean_recall}", f"- Macro Precision@5: {mean_precision}", "", "## Questions", ""]


def append_hit_markdown(lines, hit, rank):
    label = "HIT" if hit["is_hit"] else "MISS"
    lines.append(f"#### Rank {rank} — {label} — {hit['match_percentage']}%")
    lines.append("")
    lines.append(f"- Title: {hit.get('article_title')}")
    lines.append(f"- URL: {hit.get('url')}")
    lines.append(f"- Sub-questions: {' | '.join(hit.get('source_sub_questions') or [])}")
    lines.append("")
    lines.append("```")
    lines.append(hit.get("snippet") or "")
    lines.append("```")
    lines.append("")


def question_markdown(row):
    lines = [f"### {row['question_id']}", "", f"- Question: {row['question']}", f"- GT answer: {row.get('answer')}", f"- Unanswerable: {row['unanswerable']}", f"- Precision@5: {row['precision_at_5']}", f"- Recall@5: {row['recall_at_5']}", f"- Success@5: {row['success_at_5']}", f"- False positives: {row['false_positives']}", f"- Missing gold URLs: {', '.join(row['missing_urls']) or 'None'}", "", "Gold articles:", ""]
    for url in row["gold_urls"]:
        lines.append(f"- {url}")
    if not row["gold_urls"]:
        lines.append("- None")
    lines.extend(["", "Top chunks:", ""])
    for rank, hit in enumerate(row["top_hits"], start=1):
        append_hit_markdown(lines, hit, rank)
    return lines


def build_markdown(rows, timestamp):
    lines = ["# GT Corpus Union Top-5", "", f"- Timestamp: {timestamp.isoformat(timespec='seconds')}", f"- Top K: {EVALUATION_TOP_K}", "- Store: corpus", ""]
    lines.extend(summary_lines(rows))
    for row in rows:
        lines.extend(question_markdown(row))
    return "\n".join(lines) + "\n"


def write_outputs(output_directory, timestamp, rows):
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    chunk_rows = []
    for row in rows:
        chunk_rows.extend(chunk_csv_rows(row))
    write_csv(output_directory / f"metrics_{stamp}.csv", METRIC_FIELDNAMES, [metric_csv_row(row) for row in rows])
    write_csv(output_directory / f"chunks_{stamp}.csv", CHUNK_FIELDNAMES, chunk_rows)
    (output_directory / f"inspection_{stamp}.md").write_text(build_markdown(rows, timestamp), encoding="utf-8")


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    timestamp = datetime.now().astimezone()
    write_outputs(Path(__file__).resolve().parent / "outputs", timestamp, evaluate_all_questions(project_root, questions))


if __name__ == "__main__":
    main()
