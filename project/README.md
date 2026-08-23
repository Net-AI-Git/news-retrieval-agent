### Template AI Microservice API

#### Template Setup — fill these before first run
After cloning, replace every `<FILL_ME>` / `<project-name>` placeholder:
1. `pyproject.toml` → `name` — set the service name.
2. `README.md` clone commands below → replace `<project-name>` with the new repo name.
3. `.env` → fill every `<FILL_ME>` value (copy from the template `.env`, see path at the bottom).
4. `src/conts.py` → `OTEL_SERVICE_NAME` — set the OpenTelemetry service name used by OpenSearch.

#### Local Run
- Copy the .env file to your local repo, this file contains the environment variables.

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then install the project dependencies:
```bash
uv sync
```

- Run the uvicorn server:
```bash
uv run uvicorn main:app
```


- Verify the API works properly at http://127.0.0.1:8000/api/ping, and there are no errors in the console.


- Clone the template into a new project 
```bash
# 1. Clone the existing repository
git clone https://github.com/<organization>/<project-name>.git
 
# 2. Move into the cloned repository directory
cd <project-name>
 
# 3. Remove the old remote
git remote remove origin
 
# 4. (Create a new repository in GitHub manually)
 
# 5. Add the new remote
git remote add origin https://github.com/<organization>/<new-repo>.git
 
# 6. Push all branches to the new repo
git push --all origin
 
# 7. Push all tags to the new repo
git push --tags origin
 
# 8. Verify remotes (optional)
git remote -v
```

- Copy `.env.example` to `.env` in the project root and fill every placeholder.

## Traceable Retrieval Indexes

This section records the current retrieval decisions in full. They can be shortened later, but changes to these decisions must be intentional because they affect index compatibility and retrieval behavior.

### Retrieval strategy

The first retrieval implementation is semantic search with embeddings. This is the simplest useful baseline for questions whose wording differs from the evidence wording. Lexical or hybrid search, query expansion, reranking and additional entity or temporal logic remain possible accuracy improvements, but they should be added only after the semantic baseline is evaluated.

Facts and Corpus are both retrievable, but they serve different purposes:

- Facts provide compact, curated evidence and should usually be searched first when a direct answer may exist.
- Corpus passages provide broader source context, cross-article evidence and supporting details that are absent from the curated facts.
- A retrieval flow may query one or both stores. Results must remain bounded before they are placed in an LLM context.

The full parent article is not duplicated into Chroma at this stage. Corpus stores passages only, while `src/data/corpus.json` remains the deterministic source used to rebuild the index. Article-level storage can be added later if retrieval evaluation shows that passage expansion is required.

### Vector database decision

Chroma was selected as the local vector database.

- It is free, local, persistent and straightforward to install with Python.
- It supports explicit embeddings, metadata storage and metadata filtering.
- A persistent database is stored as a directory containing SQLite and vector-index files, so it can be rebuilt locally without production infrastructure.
- It fits the assignment's scale and keeps the first semantic-search implementation small.

LanceDB was considered because its table-oriented, columnar model is attractive when typed columns, larger analytical datasets or richer table operations are central. Chroma was preferred here because the immediate requirement is simple local semantic retrieval with metadata filters, not analytical table processing.

Metadata inside one Chroma collection could distinguish Facts from Corpus, but two physical stores were deliberately selected:

- `vector_stores/facts_chroma` contains the active `facts` collection.
- `vector_stores/corpus_chroma` contains the active `corpus` collection.

This creates an explicit system-level boundary between curated facts and source passages rather than relying only on a metadata filter or collection name. The trade-off is that searches across both evidence types require two queries and result coordination.

Chroma is not a relational database and does not enforce a foreign key between the stores. Referential integrity is therefore deterministic and application-validated: both stores derive the same `article_id` from the exact article title, and the Facts build fails if a referenced title does not exist in Corpus.

### Embedding API decision

Embeddings are generated through the OpenAI-compatible Python client and an API endpoint, not a local model. The endpoint and model are environment-configurable:

- `OPENAI_API_KEY` supplies the API credential.
- `OPENAI_BASE_URL` currently points to the OpenRouter OpenAI-compatible endpoint.
- `OPENAI_EMBEDDING_MODEL` currently defaults to `nvidia/nemotron-3-embed-1b:free`.

The model is not hard-coded into the index logic. Changing it rebuilds all vectors and may change their dimensions, while IDs, documents and traceability metadata remain fixed. API responses are validated for count, order and consistent dimensions before storage.

### Facts store schema

Each Facts record uses the fact text as both the stored Chroma document and the embedding input.

| Field | Purpose |
| --- | --- |
| `id` | Deterministic UUID derived from `article_id` and the exact fact text |
| `document` | Exact supplied fact text |
| `article_id` | Deterministic link to the matching Corpus article |
| `article_title` | Exact source article title |
| `source` | Publisher/source name |
| `category` | Supplied article category |
| `published_at` | Original publication timestamp |
| `published_at_epoch` | Integer timestamp for numeric filtering and ordering |
| `url` | Original source URL |

