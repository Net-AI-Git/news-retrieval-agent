# OpenSearch Observability — Offline Environments

Source of truth for how this microservice emits OpenTelemetry logs and queries OpenSearch. The fixed event shape is produced only by [`opensearch_repository.py`](../src/repositories/opensearch_repository.py).

## Sending structured logs through OTLP

`OpenSearchRepository.log_event(...)` writes a JSON body to the OpenTelemetry SDK. The SDK batches records and exports them over OTLP gRPC to the Collector configured by `OTEL_EXPORTER_OTLP_ENDPOINT`. The Collector and Data Prepper own timestamps, buffering, retries, and ingestion into the `logs-otel-v1*` indices.

Every event body has these fields:

```json
{
  "status": "STARTING | FINISHED | ERROR",
  "process": "<calling function name>",
  "content": "<inputs / outputs / error message>",
  "flow_id": "<flow identifier>",
  "trace_id": "<active OpenTelemetry trace identifier or null>",
  "level": "INFO | ERROR"
}
```

`status`, `process`, `flow_id`, and `trace_id` are also emitted as OpenTelemetry attributes under `attributes.event.*`. `service.name` comes from `OTEL_SERVICE_NAME` in [`conts.py`](../src/conts.py). Do not pass `process=` manually.

## Querying with PPL

`OpenSearchRepository.get_data_from_opensearch(query, flow_id)` sends PPL to `POST /_plugins/_ppl` and returns each JDBC-format row as a dictionary. Keep writing and querying as separate paths.

Count lifecycle statuses for one service:

```text
source=logs-otel-v1*
| where `resource.attributes.service.name` = "<OTEL_SERVICE_NAME>"
| spath input=body path=status output=event_status
| stats count() by event_status
```

Trace one flow:

```text
source=logs-otel-v1*
| where `attributes.event.flow_id` = "<FLOW_ID>"
| spath input=body path=process output=process
| fields time, process, severityText, traceId
| sort time
```

Error rate by process:

```text
source=logs-otel-v1*
| where `resource.attributes.service.name` = "<OTEL_SERVICE_NAME>"
| spath input=body path=process output=process
| stats count() as total, sum(case(severityText = "ERROR", 1 else 0)) as errors by process
```

Always scope queries by `resource.attributes.service.name` or another confirmed low-cardinality field. Use indexed OTel attributes for frequent filters and `spath input=body` for nested `content` fields.

## LangGraph agents

Agent code uses `opensearch-genai-observability-sdk-py[langchain]` and exports standard GenAI spans to the same OTLP endpoint. This preserves `traceId` correlation between agent spans and application logs without a vendor-specific trace format.

## Local and production operation

The self-hosted OpenSearch Observability Stack provides OpenSearch, OpenSearch Dashboards, OpenTelemetry Collector, Data Prepper, and Prometheus-compatible metrics locally. It needs no online account; internet is needed only to fetch packages and container images initially.

The upstream Docker Compose is for development and testing. Production deployment must add authentication, RBAC, TLS verification, network isolation, backups, retention, high availability, and capacity testing.

Secrets and endpoints come only from environment variables. Dashboards and saved PPL must change in the same change set whenever the event shape changes.
