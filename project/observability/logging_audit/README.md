# logging_audit

Local SQL audit tool for the JSONL events written by `LoggingRepository`.

## Usage

1. Edit `AUDIT_QUERY` in [`run_audit.py`](run_audit.py).
2. From `project/`, run `uv run python -m observability.logging_audit.run_audit`.
3. Read `audit_log/audit_<YYYYMMDD_HHMMSS_microseconds>.json`.

The in-memory SQLite view is named `logs` and exposes `time`, `status`, `process`, `content`, `flow_id`, `trace_id`, and `level`.

Examples:

| Goal | SQL |
|---|---|
| Errors | `SELECT * FROM logs WHERE level = 'ERROR' ORDER BY time DESC LIMIT 500` |
| One flow | `SELECT * FROM logs WHERE flow_id = 'abc-123' ORDER BY time` |
| Count by process | `SELECT process, count(*) FROM logs GROUP BY process` |

Do not edit [`logging_audit_client.py`](logging_audit_client.py) unless the storage or query contract changes.
