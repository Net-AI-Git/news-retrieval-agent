import json
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from dotenv import load_dotenv

from ..conts import CHROMA_BATCH_SIZE, CHROMA_SCHEMA_VERSION, DATA_DIR, FACTS_CHROMA_PATH, FACTS_EXPECTED_RECORD_COUNT, FACTS_EXPECTED_RECORDS_SHA256, FACTS_REQUIRED_FIELDS
from ..repositories.embeddings_repository import OpenAIEmbeddingsRepository
from ..repositories.facts_chroma_repository import FactsChromaRepository
from ..repositories.local_logging_repository import LocalLoggingRepository


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def load_facts_sources(task_data):
    data_dir = Path(task_data["data_dir"])
    with (data_dir / "facts.json").open(encoding="utf-8") as facts_file, (data_dir / "corpus.json").open(encoding="utf-8") as corpus_file:
        return json.load(facts_file), json.load(corpus_file)


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


def prepare_facts_collection(task_data, flow_id):
    if not FactsChromaRepository.prepare_collection(task_data, flow_id):
        raise ValueError("Facts staging collection preparation failed")


def embed_records(records, task_data, flow_id):
    embedding_dimensions = None
    for start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[start:start + CHROMA_BATCH_SIZE]
        embeddings = OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [record["document"] for record in batch]}, flow_id)
        if not embeddings:
            raise ValueError("Facts embedding generation failed")
        embedding_sizes = set()
        for embedding in embeddings:
            embedding_sizes.add(len(embedding))
        if len(embedding_sizes) != 1 or embedding_dimensions and embedding_dimensions not in embedding_sizes:
            raise ValueError("Embedding dimensions are inconsistent across facts batches")
        if embedding_dimensions is None:
            embedding_dimensions = len(embeddings[0])
        if not FactsChromaRepository.upsert_records({**task_data, "records": batch, "embeddings": embeddings}, flow_id):
            raise ValueError("Facts batch storage failed")
    return embedding_dimensions


def promote_facts_collection(records, embedding_dimensions, task_data, flow_id):
    if not FactsChromaRepository.promote_collection({**task_data, "record_count": len(records), "metadata": {"embedding_model": OpenAIEmbeddingsRepository.model_name, "embedding_dimensions": embedding_dimensions, "schema_version": CHROMA_SCHEMA_VERSION, "record_type": "fact"}}, flow_id):
        raise ValueError("Facts collection promotion failed")
    return task_data["chroma_path"]


def remove_stale_facts(records, task_data, flow_id):
    if not FactsChromaRepository.delete_extra_records({**task_data, "ids": [record["id"] for record in records]}, flow_id):
        raise ValueError("Facts extra record cleanup failed")


def run_facts_chroma_index(task_data, flow_id):
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    chroma_path = None
    try:
        facts, corpus = load_facts_sources(task_data)
        validate_sources(facts, corpus)
        records = build_records(facts)
        validate_record_manifest(records)
        prepare_facts_collection(task_data, flow_id)
        embedding_dimensions = embed_records(records, task_data, flow_id)
        remove_stale_facts(records, task_data, flow_id)
        chroma_path = promote_facts_collection(records, embedding_dimensions, task_data, flow_id)
    except Exception as err:
        LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return chroma_path


if __name__ == "__main__":
    run_facts_chroma_index({"data_dir": DATA_DIR, "chroma_path": FACTS_CHROMA_PATH}, str(uuid4()))
