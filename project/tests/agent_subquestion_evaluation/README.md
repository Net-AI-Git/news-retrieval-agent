# Agent Sub-question Evaluation

## Goal

Dump one CSV row per question with Gather tool calls next to ground truth and isolated FACTS/CORPUS union Top-5 retrieval, for visual and external-LLM review. No Answer node and no LLM-as-a-judge.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py` gather/tools loop only (answer routes to END), `src/agents/gather_agent.py`, `src/tools/retrieval_tools.py`, `src/services/retrieval_service.py`, and `src/data/ground_truth/Q01.json` through `Q11.json`. Isolated RAG copies the union Top-5 protocol from the GT facts/corpus evals. Logs are pulled with `opensearch_audit.pull_audit_logs`.

## How to run

Log collector on `:4317` and OpenSearch (host/port from `project/.env`) must be up. Do not set `OTEL_SDK_DISABLED`.

```text
cd project
uv sync
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation --smoke
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and matching ground-truth files. Vector stores are `vector_stores/facts_chroma` and `vector_stores/corpus_chroma`. `--smoke` runs Q01 only.

## Expected outcome

`outputs/gather_inspect_<timestamp>.csv` ? one row per question: GT sub-questions and expected tool calls (including date args), gold facts, corpus article metadata, Gather tool names/args/results, isolated FACTS and CORPUS Top-5 HIT/MISS plus P/R/Success@5. `flow_id` joins the row to logs.

`opensearch_audit/audit_log/audit_<timestamp>.json` ? one audit file per run, filtered by those `flow_id` values. Empty audit files fail the run.

Q04 and Q09 are unanswerable: isolated RAG recall is blank; returned hits are false positives.

## Status

Active ? 2026-08-25
