# Alerts Specification — <PROJECT_DISPLAY_NAME> Project

Specification of all <N> OpenSearch alerts for the <PROJECT_DISPLAY_NAME> project. Mirrors the columns of the per-microservice Excel files.

---

## Common values (shared across all alerts)

| Field | Value |
|---|---|
| **Severity Level** | `Critical` (SMS + email) |
| **Alert Frequency** | `Every 10 minutes` |
| **Contact (Person)** | `<CONTACT_NAME> — <CONTACT_EMAIL> — <CONTACT_PHONE>` |
| **Team** | `<TEAM_NAME>` |
| **Notification Group** | `<NOTIFICATION_GROUP>` |

---

## Alert — `<ALERT_NAME>`

| Column | Value |
|---|---|
| **A — Alert Name** | `<ALERT_NAME>` |
| **B — PPL Query** | See [`opensearch_queries.md`](opensearch_queries.md) |
| **C — Description** | Triggered when /api/monitor/applicative-health-check reports an unhealthy dependency for <microservice_slug> (<comma-separated dependency labels>). The Redis dependency is included in /applicative-health-check; /redis-queues-check returns queue depth only and is not used for alerting. |
| **D — Affected Services** | <one-line description of what stage of the pipeline is broken when this microservice is down>. |
| **E — Severity Level** | Critical |
| **F — Action for NOC** | 1) `curl <PRODUCTION_URL_BASE>/api/monitor/applicative-health-check` to identify the failed dependency (look for `is_ok=false`). 2) Restart pod in OpenShift: project `<OPENSHIFT_PROJECT>`, app `<OPENSHIFT_APP>`. 3) Re-run after 30s. 4) If still failing after 2 cycles, escalate to <CONTACT_NAME> (<CONTACT_EMAIL>, <CONTACT_PHONE>). |
| **G — Contact Info** | Primary: <CONTACT_NAME> — <CONTACT_EMAIL> — <CONTACT_PHONE>. Team: <TEAM_NAME>. Notification group: <NOTIFICATION_GROUP>. |
| **H — Alert Frequency** | Every 10 minutes |
