# opensearch_audit

Standalone tool for running PPL against OpenSearch and saving the results as timestamped JSON.

## Setup

Fill the OpenSearch connection values, `OPENSEARCH_LOG_INDEX_PATTERN`, and `OTEL_SERVICE_NAME` in `project/.env` (see `project/.env.example`).

## Usage

1. Edit `PPL_FILTER` in [`run_audit.py`](run_audit.py).
2. Run `python run_audit.py` from this directory.
3. Read `audit_log/audit_<YYYYMMDD_HHMMSS>.json`.

The base query always scopes both the configured log index pattern and service name. Add filtering, aggregation, and time conditions only in `PPL_FILTER`.

Examples:

| Goal | PPL_FILTER |
|---|---|
| Errors | `\| where severityText = 'ERROR' \| sort - time \| head 500` |
| One flow | `\| where \`attributes.event.flow_id\` = 'abc-123' \| sort time` |
| Count by process | `\| spath input=body path=process output=process \| stats count() by process` |

Do not edit [`opensearch_audit_client.py`](opensearch_audit_client.py) unless the OpenSearch connection contract itself changes.
