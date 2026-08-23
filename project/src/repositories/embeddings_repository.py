import os

from dotenv import load_dotenv
from openai import OpenAI

from .opensearch_repository import OpenSearchRepository

load_dotenv()


class OpenAIEmbeddingsRepository:

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL")

    @staticmethod
    def generate_embeddings(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        embeddings_vector = []
        try:
            text_to_embed = task_data["text"]
            embeddings_vector = OpenAIEmbeddingsRepository.client.embeddings.create(input=text_to_embed, model=OpenAIEmbeddingsRepository.model_name, encoding_format="float").data[0].embedding
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return embeddings_vector
