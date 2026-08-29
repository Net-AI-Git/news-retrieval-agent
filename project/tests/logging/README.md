# Local logging

## Goal
Verify real local JSONL persistence, SQL audit queries, OTLP span loading, and standalone dashboard generation without a logging or telemetry server.

## Scope
Exercises `src/repositories/logging_repository.py`, `observability/logging_audit/`, `observability/telemetry_audit/`, and `observability/logging_dashboard/`.

## How to run

```powershell
cd project
uv sync --frozen
uv run --frozen python -m unittest tests.logging.test_logging
```

## Inputs
The test writes uniquely identified events through the production `LoggingRepository` into the gitignored local audit log. No fixture or external service is used.

## Expected outcome
The persisted event retains the exact six-field contract, SQLite returns the written event, malformed logs and spans fail visibly, panels keep the last 20 minutes, and Plotly creates a tabbed HTML file with Overview, Errors, Agents, Questions, Cost, and GT comparison layouts and no external script source.

## Status
Active — 2026-08-29.
