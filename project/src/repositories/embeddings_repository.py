import os

from dotenv import load_dotenv
from openai import OpenAI

from ..conts import OPENAI_EMBEDDING_MAX_RETRIES, OPENAI_EMBEDDING_TIMEOUT_SECONDS
from .local_logging_repository import LocalLoggingRepository

load_dotenv()


class OpenAIEmbeddingsRepository:

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), timeout=OPENAI_EMBEDDING_TIMEOUT_SECONDS, max_retries=OPENAI_EMBEDDING_MAX_RETRIES)
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL")

    @staticmethod
    def generate_embeddings(task_data, flow_id):
        LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        embeddings = []
        try:
            embeddings = [item.embedding for item in sorted(OpenAIEmbeddingsRepository.client.embeddings.create(input=task_data["texts"], model=OpenAIEmbeddingsRepository.model_name, encoding_format="float").data, key=lambda item: item.index)]
        except Exception as err:
            LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return embeddings
