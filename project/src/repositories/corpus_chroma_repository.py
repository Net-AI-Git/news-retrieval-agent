import chromadb

from ..conts import CORPUS_ACTIVE_COLLECTION, CORPUS_STAGING_COLLECTION
from .opensearch_repository import OpenSearchRepository


class CorpusChromaRepository:

    @staticmethod
    def prepare_collection(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        prepared = False
        try:
            chroma_client = chromadb.PersistentClient(path=task_data["chroma_path"])
            collection_names = {collection.name for collection in chroma_client.list_collections()}
            if CORPUS_STAGING_COLLECTION in collection_names:
                chroma_client.delete_collection(CORPUS_STAGING_COLLECTION)
            chroma_client.create_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            prepared = True
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return prepared

    @staticmethod
    def upsert_records(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        stored = False
        try:
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            collection.upsert(ids=[record["id"] for record in task_data["records"]], documents=[record["document"] for record in task_data["records"]], metadatas=[record["metadata"] for record in task_data["records"]], embeddings=task_data["embeddings"])
            stored = True
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return stored

    @staticmethod
    def get_records(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        stored_records = None
        try:
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            stored_records = collection.get(ids=task_data["ids"], include=["documents", "metadatas", "embeddings"])
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return stored_records

    @staticmethod
    def promote_collection(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        promoted = False
        try:
            chroma_client = chromadb.PersistentClient(path=task_data["chroma_path"])
            collection = chroma_client.get_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            if collection.count() != task_data["record_count"]:
                raise ValueError("Staging corpus collection count is incomplete")
            collection.modify(metadata=task_data["metadata"])
            if collection.metadata != task_data["metadata"]:
                raise ValueError("Staging corpus collection metadata is invalid")
            if CORPUS_ACTIVE_COLLECTION in {item.name for item in chroma_client.list_collections()}:
                chroma_client.delete_collection(CORPUS_ACTIVE_COLLECTION)
            collection.modify(name=CORPUS_ACTIVE_COLLECTION)
            promoted = True
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return promoted
