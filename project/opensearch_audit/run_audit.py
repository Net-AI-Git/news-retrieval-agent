import os
from opensearch_audit_client import pull_audit_logs

PPL_FILTER = "| where severityText = 'ERROR' | sort - time | head 500"

if __name__ == "__main__":
    pull_audit_logs(f"source={os.getenv('OPENSEARCH_LOG_INDEX_PATTERN')} | where `resource.attributes.service.name` = '{os.getenv('OTEL_SERVICE_NAME')}' {PPL_FILTER}")
