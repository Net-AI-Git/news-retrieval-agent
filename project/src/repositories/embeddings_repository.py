import os

from dotenv import load_dotenv
from openai import OpenAI

from .opensearch_repository import OpenSearchRepository

load_dotenv()


class OpenAIEmbeddingsRepository:

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), timeout=60, max_retries=3)
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL")

    @staticmethod
    def generate_embeddings(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        embeddings = []
        try:
            ordered_items = sorted(OpenAIEmbeddingsRepository.client.embeddings.create(input=task_data["texts"], model=OpenAIEmbeddingsRepository.model_name, encoding_format="float").data, key=lambda item: item.index)
            if len(ordered_items) != len(task_data["texts"]):
                raise ValueError("Embedding response count does not match input count")
            if [item.index for item in ordered_items] != list(range(len(task_data["texts"]))):
                raise ValueError("Embedding response indexes do not match input order")
            embeddings = [item.embedding for item in ordered_items]
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return embeddings
