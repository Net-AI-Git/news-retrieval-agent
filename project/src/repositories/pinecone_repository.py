import os

from dotenv import load_dotenv
from pinecone import Pinecone

from .opensearch_repository import OpenSearchRepository

load_dotenv()


class PineconeRepository:

    pinecone_client = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    pinecone_dimensions = int(os.environ.get("PINECONE_DIMENSIONS")) if os.environ.get("PINECONE_DIMENSIONS") else 0
    index = pinecone_client.Index(index_name) if index_name else None

    @staticmethod
    def upload_documents(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id)
        try:
            documents = task_data["documents"]
            PineconeRepository.index.upsert(documents, batch_size=100)
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id)
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id)
        return

    @staticmethod
    def fetch_vector_by_id(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id)
        vector_values = None
        try:
            vector_id = task_data["vector_id"]
            fetched_vectors = PineconeRepository.index.fetch(ids=[vector_id])["vectors"]
            if vector_id in fetched_vectors:
                vector_values = fetched_vectors[vector_id]["values"]
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id)
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id)
        return vector_values

    @staticmethod
    def query_index(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id)
        query_response = None
        try:
            query_vector = task_data["query_vector"]
            top_k = task_data["top_k"]
            query_response = PineconeRepository.index.query(vector=query_vector, top_k=top_k, include_metadata=True)
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id)
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id)
        return query_response
