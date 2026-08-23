# data/ — Agent Guide

## Purpose
Local fixtures, sample documents, and static datasets used for **manual testing and development only**. Not consumed by production code paths.

## Contains
- [`test_data.py`](test_data.py:1) — Python module with sample payloads / hardcoded inputs for ad-hoc runs.
- Sample fixtures (`.json`, `.txt`, etc.) — anonymized examples that mirror production shapes.

## Coding Rules (specific to this directory)
- Treat as **read-only at runtime** — production code MUST NOT import from this directory.
- Fixtures used by automated tests live in [`../../tests/`](../../tests/), not here.
- Sample documents must be anonymized — no real PII, no real customer identifiers.
- New large binaries → check size before committing. Prefer `.gitignore` + a download script over committing > 1 MB blobs.

## Forbidden in this directory
- No imports **from** this directory into [`../services/`](../services/), [`../repositories/`](../repositories/), [`../routes/`](../routes/), [`../schemas/`](../schemas/).
- No production secrets, no real customer data.
- No transient temp files (`~$*`, `*.tmp`) — those should be `.gitignore`d.

## See Also
- [`../../tests/AGENTS.md`](../../tests/AGENTS.md:1) — test fixtures and automated test data.
