import json
import re
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pysbd
import tiktoken
from dotenv import load_dotenv

from ..conts import CHROMA_BATCH_SIZE, CHROMA_CHUNK_MAX_TOKENS, CHROMA_CHUNK_MIN_TOKENS, CHROMA_CHUNK_TARGET_TOKENS, CHROMA_OVERLAP_TARGET_TOKENS, CHROMA_SCHEMA_VERSION, CHROMA_TOKEN_ENCODING, CORPUS_EXPECTED_RECORD_COUNT, CORPUS_EXPECTED_RECORDS_SHA256, CORPUS_REQUIRED_FIELDS
from ..repositories.corpus_chroma_repository import CorpusChromaRepository
from ..repositories.embeddings_repository import OpenAIEmbeddingsRepository
from ..repositories.opensearch_repository import OpenSearchRepository


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
tokenizer = tiktoken.get_encoding(CHROMA_TOKEN_ENCODING)
segmenter = pysbd.Segmenter(language="en", clean=False, char_span=True)


def load_corpus(task_data):
    with (Path(task_data["data_dir"]) / "corpus.json").open(encoding="utf-8") as source_file:
        return json.load(source_file)


def validate_corpus(corpus):
    article_titles = []
    for article in corpus:
        missing_fields = CORPUS_REQUIRED_FIELDS.difference(article)
        if missing_fields:
            raise ValueError(f"Corpus article is missing fields: {sorted(missing_fields)}")
        if not article["body"].strip():
            raise ValueError(f"Corpus article body is empty: {article['title']}")
        article_titles.append(article["title"])
    if len(article_titles) != len(set(article_titles)):
        raise ValueError("Corpus article titles must be unique")


def split_corpus_sentence_units(corpus):
    article_units = []
    for article in corpus:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", article["body"].replace("\r\n", "\n").replace("\r", "\n")) if paragraph.strip()]
        paragraph_units = []
        for paragraph in paragraphs:
            if len(tokenizer.encode(paragraph)) <= CHROMA_CHUNK_MAX_TOKENS:
                paragraph_units.append([paragraph])
                continue
            spans = segmenter.segment(paragraph)
            if not spans:
                paragraph_units.append([paragraph])
                continue
            ends = [span.end for span in spans]
            ends[-1] = len(paragraph)
            units = [paragraph[start:end] for start, end in zip([0] + ends[:-1], ends)]
            if "".join(units) != paragraph:
                raise ValueError("Sentence segmentation changed paragraph text")
            paragraph_units.append(units)
        article_units.append((article, paragraph_units))
    return article_units


def chunk_corpus_units(article_units):
    article_chunks = []
    for article, paragraph_units in article_units:
        chunks = []
        for paragraph_index, units in enumerate(paragraph_units):
            paragraph = "".join(units)
            if len(tokenizer.encode(paragraph)) <= CHROMA_CHUNK_MAX_TOKENS:
                chunks.append((paragraph_index, paragraph))
                continue
            chunk_start = 0
            while chunk_start < len(units):
                chunk_end = chunk_start + 1
                while chunk_end < len(units):
                    current_tokens = len(tokenizer.encode("".join(units[chunk_start:chunk_end])))
                    candidate_tokens = len(tokenizer.encode("".join(units[chunk_start:chunk_end]) + units[chunk_end]))
                    if not (candidate_tokens <= CHROMA_CHUNK_TARGET_TOKENS or current_tokens < CHROMA_CHUNK_MIN_TOKENS and candidate_tokens <= CHROMA_CHUNK_MAX_TOKENS or candidate_tokens <= CHROMA_CHUNK_MAX_TOKENS and abs(CHROMA_CHUNK_TARGET_TOKENS - candidate_tokens) < abs(CHROMA_CHUNK_TARGET_TOKENS - current_tokens)):
                        break
                    chunk_end += 1
                chunks.append((paragraph_index, "".join(units[chunk_start:chunk_end])))
                if chunk_end == len(units):
                    break
                overlap_start = min(range(chunk_start, chunk_end), key=lambda overlap_start: abs(CHROMA_OVERLAP_TARGET_TOKENS - len(tokenizer.encode("".join(units[overlap_start:chunk_end])))))
                chunk_start = chunk_end if overlap_start == chunk_start else overlap_start
        article_chunks.append((article, chunks))
    return article_chunks


def assemble_corpus_records(article_chunks):
    records = []
    for article, chunks in article_chunks:
        article_id = str(uuid5(NAMESPACE_URL, f"pda-article:{article['title']}"))
        paragraph_chunk_counts = {}
        for chunk_index, (paragraph_index, document) in enumerate(chunks):
            paragraph_chunk_index = paragraph_chunk_counts.get(paragraph_index, 0)
            paragraph_chunk_counts[paragraph_index] = paragraph_chunk_index + 1
            records.append({"id": str(uuid5(NAMESPACE_URL, f"pda-passage:{article_id}:{paragraph_index}:{paragraph_chunk_index}:{document}")), "document": document, "embedding_input": f"{article['title']}\n\n{document}", "metadata": {"article_id": article_id, "article_title": article["title"], "chunk_index": chunk_index, "paragraph_index": paragraph_index, "source": article["source"], "author": article.get("author") or "", "category": article["category"], "published_at": article["published_at"], "published_at_epoch": int(datetime.fromisoformat(article["published_at"]).timestamp()), "url": article["url"]}})
    if len({record["id"] for record in records}) != len(records):
        raise ValueError("Corpus passage identifiers must be unique")
    return records


