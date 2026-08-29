import json
import sqlite3
from datetime import datetime
from pathlib import Path


AUDIT_LOG_DIR = Path(__file__).parent / "audit_log"
LOG_FILE_PATH = AUDIT_LOG_DIR / "events.jsonl"


def open_logs(log_file_path=None):
    log_file_path = Path(log_file_path or LOG_FILE_PATH)
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE stored_logs (time TEXT, status TEXT, process TEXT, content TEXT, flow_id TEXT, trace_id TEXT, level TEXT)")
    connection.execute("CREATE VIEW logs AS SELECT * FROM stored_logs")
    if not log_file_path.exists() or log_file_path.stat().st_size == 0:
        return connection
    try:
        with log_file_path.open(encoding="utf-8") as log_file:
            for line in log_file:
                stored_log = json.loads(line)
                event = stored_log["event"]
                connection.execute("INSERT INTO stored_logs VALUES (?, ?, ?, ?, ?, ?, ?)", (stored_log["time"], event["status"], event["process"], json.dumps(event["content"], default=str, ensure_ascii=False), event["flow_id"], event["trace_id"], event["level"]))
    except Exception:
        connection.close()
        raise
    connection.commit()
    return connection


def run_log_query(query):
    connection = open_logs()
    try:
        query_result = connection.execute(query)
        return [dict(zip([field[0] for field in query_result.description], row)) for row in query_result.fetchall()]
    finally:
        connection.close()


def write_audit_file(logs):
    AUDIT_LOG_DIR.mkdir(exist_ok=True)
    audit_file_path = AUDIT_LOG_DIR / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    audit_file_path.write_text(json.dumps(logs, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit_file_path


def export_audit_logs(query):
    print(f"STARTING export_audit_logs, query: {query}")
    audit_file_path = None
    try:
        audit_file_path = write_audit_file(run_log_query(query))
    except Exception as err:
        print(f"ERROR export_audit_logs, error: {repr(err)}")
    print(f"FINISHED export_audit_logs, file: {audit_file_path}")
    return audit_file_path
