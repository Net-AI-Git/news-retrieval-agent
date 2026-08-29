# Live E2E GT

## Goal

Run all 11 local-GT questions through the live `POST /api/grounded-answering/run` uvicorn path, pull logs and telemetry by `flow_id` / `trace_id`, and score task success plus per-agent failure against `src/data/ground_truth`.

## Scope

Exercises `src/routes/grounded_answering.py`, `src/orchestration/grounded_answering_workflow.py`, `src/agents/gather_agent.py`, `src/agents/retrieve_agent.py`, `src/agents/grade_agent.py`, `src/agents/answer_agent.py`, `src/tools/retrieval_tools.py`, `src/services/retrieval_service.py`, `src/repositories/logging_repository.py`, `src/repositories/telemetry_repository.py`, and `src/data/ground_truth/Q01.json`–`Q11.json`. Isolated prompt boards are out of scope.

## How to run

```text
cd project
uv sync
uv run python -m tests.live_e2e_gt.run_live_e2e_gt
```

Smoke (Q01 only):

```text
cd project
uv sync
uv run python -m tests.live_e2e_gt.run_live_e2e_gt --smoke
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_GATHER_AGENT_MODEL`, `OPENAI_GRADE_AGENT_MODEL`, `OPENAI_ANSWER_AGENT_MODEL`, `OPENAI_RETRIEVE_AGENT_MODEL`) and `vector_stores/facts_chroma`. The runner starts a live uvicorn process, leaves OpenTelemetry enabled, and does not print. If `DOCS_USER` / `DOCS_PASS` are unset it supplies local docs credentials so `Settings()` can boot. Success is a new `outputs/metrics_*.csv` and a regenerated `observability/logging_dashboard/dashboard.html` plus the copy at `output_for_mission/dashboard.html`.

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and the matching `src/data/ground_truth/Q01.json`–`Q11.json`.

## Expected outcome

`outputs/metrics_<timestamp>.csv` — 11 question rows plus a `TOTAL` row, utf-8-sig, percentages in 0–100:

- `task_success` — 100 only when HTTP 200, the short answer matches GT (including refusal on Q04/Q09), and every GT citation title is present on answerable questions.
- `failure_agent` — first blocking stage: `none` | `runtime` | `gather` | `retrieve` | `retrieval` | `grade` | `answer` | `citation` | `orchestration`.
- Per-agent `*_success` columns, gold/citation/hop/source/date/waste percents, `stop_verdict`, `answer_error_type`, `gather_turns`, `tool_count`, `span_count`, `duration_ms`, `flow_id`, `trace_id`.

`TOTAL.task_success` is the task success rate across the 11 questions.

After the last question the runner writes `outputs/metrics_<timestamp>.csv` and rebuilds `observability/logging_dashboard/dashboard.html`, including the GT comparison tab, then copies it to `output_for_mission/dashboard.html`.

## Status

Passing — 2026-08-29. Latest live run: `outputs/metrics_2026-08-29_15-15-15.csv`.
