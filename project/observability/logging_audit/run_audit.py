from local_logging_audit.local_logging_audit_client import export_audit_logs


AUDIT_QUERY = "SELECT * FROM local_logs WHERE level = 'ERROR' ORDER BY time DESC LIMIT 500"


if __name__ == "__main__":
    export_audit_logs(AUDIT_QUERY)
