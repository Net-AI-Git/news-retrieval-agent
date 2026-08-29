---
name: create-opensearch-tech-dashboard
description: Build or review an OpenSearch technical dashboard for one microservice or a multi-service pipeline using emitted OpenTelemetry log events. Enforces PPL, saved-object, performance, and UX rules under `project/opensearch_dashboard`.
---

# create-opensearch-tech-dashboard

## Purpose

Create or review an OpenSearch Dashboards saved-object export under [`project/opensearch_dashboard/`](../../../project/opensearch_dashboard/) using events already emitted by `OpenSearchRepository.log_event(...)`. The skill reads instrumentation and manages dashboard artifacts only; it never changes application code, probes, endpoints, or alerts.

## Required Input

- Target dashboard name and output path. Default to `project/opensearch_dashboard/<dashboard_name>.ndjson`.
- Target microservice names and their exact `OTEL_SERVICE_NAME` values.
- Log index pattern. Default to `logs-otel-v1*` only when confirmed by the deployed stack.
- Dashboard purpose and requested KPIs.
- OpenSearch Dashboards version when creating or structurally editing NDJSON.

Ask one focused question if any required value is unknown.

## Procedure

### Step 1 — Discover the emitted fields
- Read every relevant `OpenSearchRepository.log_event(...)` call and inventory `status`, `content.*`, `flow_id`, and `trace_id`.
- Every dashboard field must trace to emitted code or a standard OpenTelemetry field.
- For multiple services, inspect every service and consolidate the inventory.

### Step 2 — Plan the queries
- Scope every query to the confirmed index pattern and `resource.attributes.service.name`.
- Filter indexed fields before parsing `body`.
- Use `spath input=body` only for JSON fields that are not already emitted as OpenTelemetry attributes.
- Use `time`, `severityText`, `traceId`, and `spanId` from the OpenTelemetry log schema.
- Reuse one saved query when panels share identical filtering and aggregation.

### Step 3 — Plan panels
Include only panels supported by emitted data, in this order:
1. Overview KPIs.
2. Per-service summary.
3. Domain panels.
4. Errors by service, process, and time.
5. Optional health-check panel.

### Step 4 — Write versioned artifacts
- Store panel queries in `<dashboard_name>.ppl` or `queries/`.
- Store the matching OpenSearch Dashboards export in `<dashboard_name>.ndjson`.
- Structural saved-object changes must be made against the confirmed OpenSearch Dashboards version and re-exported.
- Never embed credentials, production endpoints, saved results, or PII.

### Step 5 — Verify
- Execute or explain every PPL query against the target OpenSearch version when a connection is available.
- Confirm every query is service-scoped and every referenced field exists.
- Validate each NDJSON line as JSON and confirm its panel queries match the saved `.ppl` files.
- Report created files and requested KPIs that lack backing fields.

## Query Rules

- Status counts: extract `status` from `body`, then aggregate by status.
- Flow tracing: filter `attributes.event.flow_id`, select `time`, `traceId`, process, and severity, then sort by time.
- Error panels: filter `severityText = 'ERROR'` before parsing error content.
- Latency panels use trace spans from `otel-v1-apm-span-*`; do not infer latency from STARTING and FINISHED log timestamps when spans exist.
- Agent panels use standard `gen_ai.*` span attributes from `otel-v1-apm-span-*`.

## Hard Prohibitions

- Do not invent service names, fields, index patterns, or GenAI attributes.
- Do not query every service by default.
- Do not hand-edit opaque saved-object internals without a confirmed OpenSearch Dashboards version.
- Do not add unsupported panels or duplicate identical queries.
- Do not modify application code or `opensearch_repository.py`.
- Do not write dashboard artifacts outside `project/opensearch_dashboard/` unless the user specifies another path.

## When to Ask Instead of Acting

- The service name, index pattern, dashboard version, purpose, or requested KPI is unclear.
- A requested KPI has no emitted field or trace span.
- The output location is ambiguous.
- No OpenSearch connection is available to validate a structural dashboard change.

Ask one focused question, then stop.
