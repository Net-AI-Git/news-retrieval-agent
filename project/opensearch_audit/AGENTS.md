# opensearch_audit — Agent Guide

> Standalone OpenSearch audit-pull tool. It has its own `.env` and output folder and does not use `OpenSearchRepository`.

## Purpose
Run an arbitrary PPL query and write its results to a timestamped JSON file without overwriting previous pulls.

## Interface
- Edit `PPL_FILTER` only in [`run_audit.py`](run_audit.py).
- Fill local OpenSearch credentials, `OPENSEARCH_LOG_INDEX_PATTERN`, and `OTEL_SERVICE_NAME` in `.env`.
- Call only `pull_audit_logs(query)` from [`opensearch_audit_client.py`](opensearch_audit_client.py).
- Keep all filtering and time logic in PPL; the client remains query-agnostic.

## Hard Rules
- Do not wire this tool into `project/src` or FastAPI.
- Do not change the timestamped, non-overwriting output behavior.
- Never commit generated files under `audit_log/`.
