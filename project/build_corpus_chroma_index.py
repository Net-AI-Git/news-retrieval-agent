import json
import re
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pysbd
import tiktoken
from dotenv import load_dotenv

from src.conts import CHROMA_BATCH_SIZE, CHROMA_CHUNK_MAX_TOKENS, CHROMA_CHUNK_MIN_TOKENS, CHROMA_CHUNK_TARGET_TOKENS, CHROMA_OVERLAP_TARGET_TOKENS, CHROMA_SCHEMA_VERSION, CHROMA_TOKEN_ENCODING, CORPUS_EXPECTED_RECORD_COUNT, CORPUS_EXPECTED_RECORDS_SHA256, CORPUS_REQUIRED_FIELDS
from src.repositories.corpus_chroma_repository import CorpusChromaRepository
from src.repositories.embeddings_repository import OpenAIEmbeddingsRepository


tokenizer = tiktoken.get_encoding(CHROMA_TOKEN_ENCODING)
segmenter = pysbd.Segmenter(language="en", clean=False, char_span=True)


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


def token_count(text):
    return len(tokenizer.encode(text))


def split_into_sentence_units(paragraph):
    spans = segmenter.segment(paragraph)
    if not spans:
        return [paragraph]
    ends = [span.end for span in spans]
    ends[-1] = len(paragraph)
    units = [paragraph[start:end] for start, end in zip([0] + ends[:-1], ends)]
    if "".join(units) != paragraph:
        raise ValueError("Sentence segmentation changed paragraph text")
    return units


def should_add_sentence(current_text, next_sentence):
    current_tokens = token_count(current_text)
    candidate_tokens = token_count(current_text + next_sentence)
    if candidate_tokens <= CHROMA_CHUNK_TARGET_TOKENS:
        return True
    if current_tokens < CHROMA_CHUNK_MIN_TOKENS and candidate_tokens <= CHROMA_CHUNK_MAX_TOKENS:
        return True
    return candidate_tokens <= CHROMA_CHUNK_MAX_TOKENS and abs(CHROMA_CHUNK_TARGET_TOKENS - candidate_tokens) < abs(CHROMA_CHUNK_TARGET_TOKENS - current_tokens)


def find_overlap_start(units, chunk_start, chunk_end):
    candidates = []
    for overlap_start in range(chunk_start, chunk_end):
        candidates.append((abs(CHROMA_OVERLAP_TARGET_TOKENS - token_count("".join(units[overlap_start:chunk_end]))), overlap_start))
    return min(candidates)[1]


def split_large_paragraph(paragraph):
    units = split_into_sentence_units(paragraph)
    chunks = []
    chunk_start = 0
    while chunk_start < len(units):
        chunk_end = chunk_start + 1
        while chunk_end < len(units) and should_add_sentence("".join(units[chunk_start:chunk_end]), units[chunk_end]):
            chunk_end += 1
        chunks.append("".join(units[chunk_start:chunk_end]))
        if chunk_end == len(units):
            break
        overlap_start = find_overlap_start(units, chunk_start, chunk_end)
        chunk_start = chunk_end if overlap_start == chunk_start else overlap_start
    return chunks


def split_article_body(body):
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", body.replace("\r\n", "\n").replace("\r", "\n")) if paragraph.strip()]
    paragraph_chunks = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        for chunk in [paragraph] if token_count(paragraph) <= CHROMA_CHUNK_MAX_TOKENS else split_large_paragraph(paragraph):
            paragraph_chunks.append((paragraph_index, chunk))
    return paragraph_chunks


def build_article_records(article):
    article_id = str(uuid5(NAMESPACE_URL, f"pda-article:{article['title']}"))
    records = []
    paragraph_chunk_counts = {}
    for chunk_index, (paragraph_index, document) in enumerate(split_article_body(article["body"])):
        paragraph_chunk_index = paragraph_chunk_counts.get(paragraph_index, 0)
        paragraph_chunk_counts[paragraph_index] = paragraph_chunk_index + 1
        records.append({"id": str(uuid5(NAMESPACE_URL, f"pda-passage:{article_id}:{paragraph_index}:{paragraph_chunk_index}:{document}")), "document": document, "embedding_input": f"{article['title']}\n\n{document}", "metadata": {"article_id": article_id, "article_title": article["title"], "chunk_index": chunk_index, "paragraph_index": paragraph_index, "source": article["source"], "author": article.get("author") or "", "category": article["category"], "published_at": article["published_at"], "published_at_epoch": int(datetime.fromisoformat(article["published_at"]).timestamp()), "url": article["url"]}})
    return records


def build_records(corpus):
    records = []
    for article in corpus:
        records.extend(build_article_records(article))
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


def validate_embedding_dimensions(embeddings, expected_dimensions):
    embedding_dimensions = {len(embedding) for embedding in embeddings}
    if len(embedding_dimensions) != 1 or expected_dimensions and expected_dimensions not in embedding_dimensions:
        raise ValueError("Embedding dimensions are inconsistent across corpus batches")
    return len(embeddings[0])


def embed_records(records, task_data, flow_id):
    embedding_dimensions = None
    for start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[start:start + CHROMA_BATCH_SIZE]
        embeddings = OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [record["embedding_input"] for record in batch]}, flow_id)
        if not embeddings:
            raise ValueError("Corpus embedding generation failed")
        validated_dimensions = validate_embedding_dimensions(embeddings, embedding_dimensions)
        if embedding_dimensions is None:
            embedding_dimensions = validated_dimensions
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


def build_corpus_chroma_index():
    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")
    task_data = {"chroma_path": str(project_root / "vector_stores" / "corpus_chroma"), "index_name": "corpus"}
    flow_id = str(uuid4())
    with (project_root / "src" / "data" / "corpus.json").open(encoding="utf-8") as source_file:
        corpus = json.load(source_file)
    validate_corpus(corpus)
    records = build_records(corpus)
    validate_record_manifest(records)
    if not CorpusChromaRepository.prepare_collection(task_data, flow_id):
        raise ValueError("Corpus staging collection preparation failed")
    embedding_dimensions = embed_records(records, task_data, flow_id)
    validate_stored_records(records, embedding_dimensions, task_data, flow_id)
    if not CorpusChromaRepository.promote_collection({**task_data, "record_count": len(records), "metadata": {"embedding_model": OpenAIEmbeddingsRepository.model_name, "embedding_dimensions": embedding_dimensions, "schema_version": CHROMA_SCHEMA_VERSION, "record_type": "corpus_passage", "chunk_target_tokens": CHROMA_CHUNK_TARGET_TOKENS, "chunk_min_tokens": CHROMA_CHUNK_MIN_TOKENS, "chunk_max_tokens": CHROMA_CHUNK_MAX_TOKENS, "overlap_target_tokens": CHROMA_OVERLAP_TARGET_TOKENS, "paragraph_boundary": "hard", "token_encoding": CHROMA_TOKEN_ENCODING, "sentence_segmenter": "pysbd:0.3.4"}}, flow_id):
        raise ValueError("Corpus collection promotion failed")
    print(f"Corpus collection rebuilt with {len(records)} passages using {OpenAIEmbeddingsRepository.model_name}")


if __name__ == "__main__":
    build_corpus_chroma_index()
