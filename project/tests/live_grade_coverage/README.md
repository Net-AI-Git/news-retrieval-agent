# Live Grade coverage

## Goal

Score isolated production Grade on frozen mid-loop states: exact `enough` / `missing_hop` / `empty_stop`, retain every accumulated chunk, stop as soon as every need is covered, and keep `note` empty on stop.

## Scope

One live `run_grade` invoke per case in `src/data/ground_truth/grade_coverage.json`. The board scores the three-verdict Grade contract in `src/prompts/grade_agent.md` and `src/schemas/agent.py`. Gather, Retrieve, tools, Chroma, Answer, and Q01–Q11 scoring are out of scope.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_coverage.run_live_grade_coverage
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GRADE_AGENT_MODEL`). Does not need Chroma. No console print; success is a new `outputs/metrics_*.csv`.

## Inputs

`inputs/control.md` is the starting production Grade prompt. Snapshot each live edit as `inputs/candidate_<name>.md`. The runner always loads `src/prompts/grade_agent.md`. Gold cases are `src/data/ground_truth/grade_coverage.json` (see `src/data/ground_truth/README.md`).

## Expected outcome

`outputs/metrics_*.csv`. `case_success=1` when `prompt_leak_hit=0`, `predicted_verdict` equals `expected_verdict`, stop verdicts have an empty `note`, and continue verdicts have a nonempty `note` that is not a prior query string.

Pass for the coverage GOAL is two consecutive newest metrics files, same prompt and model, `case_success=1` on every row.

## Status

Failing — 2026-08-29. Three-verdict append-only runtime contract implemented. Eight additional prompt experiments scored 9, 8, 9, 9, 8, 8, 7, and 9 out of 12, all with zero leakage and runtime errors. `candidate_evidence_only_coverage.md` is the retained 9/12 production prompt. Spec: `project/plans/gate4-grade-coverage-prompt-goal.md`.
