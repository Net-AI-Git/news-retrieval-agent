import csv
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH
from src.tools.retrieval_tools import RetrievalTools


METRIC_FIELDNAMES = ["question_id", "unanswerable", "hop_count", "hops_with_dates", "hops_with_source", "gold_url_count", "gold_snippet_count", "union_result_count", "url_recall", "snippet_recall", "all_chunks_found", "false_positive_url_count", "missing_urls", "missing_titles", "statuses"]
HOP_FIELDNAMES = ["question_id", "hop_index", "query", "source", "published_from", "published_to", "status", "result_count", "gold_title", "gold_url", "url_hit", "snippet_hit", "gold_url_rank", "gold_snippet_rank", "gold_url_score", "gold_snippet_score", "returned_titles"]
CHUNK_FIELDNAMES = ["question_id", "hop_index", "rank", "status", "is_gold_url", "is_gold_snippet", "match_percentage", "article_title", "url", "published_at", "snippet"]
LIVE_SEARCH_PAUSE_SECONDS = 4


def tool_task_data():
    return {"facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}


def bound_search_facts():
    tools = RetrievalTools(tool_task_data(), str(uuid4())).as_langchain_tools()
    names = [tool.name for tool in tools]
    if "search_facts" not in names:
        raise RuntimeError("search_facts is not bound: " + ", ".join(names))
    return next(tool for tool in tools if tool.name == "search_facts")


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
    for item in items:
        url = item.get("url") if isinstance(item, dict) else ""
        if url and url not in urls:
            urls.append(url)
    return urls


def required_facts_calls(ground_truth):
    calls = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("tool") == "search_facts" and item.get("expectation") == "required":
            calls.append(item)
    return calls


def hop_gold_item(ground_truth, call):
    facts = ground_truth.get("facts") or []
    index = call.get("sub_question_index") or 0
    if index < 1 or index > len(facts):
        return {}
    return facts[index - 1]


def first_matching_rank(results, gold_item, require_snippet):
    gold_url = gold_item.get("url") or ""
    gold_fact = gold_item.get("fact") or ""
    for index, item in enumerate(results, start=1):
        if (item.get("url") or "") != gold_url:
            continue
        if require_snippet and not snippet_matches(gold_fact, item.get("snippet") or ""):
            continue
        return {"rank": index, "match_percentage": item.get("match_percentage")}
    return {"rank": "", "match_percentage": ""}


def hop_hit_flag(gold_value, rank):
    if not gold_value:
        return ""
    return 1 if rank != "" else 0


def load_ground_truth(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    return ground_truth


def evaluate_hop(call, payload, gold_item):
    results = payload.get("results") or []
    return {"call": call, "payload": payload, "gold_item": gold_item, "results": results, "arguments": call.get("arguments") or {}, "url_match": first_matching_rank(results, gold_item, False), "snippet_match": first_matching_rank(results, gold_item, True)}


def union_results(hops):
    merged = []
    seen = set()
    for hop in hops:
        for item in hop["results"]:
            key = ((item.get("url") or ""), (item.get("snippet") or ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def any_snippet_match(gold_fact, snippets):
    for snippet in snippets:
        if snippet_matches(gold_fact, snippet):
            return True
    return False


def missing_gold_facts(gold_items, snippets):
    missing = []
    for item in gold_items:
        if not any_snippet_match(item.get("fact") or "", snippets):
            missing.append(item)
    return missing


def ratio(matched_count, expected_count):
    if not expected_count:
        return 1.0
    return round(matched_count / expected_count, 4)


def recall_flags(unanswerable, gold_url_list, gold_items, missing_urls, missing_facts):
    if unanswerable:
        return {"url_recall": "", "snippet_recall": "", "all_chunks_found": 1}
    url_recall = ratio(len(gold_url_list) - len(missing_urls), len(gold_url_list))
    snippet_recall = ratio(len(gold_items) - len(missing_facts), len(gold_items))
    return {"url_recall": url_recall, "snippet_recall": snippet_recall, "all_chunks_found": int(not missing_urls and not missing_facts)}


def question_metrics(ground_truth, hops, union_hits):
    gold_items = ground_truth.get("facts") or []
    unanswerable = int("unanswerable" in (ground_truth.get("intents") or []))
    gold_url_list = unique_urls(gold_items)
    hit_urls = unique_urls(union_hits)
    missing_urls = [url for url in gold_url_list if url not in hit_urls]
    missing_facts = missing_gold_facts(gold_items, [item.get("snippet") or "" for item in union_hits])
    date_hops = sum(1 for hop in hops if hop["arguments"].get("published_from") or hop["arguments"].get("published_to"))
    source_hops = sum(1 for hop in hops if hop["arguments"].get("source"))
    return {"unanswerable": unanswerable, "hop_count": len(hops), "hops_with_dates": date_hops, "hops_with_source": source_hops, "gold_url_count": len(gold_url_list), "gold_snippet_count": len(gold_items), "union_result_count": len(union_hits), **recall_flags(unanswerable, gold_url_list, gold_items, missing_urls, missing_facts), "missing_urls": missing_urls, "missing_titles": [item.get("article_title") or "" for item in missing_facts], "false_positive_url_count": len([url for url in hit_urls if url not in gold_url_list]), "statuses": [hop["payload"].get("status") or "" for hop in hops]}


def evaluate_question(project_root, question_data):
    ground_truth = load_ground_truth(project_root, question_data)
    search_facts = bound_search_facts()
    hops = []
    for call in required_facts_calls(ground_truth):
        if hops:
            sleep(LIVE_SEARCH_PAUSE_SECONDS)
        hops.append(evaluate_hop(call, search_facts.invoke(call.get("arguments") or {}), hop_gold_item(ground_truth, call)))
    union_hits = union_results(hops)
    return {"question_id": question_data["id"], "hops": hops, "union_hits": union_hits, **question_metrics(ground_truth, hops, union_hits)}


def evaluate_all_questions(project_root, questions):
    rows = []
    for question_data in questions:
        if rows:
            sleep(LIVE_SEARCH_PAUSE_SECONDS)
        rows.append(evaluate_question(project_root, question_data))
    return rows


def hop_csv_row(question_id, hop):
    gold_item = hop["gold_item"]
    arguments = hop["arguments"]
    url_rank = hop["url_match"]["rank"]
    snippet_rank = hop["snippet_match"]["rank"]
    return {"question_id": question_id, "hop_index": hop["call"].get("sub_question_index") or "", "query": arguments.get("question") or "", "source": arguments.get("source") or "", "published_from": arguments.get("published_from") or "", "published_to": arguments.get("published_to") or "", "status": hop["payload"].get("status") or "", "result_count": len(hop["results"]), "gold_title": gold_item.get("article_title") or "", "gold_url": gold_item.get("url") or "", "url_hit": hop_hit_flag(gold_item.get("url"), url_rank), "snippet_hit": hop_hit_flag(gold_item.get("fact"), snippet_rank), "gold_url_rank": url_rank, "gold_snippet_rank": snippet_rank, "gold_url_score": hop["url_match"]["match_percentage"], "gold_snippet_score": hop["snippet_match"]["match_percentage"], "returned_titles": " | ".join(item.get("article_title") or "" for item in hop["results"])}


def chunk_csv_rows(question_id, hop):
    rows = []
    gold_url = hop["gold_item"].get("url") or ""
    gold_fact = hop["gold_item"].get("fact") or ""
    for rank, item in enumerate(hop["results"], start=1):
        rows.append({"question_id": question_id, "hop_index": hop["call"].get("sub_question_index") or "", "rank": rank, "status": hop["payload"].get("status") or "", "is_gold_url": int(bool(gold_url) and (item.get("url") or "") == gold_url), "is_gold_snippet": int(bool(gold_fact) and snippet_matches(gold_fact, item.get("snippet") or "")), "match_percentage": item.get("match_percentage"), "article_title": item.get("article_title") or "", "url": item.get("url") or "", "published_at": item.get("published_at") or "", "snippet": item.get("snippet") or ""})
    return rows


def metric_csv_row(row):
    return {"question_id": row["question_id"], "unanswerable": row["unanswerable"], "hop_count": row["hop_count"], "hops_with_dates": row["hops_with_dates"], "hops_with_source": row["hops_with_source"], "gold_url_count": row["gold_url_count"], "gold_snippet_count": row["gold_snippet_count"], "union_result_count": row["union_result_count"], "url_recall": row["url_recall"], "snippet_recall": row["snippet_recall"], "all_chunks_found": row["all_chunks_found"], "false_positive_url_count": row["false_positive_url_count"], "missing_urls": " | ".join(row["missing_urls"]), "missing_titles": " | ".join(row["missing_titles"]), "statuses": " | ".join(row["statuses"])}


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_directory, timestamp, rows):
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    hop_rows = []
    chunk_rows = []
    for row in rows:
        for hop in row["hops"]:
            hop_rows.append(hop_csv_row(row["question_id"], hop))
            chunk_rows.extend(chunk_csv_rows(row["question_id"], hop))
    write_csv(output_directory / f"metrics_{stamp}.csv", METRIC_FIELDNAMES, [metric_csv_row(row) for row in rows])
    write_csv(output_directory / f"hops_{stamp}.csv", HOP_FIELDNAMES, hop_rows)
    write_csv(output_directory / f"chunks_{stamp}.csv", CHUNK_FIELDNAMES, chunk_rows)


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    write_outputs(Path(__file__).resolve().parent / "outputs", datetime.now().astimezone(), evaluate_all_questions(project_root, questions))


if __name__ == "__main__":
    main()
