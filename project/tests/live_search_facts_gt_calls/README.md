# Live search_facts GT calls

## Goal

Call `search_facts` the way Gather would — exact GT `expected_tool_calls` arguments, including Q08 date windows and outlet `source` when the sub-question names one — and measure whether every gold fact chunk is in the live tool results.

## Scope

Exercises `src/tools/retrieval_tools.py` (`as_langchain_tools` → `search_facts`) against `vector_stores/facts_chroma`. Queries come from required `search_facts` rows in `src/data/ground_truth/Q01.json`–`Q11.json`. Corpus is out of scope.

## How to run

```text
cd project
uv sync
uv run python -m tests.live_search_facts_gt_calls.run_live_search_facts_gt_calls
```

Needs `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_EMBEDDING_MODEL`, plus an existing `vector_stores/facts_chroma` and `vector_stores/facts_chroma/source_catalog.json` (written at the end of facts indexing). The runner pauses `LIVE_SEARCH_PAUSE_SECONDS` between hops so a full 11-question pass stays under the OpenRouter free-tier embedding rate.

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and the matching ground-truth file for each id.

## Expected outcome

`outputs/` receives timestamped utf-8-sig CSVs:

- `metrics_*.csv` — one row per question: union of that question’s required `search_facts` calls vs all GT fact chunks (`url_recall`, `snippet_recall`, `all_chunks_found`).
- `hops_*.csv` — one row per required tool call: whether that sub-question retrieved its own gold URL and gold snippet, with ranks, date filters, and `source`.
- `chunks_*.csv` — every returned result, marked gold-URL / gold-snippet.

`all_chunks_found=1` means every GT fact URL and every GT fact sentence appeared in the union. Q04 and Q09 have empty gold: `all_chunks_found=1` if the required facts calls ran (empty results are expected). A hop `snippet_hit=0` with `url_hit=1` means the right article came back but not the gold sentence.

## Status

Active — last full run 2026-08-27 (`outputs/metrics_2026-08-27_19-41-17.csv`). 11/11 `all_chunks_found=1`. All 9 answerable questions retrieved every gold URL and gold snippet, including Q05 The Age and Q08 Tremblant. Q04 and Q09 remain empty-gold as designed.
