from datetime import datetime

from ..conts import RETRIEVAL_CORPUS_MIN_SIMILARITY, RETRIEVAL_EVIDENCE_STORE_CORPUS, RETRIEVAL_EVIDENCE_STORE_FACTS, RETRIEVAL_HIGH_CONFIDENCE_SIMILARITY, RETRIEVAL_PERCENT_SCALE, RETRIEVAL_STATUS_EMPTY, RETRIEVAL_STATUS_INVALID, RETRIEVAL_STATUS_LOW_CONFIDENCE, RETRIEVAL_STATUS_OK, RETRIEVAL_TOP_K, TELEMETRY_RETRIEVAL_NAME, TELEMETRY_RETRIEVAL_OPERATION_NAME
from ..repositories.corpus_chroma_repository import CorpusChromaRepository
from ..repositories.embeddings_repository import OpenAIEmbeddingsRepository
from ..repositories.facts_chroma_repository import FactsChromaRepository
from ..repositories.logging_repository import LoggingRepository
from ..repositories.telemetry_repository import TelemetryRepository
from .source_resolve_service import run_resolve_source


def create_query_embedding(task_data, flow_id):
    return OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [task_data["question"]]}, flow_id)[0]


def build_where_filter(task_data):
    conditions = []
    if task_data.get("published_from"):
        conditions.append({"published_at_epoch": {"$gte": int(datetime.fromisoformat(task_data["published_from"]).timestamp())}})
    if task_data.get("published_to"):
        conditions.append({"published_at_epoch": {"$lte": int(datetime.fromisoformat(task_data["published_to"]).timestamp())}})
    if task_data.get("resolved_source"):
        conditions.append({"source": task_data["resolved_source"]})
    if len(conditions) > 1:
        return {"$and": conditions}
    if conditions:
        return conditions[0]
    return None


def query_facts(task_data, flow_id, query_embedding, where_filter):
    if task_data.get("evidence_store") == RETRIEVAL_EVIDENCE_STORE_CORPUS:
        return []
    query_result = FactsChromaRepository.query_records({**task_data, "chroma_path": task_data["facts_chroma_path"], "top_k": RETRIEVAL_TOP_K, "where": where_filter}, flow_id, query_embedding)
    results = []
    if not query_result or not query_result.get("documents") or not query_result["documents"][0]:
        return results
    for document, metadata, distance in zip(query_result["documents"][0], query_result["metadatas"][0], query_result["distances"][0]):
        similarity = max(0.0, min(1.0, 1.0 - distance))
        results.append({"article_title": metadata["article_title"], "snippet": document, "url": metadata.get("url"), "published_at": metadata.get("published_at"), "match_percentage": round(similarity * RETRIEVAL_PERCENT_SCALE, 2)})
    return results


def query_corpus(task_data, flow_id, query_embedding, where_filter):
    if task_data.get("evidence_store") == RETRIEVAL_EVIDENCE_STORE_FACTS:
        return []
    query_result = CorpusChromaRepository.query_records({**task_data, "chroma_path": task_data["corpus_chroma_path"], "top_k": RETRIEVAL_TOP_K, "where": where_filter}, flow_id, query_embedding)
    results = []
    if not query_result or not query_result.get("documents") or not query_result["documents"][0]:
        return results
    for document, metadata, distance in zip(query_result["documents"][0], query_result["metadatas"][0], query_result["distances"][0]):
        similarity = max(0.0, min(1.0, 1.0 - distance))
        if similarity < RETRIEVAL_CORPUS_MIN_SIMILARITY:
            continue
        results.append({"article_title": metadata["article_title"], "snippet": document, "url": metadata.get("url"), "published_at": metadata.get("published_at"), "match_percentage": round(similarity * RETRIEVAL_PERCENT_SCALE, 2)})
    return results


def validate_question(task_data):
    if not task_data.get("question"):
        raise ValueError("Question is required")


def build_retrieval_result(question, facts, corpus):
    results = facts + corpus
    if not results:
        status = RETRIEVAL_STATUS_EMPTY
    elif max(result["match_percentage"] for result in results) >= RETRIEVAL_HIGH_CONFIDENCE_SIMILARITY * RETRIEVAL_PERCENT_SCALE:
        status = RETRIEVAL_STATUS_OK
    else:
        status = RETRIEVAL_STATUS_LOW_CONFIDENCE
    return {"status": status, "question": question, "facts": facts, "corpus": corpus}


def run_retrieval(task_data, flow_id):
    retrieval_result = {"status": RETRIEVAL_STATUS_INVALID, "question": task_data.get("question", ""), "facts": [], "corpus": []}
    with TelemetryRepository.start_span(TELEMETRY_RETRIEVAL_OPERATION_NAME, TELEMETRY_RETRIEVAL_NAME, flow_id, task_data) as retrieval_span:
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        try:
            validate_question(task_data)
            retrieval_task = {**task_data, "resolved_source": run_resolve_source(task_data, flow_id)}
            where_filter = build_where_filter(retrieval_task)
            query_embedding = create_query_embedding(retrieval_task, flow_id)
            facts = query_facts(retrieval_task, flow_id, query_embedding, where_filter)
            corpus = query_corpus(retrieval_task, flow_id, query_embedding, where_filter)
            retrieval_result = build_retrieval_result(task_data["question"], facts, corpus)
            TelemetryRepository.record_output(retrieval_span, retrieval_result)
        except Exception as err:
            TelemetryRepository.record_error(retrieval_span, err)
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return retrieval_result
