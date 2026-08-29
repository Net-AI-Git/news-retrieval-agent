# logging_dashboard — Agent Guide

## Purpose
Generate a self-contained Plotly HTML dashboard from local logs and OTLP spans. Panels cover the last 20 minutes. `run_logging_dashboard` rebuilds this file after each completed grounded-answering question. This directory still must not import application code.

## Contains
- `build_dashboard.py` — reads the `logs`, `spans`, and `span_events` SQLite views and generates the dashboard.
- `README.md` — one-command usage and panel inventory.
- `dashboard.html` — generated locally and never committed.

## Rules
- Log panels map to `time` or one of the six fields in [`../../docs/logging.md`](../../docs/logging.md).
- Span panels map to emitted OTLP fields: identity, timestamps, status, `flow_id`, `gen_ai.*`, tool fields, and span events. Coalesce `flow_id` from `flow_id` or `traceloop.association.properties.flow_id`.
- Latency comes only from span `startTimeUnixNano` and `endTimeUnixNano`. Do not compute duration from STARTING/FINISHED logs.
- Join logs and spans on `flow_id` and `trace_id`.
- Bound large span payloads in tables. Do not render embedding vectors.
- Keep Logging and Telemetry on separate tabs with different panel layouts. Overview, Question flows, and GT comparison are additional tabs.
- Agent labels come from `langgraph_node` or the span name. Do not invent agent names.
- Billed tokens use numeric `gen_ai.usage.*` when present, otherwise `characters / 4`. Estimated USD is a labeled dashboard calculation from a local rate table, not an emitted telemetry field.
- The GT comparison tab reads the latest `tests/live_e2e_gt/outputs/metrics_*.csv` and `src/data/ground_truth/Q*.json`. Label it as evaluation output, not as a log or span field. Missing metrics produce empty GT panels; malformed CSV or GT JSON fails visibly.
- Keep the output self-contained with embedded Plotly JavaScript; do not require a server or CDN.
- A log or span-shape change and its dashboard update belong in the same change set.
- Fail visibly on malformed persisted logs or spans.

## Forbidden
- No credentials, tokens, production hostnames, customer PII, or committed log/span results.
- No invented fields presented as emitted telemetry.
- No runtime imports from application code into this directory.

## See Also
- [`../../docs/logging.md`](../../docs/logging.md)
- [`../logging_audit/logging_audit_client.py`](../logging_audit/logging_audit_client.py)
- [`../telemetry_audit/telemetry_audit_client.py`](../telemetry_audit/telemetry_audit_client.py)
- [`../../src/repositories/logging_repository.py`](../../src/repositories/logging_repository.py)
- [`../../src/repositories/telemetry_repository.py`](../../src/repositories/telemetry_repository.py)
