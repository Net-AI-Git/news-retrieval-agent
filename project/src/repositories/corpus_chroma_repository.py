import chromadb

from ..conts import CHROMA_DISTANCE_METRIC, CHROMA_QUERY_INCLUDE, CORPUS_ACTIVE_COLLECTION, CORPUS_PREVIOUS_COLLECTION, CORPUS_STAGING_COLLECTION
from .logging_repository import LoggingRepository


class CorpusChromaRepository:

    @staticmethod
    def prepare_collection(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        prepared = False
        try:
            chromadb.PersistentClient(path=task_data["chroma_path"]).get_or_create_collection(CORPUS_STAGING_COLLECTION, configuration={"hnsw": {"space": CHROMA_DISTANCE_METRIC}}, embedding_function=None)
            prepared = True
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return prepared

    @staticmethod
    def upsert_records(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        stored = False
        try:
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            collection.upsert(ids=[record["id"] for record in task_data["records"]], documents=[record["document"] for record in task_data["records"]], metadatas=[record["metadata"] for record in task_data["records"]], embeddings=task_data["embeddings"])
            stored = True
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return stored

    @staticmethod
    def delete_extra_records(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        cleaned = False
        try:
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            extra_ids = []
            keep_ids = set(task_data["ids"])
            for stored_id in collection.get()["ids"]:
                if stored_id not in keep_ids:
                    extra_ids.append(stored_id)
            if extra_ids:
                collection.delete(ids=extra_ids)
            cleaned = True
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return cleaned

    @staticmethod
    def promote_collection(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        promoted = False
        try:
            chroma_client = chromadb.PersistentClient(path=task_data["chroma_path"])
            collection = chroma_client.get_collection(CORPUS_STAGING_COLLECTION, embedding_function=None)
            if collection.count() != task_data["record_count"]:
                raise ValueError("Staging corpus collection count is incomplete")
            collection.modify(metadata=task_data["metadata"])
            if collection.metadata != task_data["metadata"]:
                raise ValueError("Staging corpus collection metadata is invalid")
            collection_names = {item.name for item in chroma_client.list_collections()}
            if CORPUS_PREVIOUS_COLLECTION in collection_names:
                chroma_client.delete_collection(CORPUS_PREVIOUS_COLLECTION)
            if CORPUS_ACTIVE_COLLECTION in collection_names:
                chroma_client.get_collection(CORPUS_ACTIVE_COLLECTION, embedding_function=None).modify(name=CORPUS_PREVIOUS_COLLECTION)
            collection.modify(name=CORPUS_ACTIVE_COLLECTION)
            if CORPUS_PREVIOUS_COLLECTION in {item.name for item in chroma_client.list_collections()}:
                chroma_client.delete_collection(CORPUS_PREVIOUS_COLLECTION)
            promoted = True
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return promoted

    @staticmethod
    def query_records(task_data, flow_id, query_embedding):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        query_result = None
        try:
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(CORPUS_ACTIVE_COLLECTION, embedding_function=None)
            query_result = collection.query(query_embeddings=[query_embedding], n_results=task_data["top_k"], where=task_data.get("where"), include=CHROMA_QUERY_INCLUDE)
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return query_result
