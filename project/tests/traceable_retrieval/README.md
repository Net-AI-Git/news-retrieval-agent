# Traceable Retrieval

## Goal

Verify bounded, source-traceable semantic retrieval across the Facts and Corpus Chroma stores.

## Scope

Exercises `src/services/retrieval_service.py`, the real embedding API and both active local Chroma collections without mocks.

## How to run

```text
cd project
uv run python -m unittest tests.traceable_retrieval.test_traceable_retrieval
```

The reusable-handle test performs a full real index rebuild once and is intentionally opt-in:

```text
cd project
$env:RUN_INDEX_REBUILD_TEST="true"
uv run python -m unittest tests.traceable_retrieval.test_traceable_retrieval.TraceableRetrievalTests.test_build_index_handle_is_reused_for_multiple_questions
```

## Inputs

The fast test loads Q01 from `src/data/questions.json`, sends the question to the configured embedding API and queries the built Facts and Corpus Chroma collections. The opt-in lifecycle test calls `build_index` once, then sends Q01 and Q02 through the returned handle. Both require valid embedding credentials in `.env`.

## Expected outcome

Both stores receive the same question embedding, each result list is limited to ten items, citation metadata is preserved, and the returned evidence covers both claims in Q01. The lifecycle test also verifies that one non-empty handle serves multiple questions and that retrieval does not change either collection's record count.

## Status

Passing — 2026-08-23
