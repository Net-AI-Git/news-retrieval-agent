# Retrieval Results Export

## Goal

Run real semantic retrieval for every assignment question and capture the relevant ranked Facts and Corpus evidence in timestamped Markdown files.

## Scope

Exercises `src/services/retrieval_service.py`, the configured embedding API, and the existing local Facts and Corpus Chroma indexes without mocks or index rebuilding.

## How to run

```text
cd project
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.retrieval_results_export.run_retrieval_results_export
```

## Inputs

The runner loads every question from `src/data/questions.json`. For each question it creates one real query embedding and reuses it to query the already-built Facts and Corpus indexes.

## Expected outcome

The `outputs/` directory receives one Markdown file per question. Each filename includes the question ID and run timestamp, and each file records the retrieval status plus up to ten relevant Facts and ten relevant Corpus chunks ordered by match percentage.

## Status

Passing — 2026-08-23
