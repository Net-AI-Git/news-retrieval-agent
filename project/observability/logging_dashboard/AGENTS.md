# logging_dashboard — Agent Guide

## Purpose
Generate a self-contained Plotly HTML dashboard from events written by `LoggingRepository`. The microservice never reads this directory at runtime.

## Contains
- `build_dashboard.py` — reads the `logs` SQLite table and generates the dashboard.
- `README.md` — one-command usage and panel inventory.
- `dashboard.html` — generated locally and never committed.

## Rules
- Every dashboard field must map to `time` or one of the six fields in [`../../docs/logging.md`](../../docs/logging.md).
- Keep the output self-contained with embedded Plotly JavaScript; do not require a server or CDN.
- A log-shape change and its dashboard update belong in the same change set.
- Fail visibly on malformed persisted logs.

## Forbidden
- No credentials, tokens, production hostnames, customer PII, or committed log results.
- No invented fields or panels unsupported by emitted events.
- No runtime imports from application code into this directory.

## See Also
- [`../../docs/logging.md`](../../docs/logging.md)
- [`../../src/repositories/logging_repository.py`](../../src/repositories/logging_repository.py)
- [`../../../.Codex/rules/04-error-and-logging.md`](../../../.Codex/rules/04-error-and-logging.md)
