import os

from dotenv import load_dotenv
from openai import OpenAI

from ..conts import OPENAI_EMBEDDING_MAX_RETRIES, OPENAI_EMBEDDING_TIMEOUT_SECONDS, TELEMETRY_EMBEDDING_NAME, TELEMETRY_EMBEDDING_OPERATION_NAME
from .local_logging_repository import LocalLoggingRepository
from .local_telemetry_repository import LocalTelemetryRepository

load_dotenv()


class OpenAIEmbeddingsRepository:

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), timeout=OPENAI_EMBEDDING_TIMEOUT_SECONDS, max_retries=OPENAI_EMBEDDING_MAX_RETRIES)
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL")

    @staticmethod
    def generate_embeddings(task_data, flow_id):
        embeddings = []
        with LocalTelemetryRepository.start_span(TELEMETRY_EMBEDDING_OPERATION_NAME, TELEMETRY_EMBEDDING_NAME, flow_id, task_data) as embedding_span:
            LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
            try:
                embeddings = [item.embedding for item in sorted(OpenAIEmbeddingsRepository.client.embeddings.create(input=task_data["texts"], model=OpenAIEmbeddingsRepository.model_name, encoding_format="float").data, key=lambda item: item.index)]
                LocalTelemetryRepository.record_output(embedding_span, embeddings)
            except Exception as err:
                LocalTelemetryRepository.record_error(embedding_span, err)
                LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
            LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return embeddings
