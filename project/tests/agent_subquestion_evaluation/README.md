# Agent Sub-question Evaluation

## Goal

Dump one CSV row per question with Gather tool calls, tool results, and gold-URL retrieval metrics, for visual and external-LLM review. No Isolated RAG, no Answer node, and no LLM-as-a-judge.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py` gather/tools loop only (answer routes to END), `src/agents/gather_agent.py`, `src/tools/retrieval_tools.py`, and `src/data/ground_truth/Q01.json` through `Q11.json`. Isolated RAG lives in `tests/gt_facts_union_topk` and `tests/gt_corpus_union_topk` and is not imported here. After the run, `local_logging_audit.export_audit_logs` writes a snapshot of events for the run `trace_id`.

## How to run

No log collector or OpenSearch is required. Events append to `local_logging_audit/audit_log/events.jsonl`.

```text
cd project
uv sync
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation --smoke
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation
```

Isolated RAG (separate tests, not this package):

```text
cd project
uv run python -m tests.gt_facts_union_topk.run_gt_facts_union_topk
uv run python -m tests.gt_corpus_union_topk.run_gt_corpus_union_topk
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and matching ground-truth files. Vector stores are `vector_stores/facts_chroma` and `vector_stores/corpus_chroma`. `--smoke` runs Q01 only.

## Expected outcome

`outputs/gather_inspect_<timestamp>.csv` — one row per question: GT sub-questions and expected tool calls (including date args), gold facts, corpus article metadata, Gather tool names/args/results with per-hit `is_hit`, gold-URL recall/precision/success for facts and corpus, missing gold URLs, extra `search_corpus` flag, and date-filter counts. `flow_id` is per question; `trace_id` is shared by the whole run.

`local_logging_audit/audit_log/audit_<timestamp>.json` — one audit file per run, filtered by that `trace_id`. Empty audit files fail the run.

Q04 and Q09 are unanswerable: agent URL recall/precision are blank. Returned hits are false positives (`is_hit` is false).

## Status

Active — 2026-08-25
