# postman/ — Agent Guide

## Purpose
Postman collections + environments for manually exercising the microservice's HTTP API. Used by developers, QA, and integration partners. Not consumed by the runtime.

## Contains
- `*.postman_collection.json` — exported Postman collections (one per service / domain). Self-contained: endpoints and docs credentials are baked directly into each request — no separate environment file.
- Optional `README.md` per collection describing what it covers.

## Coding Rules (specific to this directory)
- Every endpoint in [`../src/routes/`](../src/routes/) should have at least one corresponding Postman request — happy path minimum.
- Endpoints and credentials are inline per request (no `{{variable}}` placeholders, no environment file). Real tokens live in each developer's local copy, never committed with real values.
- Multiple environments are modeled as one top-level folder per environment (`Local` / `Dev` / `Preprod` / `Prod`), each holding the full request set with its base URL baked into every request.
- Enumerated endpoint options get one dedicated request each — never a single request the user must edit. Every use case under [`../test_data_generator/data/use_cases/`](../test_data_generator/data/use_cases/) (`ambulatory`, `pension_redemption`, `underwriting`) is its own request with `use_case` baked into the body, plus one "all use cases" request (`""`) — in every environment folder.
- Each request carries an example response in the `example` block — keeps the collection self-documenting.
- Re-export from Postman after every meaningful change (new route, contract change). Stale collections are worse than missing ones.
- Collection name + filename must match the service / domain (e.g. `example_feature.postman_collection.json` for [`../src/routes/example_feature.py`](../src/routes/example_feature.py:1)).

## Forbidden in this directory
- No real credentials, no production tokens, no real customer PII in saved examples.
- No executable code — `.json` files only (plus optional `.md`).
- No production hosts baked into requests without an explicit warning.

## See Also
- [`../src/routes/AGENTS.md`](../src/routes/AGENTS.md:1) — the API surface the collections exercise.
