# logging_audit — Agent Guide

## Purpose
Query the local JSONL log with in-memory SQLite and write timestamped audit snapshots without overwriting previous exports.

## Interface
- Edit `AUDIT_QUERY` only in [`run_audit.py`](run_audit.py).
- The audit runner calls `export_audit_logs(query)`; the local dashboard may reuse `open_logs()` for the same SQL view.
- Keep filtering and time logic in SQL; the client remains query-agnostic.

## Hard Rules
- Do not wire this tool into `project/src` or FastAPI.
- Do not change the timestamped, non-overwriting output behavior.
- Never commit generated files under `audit_log/`.
- Do not silently ignore malformed JSONL records.
