# Live E2E GT

## Goal

Call root `solution.py` the same way the assignment harness will (`build_index(data_dir)` once, then `answer(index, question_id, question)` per question), then score that public `{answer, citations}` dict plus logs/telemetry against `src/data/ground_truth`.

## Scope

Exercises `solution.build_index`, `solution.answer`, `src/orchestration/grounded_answering_workflow.py`, `src/agents/gather_agent.py`, `src/agents/retrieve_agent.py`, `src/agents/grade_agent.py`, `src/agents/answer_agent.py`, `src/tools/retrieval_tools.py`, `src/services/retrieval_service.py`, `src/repositories/logging_repository.py`, `src/repositories/telemetry_repository.py`, and `src/data/ground_truth/Q01.json`–`Q11.json`. The FastAPI route, uvicorn, and `recorded_answer` are out of scope.

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

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_GATHER_AGENT_MODEL`, `OPENAI_GRADE_AGENT_MODEL`, `OPENAI_ANSWER_AGENT_MODEL`, `OPENAI_RETRIEVE_AGENT_MODEL`) and `output_for_mission/facts_chroma`. The runner imports `build_index` and `answer` only, calls them back-to-back like the assignment harness (no extra pauses), leaves OpenTelemetry enabled, and does not print. Timeouts and rate limits surface as `runtime_error`. Success is a new `outputs/metrics_*.csv` and a regenerated `observability/logging_dashboard/dashboard.html`.

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and the matching `src/data/ground_truth/Q01.json`–`Q11.json`. `task_success` and citation scores use the dict returned by `answer`. Per-agent boards join the latest `execute_grounded_answering` log and new telemetry spans for that question text.

## Expected outcome

`outputs/metrics_<timestamp>.csv` — 11 question rows plus a `TOTAL` row, utf-8-sig, percentages in 0–100:

- `task_success` — 100 only when `answer()` returned a short answer that matches GT (including refusal on Q04/Q09), answerable questions include every GT citation title, and the workflow log has no ERROR.
- `failure_agent` — first blocking stage: `none` | `runtime` | `gather` | `retrieve` | `retrieval` | `grade` | `answer` | `citation` | `orchestration`.
- Per-agent `*_success` columns, gold/citation/hop/source/date/waste percents, `stop_verdict`, `answer_error_type`, `gather_turns`, `tool_count`, `span_count`, `duration_ms`, `flow_id`, `trace_id`. `http_status` stays empty.

`TOTAL.task_success` is the task success rate across the 11 questions.

After scoring, the runner writes `outputs/metrics_<timestamp>.csv` and rebuilds `observability/logging_dashboard/dashboard.html`, including the GT comparison tab.

## Status

Passing — 2026-08-29. Assignment-harness path (`build_index` / `answer`). Latest: `outputs/metrics_2026-08-29_15-36-04.csv`. `TOTAL.task_success` = 100.
