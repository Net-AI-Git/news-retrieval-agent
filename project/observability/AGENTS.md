# observability/ — Agent Guide

## Purpose
Offline observability tooling and local artifact output. Runtime writers stay in [`../src/repositories/`](../src/repositories/). After each completed grounded-answering question, [`../src/services/logging_dashboard_service.py`](../src/services/logging_dashboard_service.py) rebuilds the dashboard. FastAPI routes do not import this directory. Dashboard and audit tools still must not import application code.

## Contains
- [`logging_audit/`](logging_audit/) — SQL audit queries over the local JSONL log.
- [`telemetry_audit/`](telemetry_audit/) — SQL loader for local OTLP JSONL spans.
- [`logging_dashboard/`](logging_dashboard/) — standalone Plotly dashboard generated from logs, spans, and the latest live E2E GT metrics CSV.
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
