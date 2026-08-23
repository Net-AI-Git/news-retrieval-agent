# opensearch_dashboard/ — Agent Guide

## Purpose
Version-controlled OpenSearch Dashboards saved objects and the PPL queries that power them. The microservice never reads this directory at runtime.

## Contains
- `*.ndjson` — saved-object exports from OpenSearch Dashboards, one dashboard export per file.
- `*.ppl` — reviewable PPL queries used by the matching dashboard.
- Optional `README.md` files describing the monitored service, index pattern, variables, and alerts.

## Rules
- One dashboard export per `snake_case` file.
- Every `<name>.ndjson` MUST have a matching `<name>.ppl` or `queries/` directory.
- Queries MUST consume `OpenSearchRepository.log_event(...)` records from `logs-otel-v1*` and match the `status`, `flow_id`, `trace_id`, and `content` contract in [`../docs/opensearch.md`](../docs/opensearch.md:1).
- Every query MUST scope by a confirmed `resource.attributes.service.name`; never query every service by default.
- Re-export NDJSON after every structural dashboard change. Keep PPL synchronized with the exported panels.
- A log-shape change and its dashboard updates belong in the same change set.

## Forbidden
- No executable code.
- No runtime imports from this directory.
- No credentials, tokens, production hostnames, customer PII, or saved results.
- No invented fields; every queried field must trace to an emitted log or OpenTelemetry semantic convention.

## See Also
- [`../docs/opensearch.md`](../docs/opensearch.md:1)
- [`../src/repositories/opensearch_repository.py`](../src/repositories/opensearch_repository.py:1)
- [`../../.Codex/rules/04-error-and-logging.md`](../../.Codex/rules/04-error-and-logging.md:1)
