"""Gate 0: match GT facts/citations/questions against facts.json (no corpus)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "data"
GT_DIR = DATA / "ground_truth"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fact_key(row: dict) -> tuple:
    return (row.get("url") or "", row.get("fact") or "")


def main() -> None:
    facts = load_json(DATA / "facts.json")
    questions = {row["id"]: row["question"] for row in load_json(DATA / "questions.json")}
    by_url: dict[str, list[dict]] = {}
    by_exact: dict[tuple[str, str], dict] = {}
    for row in facts:
        by_url.setdefault(row.get("url") or "", []).append(row)
        by_exact[fact_key(row)] = row

    sources = Counter(row.get("source") for row in facts)
    print("facts.json rows", len(facts), "unique urls", len(by_url))
    print("sources with nyt/wsj/bbc/forbes:")
    for source, count in sorted(sources.items()):
        lowered = (source or "").lower()
        if any(token in lowered for token in ("new york times", "wall street", "bbc", "forbes", "journal")):
            print(f"  {count:3d}  {source}")

    keywords = (
        "pets best",
        "forerunner",
        "pet insurance",
        "wall street journal",
        "wsj",
        "forbes",
    )
    print("\nkeyword hits in facts.json:")
    for keyword in keywords:
        hits = [
            row
            for row in facts
            if keyword in json.dumps(row, ensure_ascii=False).lower()
        ]
        print(f"  {keyword!r}: {len(hits)}")
        for row in hits[:5]:
            print("   ", row.get("source"), row.get("article_title"), row.get("url"))

    nyt = [row for row in facts if (row.get("source") or "") == "The New York Times"]
    print("\nNYT facts:")
    for row in nyt:
        print(" ", row.get("published_at"), row.get("article_title"))
        print("   ", (row.get("fact") or "")[:180])

    for path in sorted(GT_DIR.glob("Q*.json")):
        gt = load_json(path)
        qid = gt["id"]
        print("\n" + "=" * 80)
        print(qid, gt.get("answer"), gt.get("intents"))
        q_match = (gt.get("question") or "") == questions.get(qid)
        print("question vs questions.json:", "MATCH" if q_match else "MISMATCH")
        if not q_match:
            print("  gt:", gt.get("question"))
            print("  q :", questions.get(qid))

        tool_names = [call.get("tool") for call in gt.get("expected_tool_calls") or []]
        print("tools:", tool_names)
        print("facts count", len(gt.get("facts") or []), "citations", len(gt.get("citations") or []))

        for index, gold in enumerate(gt.get("facts") or [], start=1):
            url = gold.get("url") or ""
            text = gold.get("fact") or ""
            store = by_exact.get((url, text))
            url_rows = by_url.get(url) or []
            print(f"  hop {index}: {gold.get('source')} | {gold.get('published_at')} | {gold.get('article_title')}")
            print(f"          url in store: {bool(url_rows)}  exact fact+url: {store is not None}  url-row count: {len(url_rows)}")
            if store is None and url_rows:
                for row in url_rows:
                    same_title = row.get("article_title") == gold.get("article_title")
                    same_source = row.get("source") == gold.get("source")
                    same_date = row.get("published_at") == gold.get("published_at")
                    print(
                        "          store fact prefix:",
                        (row.get("fact") or "")[:120],
                        "| title/source/date",
                        same_title,
                        same_source,
                        same_date,
                    )
            elif store is not None:
                mismatches = [
                    field
                    for field in ("article_title", "source", "category", "published_at")
                    if store.get(field) != gold.get(field)
                ]
                print("          field mismatches:", mismatches or "none")

        citations = gt.get("citations") or []
        gold_facts_list = gt.get("facts") or []
        for index, citation in enumerate(citations, start=1):
            title = citation.get("article_title")
            snippet = citation.get("snippet")
            matched = next((item for item in gold_facts_list if item.get("article_title") == title and item.get("fact") == snippet), None)
            print(f"  cite {index}: title+snippet vs GT facts: {'OK' if matched else 'MISS'}")

        dates = [(item.get("source"), item.get("published_at"), item.get("article_title")) for item in gold_facts_list]
        if len(dates) >= 2:
            print("  published_at order:")
            for source, published_at, title in dates:
                print(f"    {published_at}  {source}  {title}")


if __name__ == "__main__":
    main()
