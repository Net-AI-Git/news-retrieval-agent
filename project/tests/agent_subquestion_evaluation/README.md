# Agent Sub-question Evaluation

## Goal

Dump one CSV row per question with Gather tool calls next to ground truth and isolated FACTS/CORPUS union Top-5 retrieval, for visual and external-LLM review. No Answer node and no LLM-as-a-judge.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py` gather/tools loop only (answer routes to END), `src/agents/gather_agent.py`, `src/tools/retrieval_tools.py`, `src/services/retrieval_service.py`, and `src/data/ground_truth/Q01.json` through `Q11.json`. Isolated RAG copies the union Top-5 protocol from the GT facts/corpus evals. Audit-log pull is skipped until the log stack is back.

## How to run

If OTLP `:4317` is closed the runner sets `OTEL_SDK_DISABLED` so the run does not hang. Re-enable log pull later when the collector and OpenSearch are up.

```text
cd project
uv sync
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation --smoke
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and matching ground-truth files. Vector stores are `vector_stores/facts_chroma` and `vector_stores/corpus_chroma`. `--smoke` runs Q01 only.

## Expected outcome

`outputs/gather_inspect_<timestamp>.csv` — one row per question: GT sub-questions and expected tool calls (including date args), gold facts, corpus article metadata, Gather tool names/args/results, isolated FACTS and CORPUS Top-5 HIT/MISS plus P/R/Success@5. `flow_id` is on the row for a later log join.

Q04 and Q09 are unanswerable: isolated RAG recall is blank; returned hits are false positives.

## Status

Active — 2026-08-25. Log stack not required for this run.
