# telemetry_audit

Load `observability/telemetry/spans-*.jsonl` into in-memory SQLite for the dashboard.

The views are:

- `spans` — one row per span, including derived `agent`, `input_chars`, and `output_chars`
- `span_events` — one row per span event

The dashboard owns SQL. This client only loads files.

Malformed JSONL fails visibly. A missing directory or empty files produce empty tables.
