# Local Logging

Source of truth for structured application logs, local audit queries, and the generated dashboard. [`LocalLoggingRepository`](../src/repositories/local_logging_repository.py) is the only runtime writer.

## Storage

`LocalLoggingRepository.log_event(...)` appends one UTF-8 JSON object per line to `local_logging_audit/audit_log/events.jsonl` and flushes it immediately. No server, Docker container, account, or environment variable is required.

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

`src/repositories/local_telemetry_repository.py` initializes one sampled OpenTelemetry provider when `run_grounded_answering(...)` starts. It writes completed spans immediately through the official OTLP JSON file exporter to a unique append-only `local_telemetry/spans-<UTC>-<PID>.jsonl` file for each process. Starting a new process creates the next file; existing files are never overwritten or deleted automatically.

The explicit root span is `invoke_workflow grounded_answering`. LangChain instrumentation creates its model, graph-node, and tool descendants. Retrieval and direct OpenAI embedding calls use manual child spans because they are outside the instrumented LangChain surface. `flow_id` is copied from OpenTelemetry baggage onto every span, and lifecycle logs read the active `trace_id`, so one flow can be reconstructed across both JSONL stores.

Inputs, outputs, tool calls, evidence, routing decisions, token usage, and errors are retained. Keys that look like credentials, authorization values, API keys, passwords, secrets, or session tokens are replaced with `[REDACTED]`; hidden model reasoning is not captured. No Collector, server, Docker container, account, or network connection is used for telemetry export.

Lifecycle logging remains explicit in the owning function. Telemetry uses one explicit workflow context and framework instrumentation rather than custom decorators, avoiding hidden safe-default behavior and duplicate spans.

## Audit queries

Run from `project/`:

```powershell
uv run python -m local_logging_audit.run_audit
```

The audit client loads JSONL into an in-memory SQLite view named `local_logs` with `time`, `status`, `process`, `content`, `flow_id`, `trace_id`, and `level` columns. `run_audit.py` owns the SQL filter. Results are written to a new timestamped JSON file under `audit_log/`.

Missing or empty log files produce an empty table. Malformed JSONL fails visibly instead of silently dropping records.

## Dashboard

Run from `project/`:

```powershell
uv run python -m local_logging_dashboard.build_dashboard
```

The command writes a self-contained `local_logging_dashboard/dashboard.html` with total events, errors, status counts, errors by process, events over time, and recent errors. The HTML embeds Plotly and requires no running server or internet connection.

Generated JSONL, audit snapshots, and dashboard HTML are local artifacts and are not committed.
