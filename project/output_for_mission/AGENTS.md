# output_for_mission — Agent Guide

## Purpose
Assignment deliverable folder at the project root. Not read by FastAPI at runtime.

## Contains
- `answers.json` — public answer schema for all 11 question IDs.
- `transcripts.json` — tool-call / agent turns for those same questions.
- `dashboard.html` — copy of the generated local logs-and-telemetry dashboard. Never committed.

## Rules
- `solution.py` writes `answers.json` and `transcripts.json` here after each `answer`.
- `observability/logging_dashboard/build_dashboard.py` writes the live dashboard under `observability/logging_dashboard/`, then copies it here.
- Paths are `MISSION_OUTPUT_DIRECTORY`, `ANSWERS_PATH`, `TRANSCRIPTS_PATH`, and `MISSION_DASHBOARD_PATH` in [`../src/conts.py`](../src/conts.py).

## Forbidden
- No application source, prompts, or secrets.
- Do not import this directory from `src/` at runtime.

## See Also
- [`../solution.py`](../solution.py)
- [`../observability/logging_dashboard/AGENTS.md`](../observability/logging_dashboard/AGENTS.md)
