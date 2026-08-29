# Live Grade GT

## Goal

Score the production Grade prompt on frozen mid-loop states (continue vs stop) without running Gather or Answer. Leakage against the 11-question exam set must stay 0.

## Scope

`src/prompts/grade_agent.md` and `src/agents/grade_agent.py` only. Gather, Answer, retrieval, and the 11-question live loop are out of this runner. The 11/11 exam bar is `tests/live_gather_gt`.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_gt.run_live_grade_gt
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GRADE_AGENT_MODEL`). Does not need Chroma. No console print; success is a new `outputs/metrics_*.csv`.

## Inputs

- `inputs/control.md` — snapshot of the starting Grade prompt. Do not copy it forward as a new idea; snapshot your own candidates.
- `src/data/ground_truth/grade_invented_midloop_stop_continue.json` — invented mid-loop states (question + evidence + prior_queries). Not the exam set.

## Expected outcome

`outputs/metrics_*.csv`. `case_success=1` when `predicted_route` matches `expected_route`, `prompt_leak_hit=0`, and a continue case does not put a prior query string in `note`.

This runner is a cheap stop/continue check. It is not 11/11 vs the exam set.

## Status

Standalone-retry track stopped at 7/11. Best live pair is still Grade `literal_need_binding` (9/11). Spec: `project/plans/gate4-standalone-retry-prompt-goal.md`. Closed Grade-only spec: `project/plans/gate4-live-grade-prompt-goal.md`.
