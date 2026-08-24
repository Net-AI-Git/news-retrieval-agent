# Agent Sub-question Evaluation

## Goal

Measure Gather decomposition as the actual search `question` strings, then score isolated facts+corpus retrieval per those strings against parent-question ground-truth URLs.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py` gather/tools loop only (no Answer node), `src/agents/gather_agent.py`, `src/tools/retrieval_tools.py`, `src/services/retrieval_service.py`, `src/repositories/embeddings_repository.py`, and `src/data/ground_truth/Q01.json` through `Q11.json`.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
$env:OPENAI_MODEL="openai/gpt-4o-mini"
uv run python -m tests.agent_subquestion_evaluation.run_agent_subquestion_evaluation
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and matching ground-truth files. Vector stores are the existing `vector_stores/facts_chroma` and `vector_stores/corpus_chroma`. Decomposition similarity uses `OPENAI_EMBEDDING_MODEL`.

## Expected outcome

`outputs/` receives timestamped CSVs:

- `decomposition_pairs_*.csv` ? all `agent_i x gt_j` cosine pairs plus `is_best_gt_for_this_agent_row`
- `retrieval_per_subquestion_*.csv` ? facts+corpus URL P/R/MRR@10 per agent search call vs the parent question URL union
- `retrieval_per_question_*.csv` ? same metrics on the union of that question's agent searches
- `summary_*.md` ? port reachability and per-question retrieval totals

Q04 and Q09 are flagged `unanswerable`: recall is not scored against an empty URL set; the row records returned URL count as false positives.

Logs to OTLP `:4317` / OpenSearch `:9200` are optional debug. This repository's `docker-compose.yaml` is the app container, not the log stack. If those ports are closed the runner sets `OTEL_SDK_DISABLED` and still writes CSV metrics.

## Status

Active ? last run 2026-08-24. 11 questions, 39 agent search calls, mean best cosine 0.753. Answerable questions all reached document recall@10 = 1.0 on the per-question URL union. Q04 returned 0 URLs; Q09 returned 1 false positive.
