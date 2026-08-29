import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from observability.logging_audit.logging_audit_client import LOG_FILE_PATH, open_logs, run_log_query
from observability.logging_dashboard.build_dashboard import GT_METRIC_FIELDS, build_dashboard, load_gt_metrics, load_log_panels, model_rates
from observability.telemetry_audit.telemetry_audit_client import open_spans
from src.repositories.logging_repository import LoggingRepository


def emit_test_event(flow_id):
    return LoggingRepository.log_event(status="ERROR", content={"message": "Unicode check"}, flow_id=flow_id, trace_id="trace-test", level="ERROR")


class LoggingTests(unittest.TestCase):

    def test_log_event_appends_exact_event_shape(self):
        flow_id = str(uuid4())
        lines_before = LOG_FILE_PATH.read_text(encoding="utf-8").splitlines() if LOG_FILE_PATH.exists() else []
        response = emit_test_event(flow_id)
        stored_lines = LOG_FILE_PATH.read_text(encoding="utf-8").splitlines()
        stored_log = json.loads(stored_lines[-1])
        self.assertEqual("written", response)
        self.assertEqual(len(lines_before) + 1, len(stored_lines))
        self.assertEqual({"time", "event"}, set(stored_log))
        self.assertEqual({"status", "process", "content", "flow_id", "trace_id", "level"}, set(stored_log["event"]))
        self.assertEqual({"status": "ERROR", "process": "emit_test_event", "content": {"message": "Unicode check"}, "flow_id": flow_id, "trace_id": "trace-test", "level": "ERROR"}, stored_log["event"])

    def test_sql_query_reads_written_event(self):
        flow_id = str(uuid4())
        emit_test_event(flow_id)
        query_results = run_log_query(f"SELECT status, process, content, flow_id, trace_id, level FROM logs WHERE flow_id = '{flow_id}'")
        self.assertEqual(1, len(query_results))
        self.assertEqual({"message": "Unicode check"}, json.loads(query_results[0]["content"]))
        self.assertEqual({"status": "ERROR", "process": "emit_test_event", "flow_id": flow_id, "trace_id": "trace-test", "level": "ERROR"}, {key: query_results[0][key] for key in ["status", "process", "flow_id", "trace_id", "level"]})

    def test_dashboard_is_self_contained(self):
        dashboard_html = build_dashboard().read_text(encoding="utf-8")
        self.assertIn("Local logs and telemetry dashboard (last 20 minutes)", dashboard_html)
        self.assertIn("Recent errors", dashboard_html)
        self.assertIn("Trace waterfall", dashboard_html)
        self.assertIn("btn-logging", dashboard_html)
        self.assertIn("btn-telemetry", dashboard_html)
        self.assertIn("Question flows", dashboard_html)
        self.assertIn("GT comparison", dashboard_html)
        self.assertIn("Task success %", dashboard_html)
        self.assertIn("Estimated USD", dashboard_html)
        self.assertIn("Plots.resize", dashboard_html)
        self.assertIn("responsive", dashboard_html)
        self.assertNotIn("<script src=", dashboard_html)

    def test_gt_metrics_missing_directory_is_empty(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            loaded = load_gt_metrics(Path(temporary_directory) / "missing")
            self.assertEqual("", loaded["gt_metrics_name"])
            self.assertEqual([], loaded["gt_rows"])

    def test_gt_metrics_missing_fields_fail_visibly(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            Path(temporary_directory, "metrics_bad.csv").write_text("question_id,task_success\nQ01,100\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gt_metrics(temporary_directory)

    def test_gt_metrics_join_question_text_and_success_rate(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            defaults = {}
            for field_name in GT_METRIC_FIELDS:
                defaults[field_name] = "100.0" if field_name.endswith("success") or field_name.endswith("_pct") else ""
            defaults["question_id"] = "Q01"
            defaults["http_status"] = "200"
            defaults["flow_id"] = "flow-gt"
            defaults["failure_agent"] = "none"
            defaults["gt_answer"] = "Yes"
            defaults["predicted_answer"] = "Yes"
            defaults["stop_verdict"] = "on_time"
            defaults["answer_error_type"] = "none"
            total = dict(defaults)
            total["question_id"] = "TOTAL"
            with Path(temporary_directory, "metrics_2026-01-01_00-00-00.csv").open("w", encoding="utf-8-sig", newline="") as metrics_file:
                writer = csv.DictWriter(metrics_file, fieldnames=list(GT_METRIC_FIELDS))
                writer.writeheader()
                writer.writerow(defaults)
                writer.writerow(total)
            loaded = load_gt_metrics(temporary_directory)
            self.assertEqual("Q01", loaded["gt_rows"][0]["question_id"])
            self.assertIn("Sporting News", loaded["gt_rows"][0]["question"])
            self.assertEqual(100.0, loaded["gt_rows"][0]["task_success"])
            self.assertEqual("100.0", loaded["gt_total"]["task_success"])

    def test_model_rate_prefers_mini_before_gpt_41(self):
        self.assertEqual((0.4, 1.6), model_rates("openai/gpt-4.1-mini"))
        self.assertEqual((2.0, 8.0), model_rates("openai/gpt-4.1"))

    def test_span_agent_and_char_token_fallback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            Path(temporary_directory, "spans-char.jsonl").write_text(json.dumps({"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "test"}, "spans": [{"traceId": "aa", "spanId": "bb", "name": "execute_task gather", "startTimeUnixNano": "1000", "endTimeUnixNano": "2000", "attributes": [{"key": "gen_ai.operation.name", "value": {"stringValue": "execute_task"}}, {"key": "gen_ai.request.model", "value": {"stringValue": "openai/gpt-4.1-mini"}}, {"key": "gen_ai.usage.input_tokens", "value": {"stringValue": "[REDACTED]"}}, {"key": "gen_ai.input.messages", "value": {"stringValue": "abcd1234"}}, {"key": "gen_ai.output.messages", "value": {"stringValue": "wxyz"}}, {"key": "flow_id", "value": {"stringValue": "flow-1"}}], "status": {}}]}]}]}) + "\n", encoding="utf-8")
            connection = open_spans(temporary_directory)
            row = connection.execute("SELECT agent, input_tokens, input_chars, output_chars FROM spans").fetchone()
            self.assertEqual(("gather", None, 8, 4), row)
            connection.close()

    def test_missing_and_empty_logs_produce_empty_table(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            connection = open_logs(Path(temporary_directory) / "events.jsonl")
            self.assertEqual(0, connection.execute("SELECT count(*) FROM logs").fetchone()[0])
            connection.close()

    def test_malformed_log_fails_visibly(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            malformed_log_path = Path(temporary_directory) / "events.jsonl"
            malformed_log_path.write_text("not-json\n", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                open_logs(malformed_log_path)

    def test_missing_and_empty_spans_produce_empty_table(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            connection = open_spans(Path(temporary_directory))
            self.assertEqual(0, connection.execute("SELECT count(*) FROM spans").fetchone()[0])
            connection.close()

    def test_malformed_span_fails_visibly(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            Path(temporary_directory, "spans-bad.jsonl").write_text("not-json\n", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                open_spans(Path(temporary_directory))

    def test_log_panels_exclude_events_older_than_lookback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "events.jsonl"
            old_time = (datetime.now(timezone.utc) - timedelta(minutes=21)).isoformat()
            new_time = datetime.now(timezone.utc).isoformat()
            log_path.write_text(json.dumps({"time": old_time, "event": {"status": "ERROR", "process": "old_process", "content": {"message": "old"}, "flow_id": "old-flow", "trace_id": "old-trace", "level": "ERROR"}}) + "\n" + json.dumps({"time": new_time, "event": {"status": "ERROR", "process": "new_process", "content": {"message": "new"}, "flow_id": "new-flow", "trace_id": "new-trace", "level": "ERROR"}}) + "\n", encoding="utf-8")
            connection = open_logs(log_path)
            panels = load_log_panels(connection, (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat())
            self.assertEqual(1, panels["log_total"])
            self.assertEqual("new_process", panels["error_processes"][0][0])
            connection.close()


if __name__ == "__main__":
    unittest.main()
