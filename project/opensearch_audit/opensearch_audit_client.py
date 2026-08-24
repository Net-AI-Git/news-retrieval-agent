import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from opensearchpy import OpenSearch

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OPENSEARCH_CLIENT = OpenSearch(hosts=[{"host": os.getenv("OPENSEARCH_HOST"), "port": int(os.getenv("OPENSEARCH_PORT"))}], http_auth=(os.getenv("OPENSEARCH_USER"), os.getenv("OPENSEARCH_PASSWORD")), use_ssl=os.getenv("OPENSEARCH_USE_SSL").lower() == "true", verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS").lower() == "true", ssl_assert_hostname=False, ssl_show_warn=False, http_compress=True, max_retries=3, retry_on_timeout=True)
AUDIT_LOG_DIR = Path(__file__).parent / "audit_log"


def run_opensearch_query(query):
    query_response = OPENSEARCH_CLIENT.transport.perform_request("POST", "/_plugins/_ppl", body={"query": query})
    field_names = [field["name"] for field in query_response.get("schema", [])]
    return [dict(zip(field_names, row)) for row in query_response.get("datarows", [])]


def write_audit_file(opensearch_logs):
    AUDIT_LOG_DIR.mkdir(exist_ok=True)
    audit_file_path = AUDIT_LOG_DIR / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    audit_file_path.write_text(json.dumps(opensearch_logs, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit_file_path


def pull_audit_logs(query):
    print(f"STARTING pull_audit_logs, query: {query}")
    audit_file_path = None
    try:
        audit_file_path = write_audit_file(run_opensearch_query(query))
    except Exception as err:
        print(f"ERROR pull_audit_logs, error: {repr(err)}")
    print(f"FINISHED pull_audit_logs, file: {audit_file_path}")
    return audit_file_path
