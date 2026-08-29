import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "data"
GT_DIR = DATA / "ground_truth"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fact_key(row):
    return (row.get("url") or "", row.get("fact") or "")


def index_facts(facts):
    by_url = {}
    by_exact = {}
    for row in facts:
        by_url.setdefault(row.get("url") or "", []).append(row)
        by_exact[fact_key(row)] = row
    return by_url, by_exact


def print_source_hits(facts, by_url):
    sources = Counter(row.get("source") for row in facts)
    print("facts.json rows", len(facts), "unique urls", len(by_url))
    print("sources with nyt/wsj/bbc/forbes:")
    for source, count in sorted(sources.items()):
        if any(token in (source or "").lower() for token in ("new york times", "wall street", "bbc", "forbes", "journal")):
            print(f"  {count:3d}  {source}")


def print_keyword_hits(facts):
    print("\nkeyword hits in facts.json:")
    for keyword in ("pets best", "forerunner", "pet insurance", "wall street journal", "wsj", "forbes"):
        hits = [row for row in facts if keyword in json.dumps(row, ensure_ascii=False).lower()]
        print(f"  {keyword!r}: {len(hits)}")
        for row in hits[:5]:
            print("   ", row.get("source"), row.get("article_title"), row.get("url"))


def print_nyt_facts(facts):
    print("\nNYT facts:")
    for row in [row for row in facts if (row.get("source") or "") == "The New York Times"]:
        print(" ", row.get("published_at"), row.get("article_title"))
        print("   ", (row.get("fact") or "")[:180])


def print_unmatched_store_rows(gold, url_rows):
    for row in url_rows:
        print("          store fact prefix:", (row.get("fact") or "")[:120], "| title/source/date", row.get("article_title") == gold.get("article_title"), row.get("source") == gold.get("source"), row.get("published_at") == gold.get("published_at"))


def print_gold_hops(gt, by_url, by_exact):
    for index, gold in enumerate(gt.get("facts") or [], start=1):
        url = gold.get("url") or ""
        store = by_exact.get((url, gold.get("fact") or ""))
        url_rows = by_url.get(url) or []
        print(f"  hop {index}: {gold.get('source')} | {gold.get('published_at')} | {gold.get('article_title')}")
        print(f"          url in store: {bool(url_rows)}  exact fact+url: {store is not None}  url-row count: {len(url_rows)}")
        if store is None and url_rows:
            print_unmatched_store_rows(gold, url_rows)
        elif store is not None:
            print("          field mismatches:", [field for field in ("article_title", "source", "category", "published_at") if store.get(field) != gold.get(field)] or "none")


def print_citations_and_dates(gt):
    gold_facts_list = gt.get("facts") or []
    for index, citation in enumerate(gt.get("citations") or [], start=1):
        print(f"  cite {index}: title+snippet vs GT facts: {'OK' if next((item for item in gold_facts_list if item.get('article_title') == citation.get('article_title') and item.get('fact') == citation.get('snippet')), None) else 'MISS'}")
    dates = [(item.get("source"), item.get("published_at"), item.get("article_title")) for item in gold_facts_list]
    if len(dates) >= 2:
        print("  published_at order:")
        for source, published_at, title in dates:
            print(f"    {published_at}  {source}  {title}")


def print_gt_file(path, questions, by_url, by_exact):
    gt = load_json(path)
    qid = gt["id"]
    print("\n" + "=" * 80)
    print(qid, gt.get("answer"), gt.get("intents"))
    q_match = (gt.get("question") or "") == questions.get(qid)
    print("question vs questions.json:", "MATCH" if q_match else "MISMATCH")
    if not q_match:
        print("  gt:", gt.get("question"))
        print("  q :", questions.get(qid))
    print("tools:", [call.get("tool") for call in gt.get("expected_tool_calls") or []])
    print("facts count", len(gt.get("facts") or []), "citations", len(gt.get("citations") or []))
    print_gold_hops(gt, by_url, by_exact)
    print_citations_and_dates(gt)


def main():
    facts = load_json(DATA / "facts.json")
    questions = {row["id"]: row["question"] for row in load_json(DATA / "questions.json")}
    by_url, by_exact = index_facts(facts)
    print_source_hits(facts, by_url)
    print_keyword_hits(facts)
    print_nyt_facts(facts)
    for path in sorted(GT_DIR.glob("Q*.json")):
        print_gt_file(path, questions, by_url, by_exact)


if __name__ == "__main__":
    main()
