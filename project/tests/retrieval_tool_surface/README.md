# Retrieval Tool Surface

## Goal

Verify that `search_facts` and `search_corpus` validate arguments, query only the selected store, and return bounded citation-ready results without exposing raw store internals.

## Scope

Exercises `src/tools/retrieval_tools.py`, `src/schemas/agent.py`, and `src/services/retrieval_service.py` with mocked embeddings and Chroma queries. No live network calls.

## How to run

```text
cd project
$env:OTEL_SDK_DISABLED="true"
uv run python -m unittest tests.retrieval_tool_surface.test_retrieval_tool_surface
```

## Inputs

No files in `inputs/`. Tests construct in-memory question payloads and mocked retrieval records.

## Expected outcome

`search_facts` queries only Facts and returns a `results` list. `search_corpus` queries only Corpus. Invalid tool arguments return `status=invalid` with an empty result list. Dual-store retrieval without `evidence_store` still queries both stores. LangGraph wrappers expose only `question` and optional dates. The tools module calls `run_retrieval` and does not read source JSON files.

## Status

Active — 2026-08-23
