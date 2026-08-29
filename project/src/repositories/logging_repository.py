import contextvars
import inspect
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from opentelemetry import trace

from ..conts import LOG_FILE_PATH, LOGGER_NAME


class LoggingRepository:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()
    active_trace_id = contextvars.ContextVar("active_trace_id", default=None)

    @staticmethod
    def current_trace_id(explicit_trace_id=None):
        span_context = trace.get_current_span().get_span_context()
        return explicit_trace_id or LoggingRepository.active_trace_id.get() or (format(span_context.trace_id, "032x") if span_context.is_valid else None)

    @staticmethod
    def log_event(status, process=None, content=None, flow_id=None, trace_id=None, level=None):
        response = None
        try:
            if not LoggingRepository.logger.handlers:
                Path(LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
                file_handler.setFormatter(logging.Formatter("%(message)s"))
                LoggingRepository.logger.addHandler(file_handler)
            process = process or inspect.stack()[1].function
            trace_id = LoggingRepository.current_trace_id(trace_id)
            LoggingRepository.logger.log(getattr(logging, level or "INFO"), json.dumps({"time": datetime.now(timezone.utc).isoformat(), "event": {"status": status, "process": process, "content": content, "flow_id": flow_id, "trace_id": trace_id, "level": level}}, default=str, ensure_ascii=False))
            for handler in LoggingRepository.logger.handlers:
                handler.flush()
            response = "written"
        except Exception as err:
            response = f"ERROR log_event, error: {repr(err)}, full error: {err.__cause__}"
            print(response, file=sys.stderr)
        return response
