# output_for_mission — Agent Guide

## Purpose
Assignment deliverable folder at the project root. FastAPI does not import this package; it opens `facts_chroma` through `FACTS_CHROMA_PATH`.

## Contains
- `answers.json` — public answer schema for all 11 question IDs.
- `transcripts.json` — tool-call / agent turns for those same questions.
- `dashboard.html` — copy of the generated local logs-and-telemetry dashboard. Never committed.
- `facts_chroma/` — persistent Facts Chroma store written by indexing. Binary files are never committed; `source_catalog.json` is.

## Rules
- `solution.py` writes `answers.json` and `transcripts.json` here after each `answer`.
- `observability/logging_dashboard/build_dashboard.py` writes the live dashboard under `observability/logging_dashboard/`, then copies it here.
- Indexing writes the Facts store to `FACTS_CHROMA_PATH` here.
- Paths are `MISSION_OUTPUT_DIRECTORY`, `ANSWERS_PATH`, `TRANSCRIPTS_PATH`, `MISSION_DASHBOARD_PATH`, and `FACTS_CHROMA_PATH` in [`../src/conts.py`](../src/conts.py).

## Forbidden
- No application source, prompts, or secrets.
- Do not import this directory from `src/` at runtime.

## See Also
- [`../solution.py`](../solution.py)
- [`../observability/logging_dashboard/AGENTS.md`](../observability/logging_dashboard/AGENTS.md)
