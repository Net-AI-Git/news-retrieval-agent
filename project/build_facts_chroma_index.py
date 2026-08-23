import json
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from dotenv import load_dotenv

from src.conts import CHROMA_BATCH_SIZE, CHROMA_SCHEMA_VERSION, FACTS_EXPECTED_RECORD_COUNT, FACTS_EXPECTED_RECORDS_SHA256, FACTS_REQUIRED_FIELDS
from src.repositories.embeddings_repository import OpenAIEmbeddingsRepository
from src.repositories.facts_chroma_repository import FactsChromaRepository


def load_json(path):
    with path.open(encoding="utf-8") as source_file:
        return json.load(source_file)


def validate_sources(facts, corpus):
    corpus_titles = [article["title"] for article in corpus]
    if len(corpus_titles) != len(set(corpus_titles)):
        raise ValueError("Corpus article titles must be unique")
    for fact in facts:
        missing_fields = FACTS_REQUIRED_FIELDS.difference(fact)
        if missing_fields:
            raise ValueError(f"Fact is missing fields: {sorted(missing_fields)}")
        if fact["article_title"] not in corpus_titles:
            raise ValueError(f"Fact article is absent from corpus: {fact['article_title']}")


def build_records(facts):
    records = []
    for fact in facts:
        article_id = str(uuid5(NAMESPACE_URL, f"pda-article:{fact['article_title']}"))
        records.append({"id": str(uuid5(NAMESPACE_URL, f"pda-fact:{article_id}:{fact['fact']}")), "document": fact["fact"], "metadata": {"article_id": article_id, "article_title": fact["article_title"], "source": fact["source"], "category": fact["category"], "published_at": fact["published_at"], "published_at_epoch": int(datetime.fromisoformat(fact["published_at"]).timestamp()), "url": fact["url"]}})
    if len({record["id"] for record in records}) != len(records):
        raise ValueError("Fact identifiers must be unique")
    return records


def validate_record_manifest(records):
    if len(records) != FACTS_EXPECTED_RECORD_COUNT:
        raise ValueError(f"Facts record count changed: {len(records)}")
    records_digest = sha256()
    for record in sorted(records, key=lambda item: item["id"]):
        records_digest.update(json.dumps({"id": record["id"], "document": record["document"], "metadata": record["metadata"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
    if records_digest.hexdigest() != FACTS_EXPECTED_RECORDS_SHA256:
        raise ValueError("Facts records do not match the approved Chroma DB manifest")


def validate_embedding_dimensions(embeddings, expected_dimensions):
    embedding_dimensions = {len(embedding) for embedding in embeddings}
    if len(embedding_dimensions) != 1 or expected_dimensions and expected_dimensions not in embedding_dimensions:
        raise ValueError("Embedding dimensions are inconsistent across facts batches")
    return len(embeddings[0])


def embed_records(records, task_data, flow_id):
    embedding_dimensions = None
    for start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[start:start + CHROMA_BATCH_SIZE]
        embeddings = OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [record["document"] for record in batch]}, flow_id)
        if not embeddings:
            raise ValueError("Facts embedding generation failed")
        validated_dimensions = validate_embedding_dimensions(embeddings, embedding_dimensions)
        if embedding_dimensions is None:
            embedding_dimensions = validated_dimensions
        if not FactsChromaRepository.upsert_records({**task_data, "records": batch, "embeddings": embeddings}, flow_id):
            raise ValueError("Facts batch storage failed")
        print(f"Indexed facts: {min(start + len(batch), len(records))}/{len(records)}")
    return embedding_dimensions


def validate_stored_records(records, embedding_dimensions, task_data, flow_id):
    for start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[start:start + CHROMA_BATCH_SIZE]
        stored_batch = FactsChromaRepository.get_records({**task_data, "ids": [record["id"] for record in batch]}, flow_id)
        if not stored_batch:
            raise ValueError("Stored facts batch could not be read")
        stored_indexes = {record_id: index for index, record_id in enumerate(stored_batch["ids"])}
        if set(stored_indexes) != {record["id"] for record in batch}:
            raise ValueError("Stored fact identifiers do not match source records")
        for record in batch:
            stored_index = stored_indexes[record["id"]]
            if stored_batch["documents"][stored_index] != record["document"] or stored_batch["metadatas"][stored_index] != record["metadata"]:
                raise ValueError(f"Stored fact content does not match source record: {record['id']}")
            if len(stored_batch["embeddings"][stored_index]) != embedding_dimensions:
                raise ValueError(f"Stored fact embedding dimensions are invalid: {record['id']}")


def build_facts_chroma_index():
    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")
    task_data = {"chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "index_name": "facts"}
    flow_id = str(uuid4())
    facts = load_json(project_root / "src" / "data" / "facts.json")
    validate_sources(facts, load_json(project_root / "src" / "data" / "corpus.json"))
    records = build_records(facts)
    validate_record_manifest(records)
    if not FactsChromaRepository.prepare_collection(task_data, flow_id):
        raise ValueError("Facts staging collection preparation failed")
    embedding_dimensions = embed_records(records, task_data, flow_id)
    validate_stored_records(records, embedding_dimensions, task_data, flow_id)
    if not FactsChromaRepository.promote_collection({**task_data, "record_count": len(records), "metadata": {"embedding_model": OpenAIEmbeddingsRepository.model_name, "embedding_dimensions": embedding_dimensions, "schema_version": CHROMA_SCHEMA_VERSION, "record_type": "fact"}}, flow_id):
        raise ValueError("Facts collection promotion failed")
    print(f"Facts collection rebuilt with {len(records)} records using {OpenAIEmbeddingsRepository.model_name}")


if __name__ == "__main__":
    build_facts_chroma_index()
