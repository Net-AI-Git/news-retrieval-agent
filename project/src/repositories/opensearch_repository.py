import inspect
import json
import logging
import os

from dotenv import load_dotenv
from opensearchpy import OpenSearch
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from ..conts import OTEL_SERVICE_NAME

load_dotenv()


class OpenSearchRepository:
    client = OpenSearch(hosts=[{"host": os.getenv("OPENSEARCH_HOST"), "port": int(os.getenv("OPENSEARCH_PORT"))}], http_auth=(os.getenv("OPENSEARCH_USER"), os.getenv("OPENSEARCH_PASSWORD")), use_ssl=os.getenv("OPENSEARCH_USE_SSL").lower() == "true", verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS").lower() == "true", ssl_assert_hostname=False, ssl_show_warn=False, http_compress=True, max_retries=3, retry_on_timeout=True)
    logger_provider = LoggerProvider(resource=Resource.create({"service.name": OTEL_SERVICE_NAME}))
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"), insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE").lower() == "true")))
    set_logger_provider(logger_provider)
    logger = logging.getLogger(OTEL_SERVICE_NAME)
    logger.setLevel(logging.INFO)
    logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

    @staticmethod
    def log_event(status, process=None, content=None, flow_id=None, trace_id=None, level=None):
        response = None
        try:
            process = process or inspect.stack()[1].function
            span_context = trace.get_current_span().get_span_context()
            trace_id = trace_id or (format(span_context.trace_id, "032x") if span_context.is_valid else None)
            event = {"status": status, "process": process, "content": content, "flow_id": flow_id, "trace_id": trace_id, "level": level}
            OpenSearchRepository.logger.log(getattr(logging, level or "INFO"), json.dumps(event, default=str, ensure_ascii=False), extra={"event.status": status, "event.process": process, "event.flow_id": flow_id or "", "event.trace_id": trace_id or ""})
            response = "queued"
        except Exception as err:
            response = f"ERROR log_to_opensearch, error: {repr(err)}, full error: {err.__cause__}"
            OpenSearchRepository.logger.exception(response)
        return response

    @staticmethod
    def publish_metrics(metric, metric_id):
        response = None
        try:
            metric["metric_id"] = metric_id
            OpenSearchRepository.logger.info(json.dumps(metric, default=str, ensure_ascii=False), extra={"event.kind": "metric", "event.metric_id": metric_id})
            response = "queued"
        except Exception as err:
            response = f"ERROR publish_metrics, error: {repr(err)}, full error: {err.__cause__}"
            OpenSearchRepository.logger.exception(response)
        return response

    @staticmethod
    def get_data_from_opensearch(query, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=query, flow_id=flow_id, level="INFO")
        opensearch_logs = []
        try:
            query_response = OpenSearchRepository.client.transport.perform_request("POST", "/_plugins/_ppl", body={"query": query})
            field_names = [field["name"] for field in query_response.get("schema", [])]
            opensearch_logs = [dict(zip(field_names, row)) for row in query_response.get("datarows", [])]
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "full_error": err.__cause__}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content={"opensearch_logs_retrieved": bool(opensearch_logs)}, flow_id=flow_id, level="INFO")
        return opensearch_logs
