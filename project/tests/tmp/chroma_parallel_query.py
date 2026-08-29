from concurrent.futures import ThreadPoolExecutor

import chromadb
from chromadb.api.shared_system_client import SharedSystemClient

from src.conts import FACTS_ACTIVE_COLLECTION, FACTS_CHROMA_PATH, RETRIEVAL_TOP_K
from src.repositories.facts_chroma_repository import FactsChromaRepository


def peek_embedding():
    chroma_client = chromadb.PersistentClient(path=FACTS_CHROMA_PATH)
    collection = chroma_client.get_collection(FACTS_ACTIVE_COLLECTION, embedding_function=None)
    peeked = collection.peek(limit=1)
    embeddings = peeked.get("embeddings")
    chroma_client.close()
    SharedSystemClient.clear_system_cache()
    FactsChromaRepository.client = None
    FactsChromaRepository.client_path = None
    if embeddings is None or len(embeddings) == 0:
        raise RuntimeError("facts collection has no embeddings")
    return list(embeddings[0])


def run_query(query_embedding):
    return FactsChromaRepository.query_records({"chroma_path": FACTS_CHROMA_PATH, "top_k": RETRIEVAL_TOP_K, "where": None}, "chroma-parallel", query_embedding)


def main():
    query_embedding = peek_embedding()
    failures = 0
    empties = 0
    rounds = 40
    workers = 2
    for round_index in range(rounds):
        if FactsChromaRepository.client is not None:
            FactsChromaRepository.client.close()
            FactsChromaRepository.client = None
            FactsChromaRepository.client_path = None
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(run_query, [query_embedding] * workers))
        for query_result in results:
            if query_result is None:
                failures += 1
            elif not query_result.get("documents") or not query_result["documents"][0]:
                empties += 1
    print(f"rounds={rounds} workers={workers} failures={failures} empties={empties} path={FACTS_CHROMA_PATH}")


if __name__ == "__main__":
    main()
