# logging_audit — Agent Guide

## Purpose
Query the local JSONL log with in-memory SQLite and write timestamped audit snapshots without overwriting previous exports.

## Interface
- Edit `AUDIT_QUERY` only in [`run_audit.py`](run_audit.py).
- The audit runner calls `export_audit_logs(query)`. FastAPI routes do not import this client. `build_dashboard` and `run_logging_dashboard` may call `open_logs()`.
- Keep filtering and time logic in SQL; the client remains query-agnostic.

## Hard Rules
- Do not import this client from FastAPI routes.
- Do not change the timestamped, non-overwriting output behavior.
- Never commit generated files under `audit_log/`.
- Do not silently ignore malformed JSONL records.
