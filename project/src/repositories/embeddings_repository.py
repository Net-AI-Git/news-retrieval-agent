import os

from dotenv import load_dotenv
from openai import AzureOpenAI

from .opensearch_repository import OpenSearchRepository

load_dotenv()


class OpenAIEmbeddingsRepository:

    client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_EMBEDDINGS_API_KEY"), api_version=os.getenv("AZURE_OPENAI_EMBEDDINGS_API_VERSION"), azure_endpoint=os.getenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT"))
    embeddings_dim = int(os.getenv("EMBEDDINGS_DIMENSIONS")) if os.getenv("EMBEDDINGS_DIMENSIONS") else 0
    model_deployment_name = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME")

    @staticmethod
    def generate_embeddings(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id)
        embeddings_vector = []
        try:
            text_to_embed = task_data["text"]
            embeddings_vector = OpenAIEmbeddingsRepository.client.embeddings.create(input=text_to_embed, dimensions=OpenAIEmbeddingsRepository.embeddings_dim, model=OpenAIEmbeddingsRepository.model_deployment_name).data[0].embedding
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id)
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id)
        return embeddings_vector
