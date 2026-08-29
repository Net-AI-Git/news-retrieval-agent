import json
from pathlib import Path

import chromadb

from ..conts import CHROMA_DISTANCE_METRIC, CHROMA_QUERY_INCLUDE, FACTS_ACTIVE_COLLECTION, FACTS_PREVIOUS_COLLECTION, FACTS_SOURCE_CATALOG_FILENAME, FACTS_STAGING_COLLECTION
from .logging_repository import LoggingRepository


class FactsChromaRepository:

    @staticmethod
    def prepare_collection(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        prepared = False
        try:
            chromadb.PersistentClient(path=task_data["chroma_path"]).get_or_create_collection(FACTS_STAGING_COLLECTION, configuration={"hnsw": {"space": CHROMA_DISTANCE_METRIC}}, embedding_function=None)
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
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(FACTS_STAGING_COLLECTION, embedding_function=None)
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
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(FACTS_STAGING_COLLECTION, embedding_function=None)
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
            collection = chroma_client.get_collection(FACTS_STAGING_COLLECTION, embedding_function=None)
            if collection.count() != task_data["record_count"]:
                raise ValueError("Staging facts collection count is incomplete")
            collection.modify(metadata=task_data["metadata"])
            if collection.metadata != task_data["metadata"]:
                raise ValueError("Staging facts collection metadata is invalid")
            collection_names = {item.name for item in chroma_client.list_collections()}
            if FACTS_PREVIOUS_COLLECTION in collection_names:
                chroma_client.delete_collection(FACTS_PREVIOUS_COLLECTION)
            if FACTS_ACTIVE_COLLECTION in collection_names:
                chroma_client.get_collection(FACTS_ACTIVE_COLLECTION, embedding_function=None).modify(name=FACTS_PREVIOUS_COLLECTION)
            collection.modify(name=FACTS_ACTIVE_COLLECTION)
            if FACTS_PREVIOUS_COLLECTION in {item.name for item in chroma_client.list_collections()}:
                chroma_client.delete_collection(FACTS_PREVIOUS_COLLECTION)
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
            collection = chromadb.PersistentClient(path=task_data["chroma_path"]).get_collection(FACTS_ACTIVE_COLLECTION, embedding_function=None)
            where_filter = task_data.get("where")
            if where_filter:
                match_count = len(collection.get(where=where_filter, limit=task_data["top_k"]).get("ids") or [])
            else:
                match_count = min(task_data["top_k"], collection.count())
            if not match_count:
                query_result = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            else:
                query_result = collection.query(query_embeddings=[query_embedding], n_results=match_count, where=where_filter, include=CHROMA_QUERY_INCLUDE)
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return query_result

    @staticmethod
    def write_source_catalog(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        stored = False
        try:
            catalog_path = Path(task_data["chroma_path"]) / FACTS_SOURCE_CATALOG_FILENAME
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(json.dumps(task_data["source_catalog"], ensure_ascii=False), encoding="utf-8")
            stored = True
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return stored

    @staticmethod
    def read_source_catalog(task_data, flow_id):
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        catalog = None
        try:
            catalog_path = Path(task_data["chroma_path"]) / FACTS_SOURCE_CATALOG_FILENAME
            if catalog_path.is_file():
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return catalog
