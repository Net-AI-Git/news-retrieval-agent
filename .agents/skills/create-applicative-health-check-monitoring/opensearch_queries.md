# OpenSearch PPL Queries — <PROJECT_DISPLAY_NAME> Health Alerts

These queries detect dependency health-check failures emitted through OpenTelemetry. They cover both `/applicative-health-check` and `/redis-queues-check` because probe failures use a `process` value matching `is_healthy*`.

Assumptions:
- Logs are stored in `<OPENSEARCH_LOG_INDEX_PATTERN>`.
- `resource.attributes.service.name` equals `<OTEL_SERVICE_NAME>`.
- The JSON event is stored in the OpenTelemetry `body` field.

Validate both production values before publishing an alert.

## Alert — `<ALERT_NAME>`

**Trigger**: any health-check ERROR event from `<microservice_slug>` in the last 15 minutes.

```ppl
source=<OPENSEARCH_LOG_INDEX_PATTERN>
| where `resource.attributes.service.name` = '<OTEL_SERVICE_NAME>'
| where time >= date_sub(now(), INTERVAL 15 MINUTE)
| where severityText = 'ERROR'
| spath input=body path=process output=process
| where process LIKE 'is_healthy%'
| stats count() as count by process
| where count > 0
| sort - count
```

**Alert condition**: trigger if `count >= 1` for any row.

## Bonus Alert (optional) — Application Down

Create one monitor per service. It detects when that service produced no logs during the last 15 minutes.

```ppl
source=<OPENSEARCH_LOG_INDEX_PATTERN>
| where `resource.attributes.service.name` = '<OTEL_SERVICE_NAME>'
| where time >= date_sub(now(), INTERVAL 15 MINUTE)
| stats count() as count
| where count = 0
```

**Alert condition**: trigger if one row remains.

## Sample event body

```json
{
  "status": "ERROR",
  "level": "ERROR",
  "process": "is_healthy",
  "content": {
    "error": "ConnectionError('Cannot connect to redis-host:6379')",
    "queue_id": "<REDIS_QUEUE_CONST_NAME>"
  },
  "flow_id": "9b5c-..."
}
```
