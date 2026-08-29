# Local agent telemetry

## Goal
Verify that production telemetry writes correlated OTLP JSONL spans and lifecycle logs locally without a Collector or network connection.

## Scope
Exercises `src/repositories/telemetry_repository.py` and `src/repositories/logging_repository.py` with real OpenTelemetry SDK processing and file export; LangChain auto-instrumentation is isolated because this test does not execute an agent or network call.

## How to run

```powershell
cd project
uv sync --frozen
uv run --frozen python -m unittest tests.local_agent_telemetry.test_local_agent_telemetry
```

## Inputs
The test creates one temporary workflow span, one child retrieval span, and one lifecycle log containing a synthetic secret field.

## Expected outcome
Both spans share one trace ID and carry the same `flow_id`, the lifecycle log contains that trace ID, the secret value is absent from telemetry, and the exporter creates one local OTLP JSONL process file.

## Status
Active — 2026-08-28.
