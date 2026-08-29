import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from local_logging_audit.local_logging_audit_client import LOCAL_LOG_FILE_PATH, open_local_logs, run_local_log_query
from local_logging_dashboard.build_dashboard import build_dashboard
from src.repositories.local_logging_repository import LocalLoggingRepository


def emit_test_event(flow_id):
    return LocalLoggingRepository.log_event(status="ERROR", content={"message": "בדיקת Unicode"}, flow_id=flow_id, trace_id="trace-test", level="ERROR")


class LocalLoggingTests(unittest.TestCase):

    def test_log_event_appends_exact_event_shape(self):
        flow_id = str(uuid4())
        lines_before = LOCAL_LOG_FILE_PATH.read_text(encoding="utf-8").splitlines() if LOCAL_LOG_FILE_PATH.exists() else []
        response = emit_test_event(flow_id)
        stored_lines = LOCAL_LOG_FILE_PATH.read_text(encoding="utf-8").splitlines()
        stored_log = json.loads(stored_lines[-1])
        self.assertEqual("written", response)
        self.assertEqual(len(lines_before) + 1, len(stored_lines))
        self.assertEqual({"time", "event"}, set(stored_log))
        self.assertEqual({"status", "process", "content", "flow_id", "trace_id", "level"}, set(stored_log["event"]))
        self.assertEqual({"status": "ERROR", "process": "emit_test_event", "content": {"message": "בדיקת Unicode"}, "flow_id": flow_id, "trace_id": "trace-test", "level": "ERROR"}, stored_log["event"])

    def test_sql_query_reads_written_event(self):
        flow_id = str(uuid4())
        emit_test_event(flow_id)
        query_results = run_local_log_query(f"SELECT status, process, content, flow_id, trace_id, level FROM local_logs WHERE flow_id = '{flow_id}'")
        self.assertEqual(1, len(query_results))
        self.assertEqual({"message": "בדיקת Unicode"}, json.loads(query_results[0]["content"]))
        self.assertEqual({"status": "ERROR", "process": "emit_test_event", "flow_id": flow_id, "trace_id": "trace-test", "level": "ERROR"}, {key: query_results[0][key] for key in ["status", "process", "flow_id", "trace_id", "level"]})

    def test_dashboard_is_self_contained(self):
        dashboard_html = build_dashboard().read_text(encoding="utf-8")
        self.assertIn("Local logging dashboard", dashboard_html)
        self.assertIn("Recent errors", dashboard_html)
        self.assertNotIn("<script src=", dashboard_html)

    def test_missing_and_empty_logs_produce_empty_table(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            connection = open_local_logs(Path(temporary_directory) / "events.jsonl")
            self.assertEqual(0, connection.execute("SELECT count(*) FROM local_logs").fetchone()[0])
            connection.close()

    def test_malformed_log_fails_visibly(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            malformed_log_path = Path(temporary_directory) / "events.jsonl"
            malformed_log_path.write_text("not-json\n", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                open_local_logs(malformed_log_path)


if __name__ == "__main__":
    unittest.main()
