import json
import sqlite3
from pathlib import Path


TELEMETRY_DIRECTORY_PATH = Path(__file__).resolve().parents[1] / "telemetry"
BOUNDED_TEXT_CHARS = 300


def read_otlp_value(wrapped_value):
    if not wrapped_value:
        return None
    if "stringValue" in wrapped_value:
        return wrapped_value["stringValue"]
    if "intValue" in wrapped_value:
        return int(wrapped_value["intValue"])
    if "doubleValue" in wrapped_value:
        return wrapped_value["doubleValue"]
    if "boolValue" in wrapped_value:
        return wrapped_value["boolValue"]
    return None


def attributes_dict(attributes):
    mapped_attributes = {}
    for attribute in attributes or []:
        mapped_attributes[attribute["key"]] = read_otlp_value(attribute.get("value"))
    return mapped_attributes


def bounded_text(value):
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= BOUNDED_TEXT_CHARS else text[:BOUNDED_TEXT_CHARS]


def span_input_preview(attributes):
    if attributes.get("gen_ai.operation.name") == "embeddings":
        return None
    raw_input = attributes.get("gen_ai.input.messages") or attributes.get("gen_ai.tool.call.arguments")
    if raw_input is None:
        return None
    text = raw_input if isinstance(raw_input, str) else json.dumps(raw_input, default=str, ensure_ascii=False)
    marker = '"question": "'
    if marker in text:
        start_index = text.index(marker) + len(marker)
        end_index = text.find('"', start_index)
        if end_index != -1:
            return text[start_index:end_index]
    return bounded_text(text)


def span_char_count(value, skip):
    if skip or value is None:
        return 0
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    return len(text)


def as_token_count(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def span_agent(name, langgraph_node, operation_name):
    if langgraph_node:
        return langgraph_node
    span_name = name or ""
    if span_name.startswith("execute_task "):
        return span_name.removeprefix("execute_task ")
    if span_name.startswith("execute_tool "):
        return "tools"
    if operation_name == "embeddings" or span_name.startswith("embeddings "):
        return "embeddings"
    if operation_name == "retrieval" or span_name.startswith("retrieval "):
        return "retrieval"
    if operation_name == "invoke_workflow" or span_name.startswith("invoke_workflow "):
        return "workflow"
    if span_name.startswith("ChatOpenAI"):
        return "chat"
    if span_name.startswith("invoke_agent") or span_name.startswith("LangGraph"):
        return "graph"
    return span_name or "unknown"


def event_detail_text(event_attributes):
    if event_attributes.get("details"):
        return bounded_text(event_attributes["details"])
    if event_attributes.get("exception.type"):
        return bounded_text(event_attributes["exception.type"])
    return bounded_text(json.dumps(event_attributes, default=str, ensure_ascii=False) if event_attributes else None)


def insert_span(connection, span):
    attributes = attributes_dict(span.get("attributes"))
    start_time_unix_nano = int(span["startTimeUnixNano"])
    end_time_unix_nano = int(span["endTimeUnixNano"])
    operation_name = attributes.get("gen_ai.operation.name")
    langgraph_node = attributes.get("traceloop.association.properties.langgraph_node")
    connection.execute("INSERT INTO stored_spans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (start_time_unix_nano, end_time_unix_nano, (end_time_unix_nano - start_time_unix_nano) / 1000000, span.get("traceId"), span.get("spanId"), span.get("parentSpanId") or None, span.get("name"), (span.get("status") or {}).get("code"), attributes.get("error.type"), attributes.get("flow_id") or attributes.get("traceloop.association.properties.flow_id"), operation_name, attributes.get("gen_ai.tool.name"), attributes.get("gen_ai.task.status"), attributes.get("gen_ai.request.model") or attributes.get("traceloop.association.properties.ls_model_name"), as_token_count(attributes.get("gen_ai.usage.input_tokens")), as_token_count(attributes.get("gen_ai.usage.output_tokens")), as_token_count(attributes.get("gen_ai.usage.total_tokens")), langgraph_node, span_input_preview(attributes), span_agent(span.get("name"), langgraph_node, operation_name), span_char_count(attributes.get("gen_ai.input.messages") or attributes.get("gen_ai.tool.call.arguments"), False), span_char_count(attributes.get("gen_ai.output.messages") or attributes.get("gen_ai.tool.call.result"), operation_name == "embeddings")))
    return


def insert_span_events(connection, span):
    for event in span.get("events") or []:
        connection.execute("INSERT INTO stored_span_events VALUES (?, ?, ?, ?, ?)", (event.get("timeUnixNano"), span.get("traceId"), span.get("spanId"), event.get("name"), event_detail_text(attributes_dict(event.get("attributes")))))
    return


def load_span_file(connection, span_file_path):
    with span_file_path.open(encoding="utf-8") as span_file:
        for line in span_file:
            if not line.strip():
                continue
            stored_record = json.loads(line)
            for resource_spans in stored_record["resourceSpans"]:
                for scope_spans in resource_spans["scopeSpans"]:
                    for span in scope_spans["spans"]:
                        insert_span(connection, span)
                        insert_span_events(connection, span)
    return


def open_spans(telemetry_directory_path=None):
    telemetry_directory_path = Path(telemetry_directory_path or TELEMETRY_DIRECTORY_PATH)
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE stored_spans (start_time_unix_nano INTEGER, end_time_unix_nano INTEGER, duration_ms REAL, trace_id TEXT, span_id TEXT, parent_span_id TEXT, name TEXT, status_code INTEGER, error_type TEXT, flow_id TEXT, operation_name TEXT, tool_name TEXT, task_status TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER, langgraph_node TEXT, input_preview TEXT, agent TEXT, input_chars INTEGER, output_chars INTEGER)")
    connection.execute("CREATE VIEW spans AS SELECT * FROM stored_spans")
    connection.execute("CREATE TABLE stored_span_events (time_unix_nano TEXT, trace_id TEXT, span_id TEXT, name TEXT, details TEXT)")
    connection.execute("CREATE VIEW span_events AS SELECT * FROM stored_span_events")
    if not telemetry_directory_path.exists():
        return connection
    try:
        for span_file_path in sorted(telemetry_directory_path.glob("spans-*.jsonl")):
            load_span_file(connection, span_file_path)
    except Exception:
        connection.close()
        raise
    connection.commit()
    return connection