def validate_record_manifest(records):
    if len(records) != CORPUS_EXPECTED_RECORD_COUNT:
        raise ValueError(f"Corpus record count changed: {len(records)}")
    records_digest = sha256()
    for record in sorted(records, key=lambda item: item["id"]):
        records_digest.update(json.dumps({"id": record["id"], "document": record["document"], "metadata": record["metadata"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
    if records_digest.hexdigest() != CORPUS_EXPECTED_RECORDS_SHA256:
        raise ValueError("Corpus records do not match the approved Chroma DB manifest")


def prepare_corpus_collection(task_data, flow_id):
    if not CorpusChromaRepository.prepare_collection(task_data, flow_id):
        raise ValueError("Corpus staging collection preparation failed")


def embed_records(records, task_data, flow_id):
    embedding_dimensions = None
    for start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[start:start + CHROMA_BATCH_SIZE]
        embeddings = OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [record["embedding_input"] for record in batch]}, flow_id)
        if not embeddings:
            raise ValueError("Corpus embedding generation failed")
        embedding_sizes = {len(embedding) for embedding in embeddings}
        if len(embedding_sizes) != 1 or embedding_dimensions and embedding_dimensions not in embedding_sizes:
            raise ValueError("Embedding dimensions are inconsistent across corpus batches")
        if embedding_dimensions is None:
            embedding_dimensions = len(embeddings[0])
        if not CorpusChromaRepository.upsert_records({**task_data, "records": batch, "embeddings": embeddings}, flow_id):
            raise ValueError("Corpus batch storage failed")
        print(f"Indexed corpus passages: {min(start + len(batch), len(records))}/{len(records)}")
    return embedding_dimensions


def validate_stored_records(records, embedding_dimensions, task_data, flow_id):
    for start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[start:start + CHROMA_BATCH_SIZE]
        stored_batch = CorpusChromaRepository.get_records({**task_data, "ids": [record["id"] for record in batch]}, flow_id)
        if not stored_batch:
            raise ValueError("Stored corpus batch could not be read")
        stored_indexes = {record_id: index for index, record_id in enumerate(stored_batch["ids"])}
        if set(stored_indexes) != {record["id"] for record in batch}:
            raise ValueError("Stored corpus identifiers do not match source records")
        for record in batch:
            stored_index = stored_indexes[record["id"]]
            if stored_batch["documents"][stored_index] != record["document"] or stored_batch["metadatas"][stored_index] != record["metadata"]:
                raise ValueError(f"Stored corpus content does not match source record: {record['id']}")
            if len(stored_batch["embeddings"][stored_index]) != embedding_dimensions:
                raise ValueError(f"Stored corpus embedding dimensions are invalid: {record['id']}")


def promote_corpus_collection(records, embedding_dimensions, task_data, flow_id):
    if not CorpusChromaRepository.promote_collection({**task_data, "record_count": len(records), "metadata": {"embedding_model": OpenAIEmbeddingsRepository.model_name, "embedding_dimensions": embedding_dimensions, "schema_version": CHROMA_SCHEMA_VERSION, "record_type": "corpus_passage", "chunk_target_tokens": CHROMA_CHUNK_TARGET_TOKENS, "chunk_min_tokens": CHROMA_CHUNK_MIN_TOKENS, "chunk_max_tokens": CHROMA_CHUNK_MAX_TOKENS, "overlap_target_tokens": CHROMA_OVERLAP_TARGET_TOKENS, "paragraph_boundary": "hard", "token_encoding": CHROMA_TOKEN_ENCODING, "sentence_segmenter": "pysbd:0.3.4"}}, flow_id):
        raise ValueError("Corpus collection promotion failed")
    print(f"Corpus collection rebuilt with {len(records)} passages using {OpenAIEmbeddingsRepository.model_name}")
    return task_data["chroma_path"]


def run_corpus_chroma_index(task_data, flow_id):
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    chroma_path = None
    try:
        corpus = load_corpus(task_data)
        validate_corpus(corpus)
        article_units = split_corpus_sentence_units(corpus)
        article_chunks = chunk_corpus_units(article_units)
        records = assemble_corpus_records(article_chunks)
        validate_record_manifest(records)
        prepare_corpus_collection(task_data, flow_id)
        embedding_dimensions = embed_records(records, task_data, flow_id)
        validate_stored_records(records, embedding_dimensions, task_data, flow_id)
        chroma_path = promote_corpus_collection(records, embedding_dimensions, task_data, flow_id)
    except Exception as err:
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return chroma_path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    run_corpus_chroma_index({"data_dir": str(Path(__file__).resolve().parents[1] / "data"), "chroma_path": str(project_root / "vector_stores" / "corpus_chroma"), "index_name": "corpus"}, str(uuid4()))
