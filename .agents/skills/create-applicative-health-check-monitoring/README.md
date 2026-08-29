# <PROJECT_DISPLAY_NAME> Monitoring — Megi Submission Package

This folder contains everything needed to submit a "הקמת ניטור אפליקטיבי" request via Megi for the **<PROJECT_DISPLAY_NAME>** project (<N> microservices in production).

## 📂 Files in this folder

| File | Purpose |
|---|---|
| [`README.md`](README.md) | This file — entry point and instructions |
| [`megi_form_values.md`](megi_form_values.md) | Copy-paste values for each field in the Megi form |
| [`alerts_specification.md`](alerts_specification.md) | Full specification of the <N> OpenSearch alerts (human-readable) |
| [`opensearch_queries.md`](opensearch_queries.md) | OpenSearch PPL queries (extracted, copy-paste ready) |
| [`<microservice_slug>_alerts.xlsx`](<microservice_slug>_alerts.xlsx) | Excel attachment for the **<microservice_slug>** Megi request |
| [`generate_excel.py`](generate_excel.py) | Script that regenerates the xlsx files if specifications change |

## 📋 What is being monitored

Each microservice exposes **two** monitor endpoints:

### Endpoint 1 — `/api/monitor/applicative-health-check` (external dependencies)

| # | Microservice | Dependencies checked |
|---|---|---|
| 1 | `<microservice_slug>` | <comma-separated dependency labels> |

### Endpoint 2 — `/api/monitor/redis-queues-check` (Redis queues + depth)

| # | Microservice | Queues checked |
|---|---|---|
| 1 | `<microservice_slug>` | `<REDIS_QUEUE_CONST_NAME>` |

The Redis check returns `service_name` + `queue_depth` (current number of pending items in the queue) — **only**. It is not a health probe (Redis connectivity surfaces in `applicative-health-check`'s `Redis` entry); on failure `RedisRepository.get_queue_statuses` emits an OpenSearch `ERROR` event and returns `[]`.

> ⚠️ The URLs are inferred from the OpenShift route name pattern. **Verify the exact OpenShift route names before submitting.**

## 🔔 The <N> alerts being requested

Each alert fires when the corresponding microservice's `/api/monitor/applicative-health-check` endpoint reports any external dependency as unhealthy (`is_ok=false`).

| # | Alert Name | Severity | Frequency |
|---|---|---|---|
| 1 | `<ALERT_NAME>` | Critical | Every 10 min |

## ✅ Submission checklist (Megi)

1. [ ] Verify the production URLs are correct (consult DevOps).
2. [ ] Open Megi → "שירותי ניטור" → "הקמת ניטור אפליקטיבי".
3. [ ] Fill all form fields using values from [`megi_form_values.md`](megi_form_values.md).
4. [ ] Submit 1 request per microservice. For each request, attach the matching xlsx file.
5. [ ] Send contact info to `<NOC_CONTACT_EMAIL>` (Hebrew email template ready in [`megi_form_values.md`](megi_form_values.md) — section "📧 מייל ל-NOC"):
    - Recipient: `<CONTACT_NAME> — <CONTACT_EMAIL> — <CONTACT_PHONE>`
    - Notification group: `<NOTIFICATION_GROUP>`

## 🛠️ Underlying implementation

- Each microservice exposes two endpoints under `/api/monitor`: `applicative-health-check` (returns `list[ServiceStatus]` — `service_name`, `is_ok`, `description`) and `redis-queues-check` (returns `list[RedisQueueStatus]` — `service_name`, `queue_depth`). Both Pydantic models live in `<service_pkg>/schemas/monitor.py` and are imported by `repositories/redis_repository.py`, `services/healthcheck_service.py`, and `routes/monitor.py`.
- All probes reuse the **existing repository singletons** — no new clients/engines are created. A breakage in any repo's init will surface in the monitor.
- Oracle probes (`OracleRepository.is_healthy*`) execute `SELECT COUNT(*)` against the main business table of each DB — proving connectivity, authentication, AND read permission on production data, not just the listener.
- Redis probe (`RedisRepository.is_healthy`) executes `RedisRepository.r.llen("queue:<name>")` purely as a connectivity probe (return value discarded). Returns `(is_healthy, error_message)` — same shape as every other probe.
- `/applicative-health-check` delegates to `HealthCheckService.run_health_check`, which fans out probes via `ThreadPoolExecutor` and assembles `list[ServiceStatus]` — every per-dependency probe is called inline (no `test_*` wrapper functions).
- `/redis-queues-check` delegates directly to `RedisRepository.get_queue_statuses`, which calls `RedisRepository.r.llen("queue:<name>")` per queue to populate `queue_depth` — Redis-queue depth is a Redis concern, not a health-check concern, so `HealthCheckService` is not involved.
- Every probe writes structured logs to OpenSearch from inside its repo/service (`status=STARTING|FINISHED|ERROR`, `process=<auto-detected function name>`, `content.error` on failure). Probes never `raise` — they absorb the exception, log it, and return `(False, ...)`.
- The <N> alerts are OpenSearch PPL alerts running every 10 min, querying these logs for any ERROR event with `process` matching `is_healthy*`.
