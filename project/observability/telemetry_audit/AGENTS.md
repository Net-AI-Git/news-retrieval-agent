# telemetry_audit — Agent Guide

## Purpose
Load local OTLP JSONL span files into an in-memory SQLite view for the unified dashboard. `build_dashboard` calls `open_spans()`. FastAPI routes do not import this directory.

## Interface
- The dashboard calls `open_spans()` and queries the `spans` and `span_events` views.
- Keep filtering and aggregation in SQL; the client remains query-agnostic.
- Read every `spans-*.jsonl` file under [`../telemetry/`](../telemetry/). Do not overwrite or delete those files.

## Hard Rules
- Do not import this client from FastAPI routes.
- Do not import application code.
- Never invent span fields, latency from logs, or service names.
- Duration comes only from `startTimeUnixNano` and `endTimeUnixNano`.
- Derived query columns (`agent`, `input_chars`, `output_chars`) are computed from emitted name, node, and payload fields. Do not invent new OTLP attributes.
- Fail visibly on malformed JSONL. Missing or empty files produce empty tables.
- Do not commit generated telemetry JSONL.

## See Also
- [`../../docs/logging.md`](../../docs/logging.md)
- [`../../src/repositories/telemetry_repository.py`](../../src/repositories/telemetry_repository.py)
- [`../logging_dashboard/AGENTS.md`](../logging_dashboard/AGENTS.md)
