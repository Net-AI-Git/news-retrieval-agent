# Logging

Source of truth for structured application logs, audit queries, and the generated dashboard. [`LoggingRepository`](../src/repositories/logging_repository.py) is the only runtime writer.

## Storage

`LoggingRepository.log_event(...)` appends one UTF-8 JSON object per line to `observability/logging_audit/audit_log/events.jsonl` and flushes it immediately. No server, Docker container, account, or environment variable is required.

Each stored line has an infrastructure timestamp around the unchanged event contract:

```json
{
  "time": "<UTC ISO-8601 timestamp>",
  "event": {
    "status": "STARTING | FINISHED | ERROR",
    "process": "<calling function name>",
    "content": "<inputs / outputs / error message>",
    "flow_id": "<flow identifier>",
    "trace_id": "<active trace identifier or null>",
    "level": "INFO | ERROR"
  }
}
```

`process` is auto-detected. An explicitly supplied `trace_id` is preserved; otherwise an active OpenTelemetry API span is used when available. The OpenTelemetry API does not export data or require a server.

## Agent telemetry

`src/repositories/telemetry_repository.py` initializes one sampled OpenTelemetry provider when `run_grounded_answering(...)` starts. It writes completed spans immediately through the official OTLP JSON file exporter to a unique append-only `observability/telemetry/spans-<UTC>-<PID>.jsonl` file for each process. Starting a new process creates the next file; existing files are never overwritten or deleted automatically.

The explicit root span is `invoke_workflow grounded_answering`. LangChain instrumentation creates its model, graph-node, and tool descendants. Retrieval and direct OpenAI embedding calls use manual child spans because they are outside the instrumented LangChain surface. `flow_id` is created in the route, passed through every layer, and copied from OpenTelemetry baggage onto every span. `trace_id` is never minted in application code; lifecycle logs and the HTTP envelope derive it from that root span so every agent, tool, retrieval, and embedding descendant shares the same value. `POST /api/grounded-answering/run` returns both identifiers on the shared `Response` (`content` stays the answer payload).

Inputs, outputs, tool calls, evidence, routing decisions, token usage, and errors are retained. Keys that look like credentials, authorization values, API keys, passwords, secrets, or session tokens are replaced with `[REDACTED]`; hidden model reasoning is not captured. No Collector, server, Docker container, account, or network connection is used for telemetry export.

Lifecycle logging remains explicit in the owning function. Telemetry uses one explicit workflow context and framework instrumentation rather than custom decorators, avoiding hidden safe-default behavior and duplicate spans.

## Audit queries

Run from `project/`:

```powershell
uv run python -m observability.logging_audit.run_audit
```

The audit client loads JSONL into an in-memory SQLite view named `logs` with `time`, `status`, `process`, `content`, `flow_id`, `trace_id`, and `level` columns. `run_audit.py` owns the SQL filter. Results are written to a new timestamped JSON file under `audit_log/`.

Missing or empty log files produce an empty table. Malformed JSONL fails visibly instead of silently dropping records.

## Dashboard

Run from `project/`:

```powershell
uv run python -m observability.logging_dashboard.build_dashboard
```

The command writes a self-contained `observability/logging_dashboard/dashboard.html` from both `events.jsonl` and `observability/telemetry/spans-*.jsonl`, limited to the last 20 minutes, plus the latest `tests/live_e2e_gt/outputs/metrics_*.csv` on the GT comparison tab. `run_grounded_answering` rebuilds that file after each completed question. The live E2E runner rebuilds it again after writing the metrics CSV. The HTML has separate Logging and Telemetry tabs, plus Overview, Question flows, and GT comparison. Log panels stay on the six-field event contract. Span panels use emitted OTLP fields; duration comes from span timestamps, not STARTING/FINISHED logs. Flows are joined on `flow_id` and `trace_id`. Billed tokens use numeric `gen_ai.usage` when present, otherwise characters / 4. Estimated USD is a labeled dashboard calculation from a local rate table. GT rates come from the scored CSV, not from invented span fields. The HTML embeds Plotly and requires no running server or internet connection.

Generated JSONL, audit snapshots, and dashboard HTML are artifacts and are not committed.
