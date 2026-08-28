---
name: create-local-logging-dashboard
description: Build or review a standalone Plotly dashboard from LocalLoggingRepository JSONL events. Enforces emitted-field, SQL, portability, and UX rules under project/local_logging_dashboard.
---

# create-local-logging-dashboard

## Purpose

Create or review the self-contained dashboard under [`project/local_logging_dashboard/`](../../../project/local_logging_dashboard/) using events emitted by `LocalLoggingRepository.log_event(...)`. The skill manages dashboard artifacts only; it never changes application behavior, probes, endpoints, or alerts.

## Required Input

- Dashboard purpose and requested KPIs.
- Target services or workflows whose emitted events must be represented.
- Any required filters beyond the standard `time`, `status`, `process`, `flow_id`, `trace_id`, and `level` columns.

Ask one focused question only when a required product decision cannot be derived from emitted fields.

## Procedure

### Step 1 — Discover emitted fields
- Read [`project/docs/local_logging.md`](../../../project/docs/local_logging.md), the dashboard directory `AGENTS.md`, and every relevant `LocalLoggingRepository.log_event(...)` call.
- Inventory `status`, `content.*`, `flow_id`, `trace_id`, and `level` without inventing fields.

### Step 2 — Plan SQL
- Query only the in-memory SQLite `local_logs` view created by `local_logging_audit_client.py`.
- Filter before aggregating and reuse one result when panels need the same data.
- Keep user-selected SQL in the audit runner; dashboard queries stay inside `build_dashboard.py`.

### Step 3 — Plan panels
Include only panels supported by emitted data, in this order:
1. Overview totals.
2. Status summary.
3. Errors by process.
4. Event timeline.
5. Recent errors.

### Step 4 — Write artifacts
- Update `build_dashboard.py` and its README together.
- Generate only `dashboard.html`; keep it gitignored and embed Plotly JavaScript in the file.
- Never embed credentials, production endpoints, saved customer data, or external CDN dependencies.

### Step 5 — Verify
- Run `uv run python -m local_logging_dashboard.build_dashboard` from `project/`.
- Confirm the HTML exists, contains the requested panels, and has no CDN URL.
- Run every SQL query against both populated and empty local logs.
- Report requested KPIs that lack backing fields.

## Hard Prohibitions

- Do not invent fields, traces, latency, or service names.
- Do not require Docker, an external datastore, a local server, an account, or an internet connection after installation.
- Do not modify application instrumentation or `local_logging_repository.py`.
- Do not commit `dashboard.html` or generated audit/log files.
- Do not write dashboard artifacts outside `project/local_logging_dashboard/` unless the user specifies another path.

## When to Ask Instead of Acting

- The dashboard purpose or requested KPI is unclear.
- A requested KPI has no emitted field.
- The output location differs from the project default.

Ask one focused question, then stop.
