import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from opentelemetry import baggage, trace
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_AGENT_NAME, GEN_AI_INPUT_MESSAGES, GEN_AI_OPERATION_NAME, GEN_AI_OUTPUT_MESSAGES
from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE
from opentelemetry.semconv.attributes.exception_attributes import EXCEPTION_TYPE
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Link, Status, StatusCode

from ..conts import TELEMETRY_DIRECTORY_PATH, OTEL_SERVICE_NAME, TELEMETRY_EVENT_DETAILS_ATTRIBUTE, TELEMETRY_FILE_PREFIX, TELEMETRY_FLOW_ID_ATTRIBUTE, TELEMETRY_REDACTED_VALUE, TELEMETRY_SECRET_KEY_PARTS, TELEMETRY_SECRET_VALUE_MARKERS, TELEMETRY_WORKFLOW_OPERATION_NAME


class FlowIdSpanProcessor(SpanProcessor):

    def on_start(self, span, parent_context=None):
        flow_id = baggage.get_baggage(TELEMETRY_FLOW_ID_ATTRIBUTE, parent_context) or baggage.get_baggage(TELEMETRY_FLOW_ID_ATTRIBUTE)
        if flow_id:
            span.set_attribute(TELEMETRY_FLOW_ID_ATTRIBUTE, flow_id)


class RedactingSpanExporter(SpanExporter):

    def __init__(self, exporter):
        self.exporter = exporter

    def export(self, spans):
        return self.exporter.export([TelemetryRepository.redact_span(span) for span in spans])

    def shutdown(self):
        self.exporter.shutdown()
        return

    def force_flush(self, timeout_millis=30000):
        return self.exporter.force_flush(timeout_millis)


class TelemetryRepository:

    lock = threading.Lock()
    provider = None

    @staticmethod
    def redact_data(value, key_name=""):
        if key_name and any(secret_part in key_name.lower() for secret_part in TELEMETRY_SECRET_KEY_PARTS):
            return TELEMETRY_REDACTED_VALUE
        if isinstance(value, str) and any(secret_marker in value.lower() for secret_marker in TELEMETRY_SECRET_VALUE_MARKERS):
            return TELEMETRY_REDACTED_VALUE
        if isinstance(value, dict):
            return {key: TelemetryRepository.redact_data(item, str(key)) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [TelemetryRepository.redact_data(item) for item in value]
        return value

    @staticmethod
    def serialize_data(value):
        return json.dumps(TelemetryRepository.redact_data(value), default=str, ensure_ascii=False)

    @staticmethod
    def redact_attributes(attributes):
        return {key: TelemetryRepository.redact_data(value, key) for key, value in (attributes or {}).items()}

    @staticmethod
    def redact_span(span):
        events = [Event(event.name, TelemetryRepository.redact_attributes(event.attributes), event.timestamp) for event in span.events]
        links = [Link(link.context, TelemetryRepository.redact_attributes(link.attributes)) for link in span.links]
        resource = Resource(TelemetryRepository.redact_attributes(span.resource.attributes), span.resource.schema_url)
        return ReadableSpan(name=span.name, context=span.context, parent=span.parent, resource=resource, attributes=TelemetryRepository.redact_attributes(span.attributes), events=events, links=links, kind=span.kind, status=Status(span.status.status_code), start_time=span.start_time, end_time=span.end_time, instrumentation_scope=span.instrumentation_scope)

    @staticmethod
    def create_provider():
        from opentelemetry.exporter.otlp.json.file import FileSpanExporter
        Path(TELEMETRY_DIRECTORY_PATH).mkdir(parents=True, exist_ok=True)
        telemetry_file_path = Path(TELEMETRY_DIRECTORY_PATH) / f"{TELEMETRY_FILE_PREFIX}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{os.getpid()}.jsonl"
        provider = TracerProvider(sampler=ParentBased(ALWAYS_ON), resource=Resource.create({ResourceAttributes.SERVICE_NAME: OTEL_SERVICE_NAME}))
        provider.add_span_processor(FlowIdSpanProcessor())
        provider.add_span_processor(SimpleSpanProcessor(RedactingSpanExporter(FileSpanExporter(telemetry_file_path))))
        trace.set_tracer_provider(provider)
        return provider

    @staticmethod
    def instrument_langchain(provider):
        try:
            from opentelemetry.instrumentation.langchain import LangchainInstrumentor
            LangchainInstrumentor().instrument(tracer_provider=provider)
        except Exception as err:
            print(f"ERROR instrument_langchain, error: {repr(err)}", file=sys.stderr)
        return

    @staticmethod
    def initialize():
        if (os.getenv(OTEL_SDK_DISABLED) or "").strip().lower() == "true":
            return trace.get_tracer(OTEL_SERVICE_NAME)
        with TelemetryRepository.lock:
            if TelemetryRepository.provider is None:
                TelemetryRepository.provider = TelemetryRepository.create_provider()
                TelemetryRepository.instrument_langchain(TelemetryRepository.provider)
        return trace.get_tracer(OTEL_SERVICE_NAME, tracer_provider=TelemetryRepository.provider)

    @staticmethod
    def start_span(operation_name, entity_name, flow_id, task_data):
        span_context = baggage.set_baggage(TELEMETRY_FLOW_ID_ATTRIBUTE, flow_id) if operation_name == TELEMETRY_WORKFLOW_OPERATION_NAME else None
        attributes = {GEN_AI_OPERATION_NAME: operation_name, GEN_AI_INPUT_MESSAGES: TelemetryRepository.serialize_data(task_data), TELEMETRY_FLOW_ID_ATTRIBUTE: flow_id}
        if operation_name == TELEMETRY_WORKFLOW_OPERATION_NAME:
            attributes[GEN_AI_AGENT_NAME] = entity_name
        return TelemetryRepository.initialize().start_as_current_span(f"{operation_name} {entity_name}", context=span_context, attributes=attributes, record_exception=False, set_status_on_exception=False)

    @staticmethod
    def record_output(span, output):
        span.set_attribute(GEN_AI_OUTPUT_MESSAGES, TelemetryRepository.serialize_data(output))
        return

    @staticmethod
    def record_error(span, err):
        span.set_attribute(ERROR_TYPE, type(err).__name__)
        span.add_event("exception", attributes={EXCEPTION_TYPE: type(err).__name__})
        span.set_status(Status(StatusCode.ERROR, type(err).__name__))
        return

    @staticmethod
    def add_event(event_name, event_data):
        trace.get_current_span().add_event(event_name, attributes={TELEMETRY_EVENT_DETAILS_ATTRIBUTE: TelemetryRepository.serialize_data(event_data)})
        return
