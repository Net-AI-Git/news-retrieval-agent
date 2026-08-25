# Local logging

## Goal
Verify real local JSONL persistence, SQL audit queries, and standalone dashboard generation without a logging server.

## Scope
Exercises `src/repositories/local_logging_repository.py`, `local_logging_audit/`, and `local_logging_dashboard/`.

## How to run

```powershell
cd project
uv sync --frozen
uv run --frozen python -m unittest tests.local_logging.test_local_logging
```

## Inputs
The test writes uniquely identified events through the production `LocalLoggingRepository` into the gitignored local audit log. No fixture or external service is used.

## Expected outcome
The persisted event retains the exact six-field contract, SQLite returns the written event, and Plotly creates an HTML file with no external script source.

## Status
Active — 2026-08-25.
