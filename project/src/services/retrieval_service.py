from datetime import datetime

from ..conts import RETRIEVAL_CORPUS_MIN_SIMILARITY, RETRIEVAL_EVIDENCE_STORE_CORPUS, RETRIEVAL_EVIDENCE_STORE_FACTS, RETRIEVAL_FACTS_MIN_SIMILARITY, RETRIEVAL_HIGH_CONFIDENCE_SIMILARITY, RETRIEVAL_PERCENT_SCALE, RETRIEVAL_STATUS_EMPTY, RETRIEVAL_STATUS_LOW_CONFIDENCE, RETRIEVAL_STATUS_OK, RETRIEVAL_TOP_K
from ..repositories.corpus_chroma_repository import CorpusChromaRepository
from ..repositories.embeddings_repository import OpenAIEmbeddingsRepository
from ..repositories.facts_chroma_repository import FactsChromaRepository
from ..repositories.opensearch_repository import OpenSearchRepository


def create_query_embedding(task_data, flow_id):
    embeddings = OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [task_data["question"]]}, flow_id)
    if len(embeddings) != 1:
        raise ValueError("Question embedding generation failed")
    return embeddings[0]


def build_published_at_filter(task_data):
    conditions = []
    if task_data.get("published_from"):
        conditions.append({"published_at_epoch": {"$gte": int(datetime.fromisoformat(task_data["published_from"]).timestamp())}})
    if task_data.get("published_to"):
        conditions.append({"published_at_epoch": {"$lte": int(datetime.fromisoformat(task_data["published_to"]).timestamp())}})
    if len(conditions) == 2:
        return {"$and": conditions}
    if conditions:
        return conditions[0]
    return None


def query_facts(task_data, flow_id, query_embedding, published_at_filter):
    if task_data.get("evidence_store") == RETRIEVAL_EVIDENCE_STORE_CORPUS:
        return []
    query_result = FactsChromaRepository.query_records({**task_data, "chroma_path": task_data["facts_chroma_path"], "query_embedding": query_embedding, "top_k": RETRIEVAL_TOP_K, "where": published_at_filter}, flow_id)
    if query_result is None:
        raise ValueError("Evidence retrieval failed")
    results = []
    for document, metadata, distance in zip(query_result["documents"][0], query_result["metadatas"][0], query_result["distances"][0]):
        similarity = max(0.0, min(1.0, 1.0 - distance))
        if similarity < RETRIEVAL_FACTS_MIN_SIMILARITY:
            continue
        results.append({"article_title": metadata["article_title"], "snippet": document, "url": metadata.get("url"), "published_at": metadata.get("published_at"), "match_percentage": round(similarity * RETRIEVAL_PERCENT_SCALE, 2)})
    return results


def query_corpus(task_data, flow_id, query_embedding, published_at_filter):
    if task_data.get("evidence_store") == RETRIEVAL_EVIDENCE_STORE_FACTS:
        return []
    query_result = CorpusChromaRepository.query_records({**task_data, "chroma_path": task_data["corpus_chroma_path"], "query_embedding": query_embedding, "top_k": RETRIEVAL_TOP_K, "where": published_at_filter}, flow_id)
    if query_result is None:
        raise ValueError("Evidence retrieval failed")
    results = []
    for document, metadata, distance in zip(query_result["documents"][0], query_result["metadatas"][0], query_result["distances"][0]):
        similarity = max(0.0, min(1.0, 1.0 - distance))
        if similarity < RETRIEVAL_CORPUS_MIN_SIMILARITY:
            continue
        results.append({"article_title": metadata["article_title"], "snippet": document, "url": metadata.get("url"), "published_at": metadata.get("published_at"), "match_percentage": round(similarity * RETRIEVAL_PERCENT_SCALE, 2)})
    return results


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
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    retrieval_result = {"status": RETRIEVAL_STATUS_EMPTY, "question": task_data.get("question", ""), "facts": [], "corpus": []}
    try:
        if not task_data.get("question"):
            raise ValueError("Question is required")
        query_embedding = create_query_embedding(task_data, flow_id)
        published_at_filter = build_published_at_filter(task_data)
        facts = query_facts(task_data, flow_id, query_embedding, published_at_filter)
        corpus = query_corpus(task_data, flow_id, query_embedding, published_at_filter)
        retrieval_result = build_retrieval_result(task_data["question"], facts, corpus)
    except Exception as err:
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return retrieval_result
