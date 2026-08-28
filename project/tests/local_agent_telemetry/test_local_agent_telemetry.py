import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from src import conts


TEST_TEMP_DIRECTORY_PATH = Path(__file__).resolve().parents[1] / "tmp"


def execute_local_telemetry_scenario(temporary_directory):
    conts.LOCAL_LOG_FILE_PATH = str(Path(temporary_directory) / "events.jsonl")
    conts.LOCAL_TELEMETRY_DIRECTORY_PATH = temporary_directory
    from src.repositories.local_logging_repository import LocalLoggingRepository
    from src.repositories.local_telemetry_repository import LocalTelemetryRepository
    flow_id = str(uuid4())
    task_data = {"question": "telemetry test", "api_key": "must-not-appear"}
    with patch.object(LocalTelemetryRepository, "instrument_langchain"):
        with LocalTelemetryRepository.start_span(conts.TELEMETRY_WORKFLOW_OPERATION_NAME, conts.TELEMETRY_WORKFLOW_NAME, flow_id, task_data) as workflow_span:
            trace_id = format(workflow_span.get_span_context().trace_id, "032x")
            workflow_span.set_attribute("auto.input", '{"authorization":"Bearer must-not-appear-auto"}')
            workflow_span.add_event("auto.event", {"exception.message": "opaque-private-value", "tool.arguments": '{"api_key":"must-not-appear-event"}'})
            LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
            with LocalTelemetryRepository.start_span(conts.TELEMETRY_RETRIEVAL_OPERATION_NAME, conts.TELEMETRY_RETRIEVAL_NAME, flow_id, task_data) as retrieval_span:
                LocalTelemetryRepository.record_output(retrieval_span, {"results": ["evidence"]})
            LocalTelemetryRepository.record_output(workflow_span, {"answer": "done"})
    LocalTelemetryRepository.provider.shutdown()
    for handler in LocalLoggingRepository.logger.handlers:
        handler.close()
    LocalLoggingRepository.logger.handlers.clear()
    telemetry_text = next(Path(temporary_directory).glob("spans-*.jsonl")).read_text(encoding="utf-8")
    stored_log = json.loads(Path(conts.LOCAL_LOG_FILE_PATH).read_text(encoding="utf-8").splitlines()[-1])
    return flow_id, trace_id, telemetry_text, stored_log


class LocalAgentTelemetryTests(unittest.TestCase):

    def test_spans_and_log_share_trace_without_secret(self):
        temporary_directory = TEST_TEMP_DIRECTORY_PATH / f"local_agent_telemetry_{uuid4()}"
        temporary_directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, temporary_directory, ignore_errors=True)
        flow_id, trace_id, telemetry_text, stored_log = execute_local_telemetry_scenario(temporary_directory)
        self.assertEqual(trace_id, stored_log["event"]["trace_id"])
        self.assertEqual(2, len(telemetry_text.splitlines()))
        self.assertGreaterEqual(telemetry_text.count(flow_id), 2)
        self.assertIn("invoke_workflow grounded_answering", telemetry_text)
        self.assertIn("retrieval knowledge", telemetry_text)
        self.assertIn(conts.TELEMETRY_REDACTED_VALUE, telemetry_text)
        self.assertNotIn("must-not-appear", telemetry_text)
        self.assertNotIn("opaque-private-value", telemetry_text)


if __name__ == "__main__":
    unittest.main()
