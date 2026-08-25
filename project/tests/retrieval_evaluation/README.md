# Retrieval Evaluation

## Goal

Measure whether retrieval reaches the expected Facts and Corpus documents for every assignment question.

## Scope

Exercises `src/services/retrieval_service.py` against the real embedding API and the existing local Chroma indexes, then compares ranked results with `src/data/ground_truth/Q01.json` through `Q11.json`.

## Metrics

- **Document Precision@10** — relevant unique source URLs divided by all unique source URLs returned.
- **Document Recall@10** — expected source URLs found divided by all expected source URLs.
- **MRR@10** — reciprocal rank of the first result whose URL belongs to the expected sources.
- **Exact Fact Recall@10** — expected fact sentences found exactly in the Facts results after whitespace normalization.
- **Correct Empty** — an unsupported question passes only when status is `empty` and both evidence lists are empty.
- **Question Pass Rate** — an answerable question passes only at 100% document recall in both stores and 100% exact fact recall; an unsupported question passes only on Correct Empty.

Macro metrics average the nine answerable questions equally. Q04 and Q09 are evaluated only by Correct Empty because their ground-truth evidence lists are empty.

## How to run

```text
cd project
uv run python -m tests.retrieval_evaluation.run_retrieval_evaluation
```

## Inputs

The runner loads `src/data/questions.json` and the matching files under `src/data/ground_truth/`. Each question is sent once to the configured embedding API; its query vector is then used against both already-built indexes.

## Expected outcome

The `outputs/` directory receives timestamped Markdown and JSON reports with aggregate metrics, per-question PASS/FAIL decisions, matched URLs, and missing URLs. No Corpus or Facts embeddings are regenerated.

## Status

Failing — 2026-08-23
