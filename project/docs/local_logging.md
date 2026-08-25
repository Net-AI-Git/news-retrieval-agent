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
