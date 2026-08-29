# observability/ — Agent Guide

## Purpose
Offline observability tooling and local artifact output. The microservice never reads this directory at runtime.

## Contains
- [`logging_audit/`](logging_audit/) — SQL audit queries over the local JSONL log.
- [`logging_dashboard/`](logging_dashboard/) — standalone Plotly dashboard generated from those events.
- [`telemetry/`](telemetry/) — local OTLP JSONL span files written by `TelemetryRepository`.

## Coding Rules
- Runtime writers stay in [`../src/repositories/`](../src/repositories/): `logging_repository.py` and `telemetry_repository.py`.
- Each subdirectory keeps its own `AGENTS.md`. This file does not replace them.
- Generated JSONL, audit snapshots, and dashboard HTML stay gitignored.

## Forbidden
- No FastAPI, services, or repository code in this directory.
- Do not import application code into the dashboard or audit tools.
- Do not move the runtime logging or telemetry repositories here.

## See Also
- [`../docs/logging.md`](../docs/logging.md)
- [`../src/repositories/logging_repository.py`](../src/repositories/logging_repository.py)
- [`../src/repositories/telemetry_repository.py`](../src/repositories/telemetry_repository.py)
- [`../../.Codex/rules/04-error-and-logging.md`](../../.Codex/rules/04-error-and-logging.md)
