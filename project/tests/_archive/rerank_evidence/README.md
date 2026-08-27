# Rerank gathered evidence

## Goal

Verify that Top-K facts from every hop are unioned, sent to the OpenRouter rerank API, and that only the reranked subset reaches Answer.

## Scope

Exercises `src/services/rerank_evidence_service.py`, `src/repositories/rerank_repository.py`, and `src/orchestration/grounded_answering_workflow.py` `answer_node`. The rerank HTTP call is mocked.

## How to run

```text
cd project
uv run python -m unittest tests._archive.rerank_evidence.test_rerank_evidence
```

## Inputs

No files in `inputs/`. Tests construct in-memory evidence items and mocked `/rerank` payloads.

## Expected outcome

Empty evidence skips the API and returns `[]`. The same fact text retrieved from two hops is sent once (whitespace-normalized snippet), keeping the higher `match_percentage`. Distinct facts that share a URL all stay. Results are ordered by `relevance_score`, scores below `RERANK_MIN_SCORE` are dropped, and the list is capped at `RERANK_KEEP_TOP_K`. An empty API result returns `None` so Answer keeps the gathered list. `answer_node` sends the reranked list to Answer.

## Status

Archived — 2026-08-27. Rerank was removed; `search_facts` returns Top-1 per hop.