The collection metadata records `embedding_model`, `embedding_dimensions`, `schema_version` and `record_type=fact`.

### Corpus store schema

Each Corpus record stores one passage as its Chroma document. Its embedding input is `article_title + "\n\n" + passage`, so semantic matching benefits from title context without modifying the passage returned as evidence.

| Field | Purpose |
| --- | --- |
| `id` | Deterministic UUID derived from article, paragraph, local paragraph chunk and exact passage |
| `document` | Exact passage returned by retrieval |
| `article_id` | Deterministic article identifier shared with Facts |
| `article_title` | Exact source article title |
| `chunk_index` | Sequential passage position within the article |
| `paragraph_index` | Original paragraph position within the article |
| `source` | Publisher/source name |
| `author` | Supplied author; missing authors are stored as an empty string because Chroma metadata cannot store `None` |
| `category` | Supplied article category |
| `published_at` | Original publication timestamp |
| `published_at_epoch` | Integer timestamp for numeric filtering and ordering |
| `url` | Original source URL |

The collection metadata also records every chunking parameter: target, minimum, maximum, overlap target, hard paragraph boundary, tokenizer encoding and sentence-segmenter version.

### Paragraph and sentence preparation

Corpus chunking is deterministic and follows these steps:

1. Normalize Windows and legacy line endings (`\r\n` and `\r`) to `\n`.
2. Treat one or more blank lines, represented by `\n\n` with optional whitespace, as a hard paragraph boundary.
3. Remove empty paragraphs and surrounding paragraph whitespace.
4. Never join a short paragraph to the next paragraph. This intentionally preserves document structure even though it produces many passages below 400 tokens.
5. Keep a paragraph unchanged when it is at most 600 tokens.
6. Split only paragraphs above 600 tokens into sentence units.

`pySBD` 0.3.4 was chosen for English sentence segmentation. It is a lightweight, deterministic, rule-based segmenter that handles sentence-boundary cases such as abbreviations and punctuation better than a simple regular expression, without requiring a local statistical model or downloaded language pipeline. Compared with heavier NLP libraries such as spaCy, it adds less installation and runtime overhead for the single requirement of sentence-boundary detection. Compared with naive `\n` or punctuation splitting, it provides explicit character spans that allow the original text to be preserved.

`pySBD` is used with `clean=False` and `char_span=True`. Chunk text is sliced from the original paragraph using the returned span boundaries rather than reconstructed from cleaned sentences. During development, `pySBD` was found to omit trailing text when the final sentence had no terminal punctuation. The final returned boundary is therefore extended to the exact paragraph length, and the concatenated sentence units are validated against the original paragraph. This correction is part of the rebuild code.

### Chunk sizing and overlap

Token counts use the deterministic `cl100k_base` encoding:

- Target chunk size: 500 tokens.
- Soft minimum: 400 tokens.
- Maximum: 600 tokens.
- Target overlap: approximately 100 tokens.

The target and minimum are soft preferences; the maximum is respected unless a single sentence itself exceeds 600 tokens. A sentence is added when it remains under the 500-token target, when it helps a chunk below 400 tokens without exceeding 600, or when the candidate remains under 600 and is closer to the 500-token target than the current chunk.

No sentence is cut to satisfy either the chunk target or overlap target. Overlap is selected from complete trailing sentences, choosing the suffix whose token count is closest to 100. A single oversized sentence remains intact. Paragraph boundaries are never crossed by either the main chunk or its overlap.

The accepted build produced 7,629 Corpus passages from 150 articles. Many passages are intentionally short because short paragraphs are preserved rather than merged.

### Determinism, validation and replacement

- `article_id`, Fact IDs and Corpus passage IDs use deterministic UUID5 values.
- Facts currently require exactly 251 logical records.
- Corpus currently requires exactly 7,629 logical passages.
- Each script contains an approved SHA-256 manifest covering every sorted ID, document and metadata object.
- A rebuild stops before embedding if its logical records do not match the approved manifest.
- Every embedding batch is validated before it is upserted.
- Every stored ID, document, metadata object and embedding dimension is read back and validated.
- Rebuilds write to `facts_staging` or `corpus_staging`. The active collection is replaced only after the staging collection is complete and valid.

The manifest intentionally excludes vector values so a different embedding model can be evaluated without changing the evidence contract. Changing source data, metadata, ID generation or chunking rules requires an explicit manifest update.

### Rebuild

Set these values in `.env`:

```dotenv
OPENAI_API_KEY=<FILL_ME>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b:free
```

From the `project` directory, install dependencies and rebuild either store:

```bash
uv sync
uv run python -m src.services.facts_chroma_index_service
uv run python -m src.services.corpus_chroma_index_service
```

The generated Chroma files are local artifacts and are not required in source control. The committed scripts, source JSON files, dependency lock and manifest fingerprints are sufficient to reproduce the same logical databases. Physical SQLite/HNSW files are not expected to be byte-for-byte identical, and vectors may differ when the configured embedding model changes.
