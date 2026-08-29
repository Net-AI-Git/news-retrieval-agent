# Knowledge retrieval and question answering

Python 3.11+ agent that indexes a news corpus, exposes typed retrieval tools, and answers 11 evaluation questions with grounded citations or an explicit refusal.

This directory is the assignment package: `solution.py`, `pyproject.toml`, source data under `src/data/`, and generated answers under `output_for_mission/`.

## Quickstart

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). From this `project` directory:

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. Defaults already point at OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`) and the models used in the recorded run. Do not put a key in any committed file.

```bash
uv sync
uv run python solution.py
```

That command:

1. Loads environment variables from `.env`.
2. Builds or reuses the Facts Chroma index from `src/data/` (`build_index`).
3. Calls `answer` once per row in `src/data/questions.json`.
4. Writes `output_for_mission/answers.json` and `output_for_mission/transcripts.json`.

A Facts index is required before answering. If `output_for_mission/facts_chroma` is missing, `build_index` creates it (embedding API calls). If it already exists for the configured embedding model, that handle is reused.

Optional HTTP ping (not required by the harness):

```bash
uv run uvicorn main:app
```

Then open `http://127.0.0.1:8000/api/ping`. Agent runs also write local JSONL traces under `observability/telemetry/`.

### Environment variables

All LLM credentials come from the environment. Required names (`REQUIRED_SOLUTION_ENV_VARS` in `src/conts.py`):

| Variable | Role |
| --- | --- |
| `OPENAI_API_KEY` | API credential (OpenRouter or compatible) |
| `OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `OPENAI_EMBEDDING_MODEL` | Embedding model for index and query |
| `OPENAI_GATHER_AGENT_MODEL` | Gather (decompose) |
| `OPENAI_GRADE_AGENT_MODEL` | Grade (enough / missing hop / empty stop) |
| `OPENAI_ANSWER_AGENT_MODEL` | Answer / refuse |
| `OPENAI_RETRIEVE_AGENT_MODEL` | Retrieve (`search_facts` arguments) |

Copy `project/.env.example`. Missing required variables fail at runtime without printing the secret.

### Public interface

`solution.py` exposes the harness contract:

- `build_index(data_dir) -> object` — opaque Facts-index handle.
- `answer(index, question_id, question) -> dict` — `{ "answer": str, "citations": [ { "article_title": str, "snippet": str } ] }`.

At answer time the loop does not read `corpus.json` or `facts.json` into the prompt. Knowledge arrives only through the bound `search_facts` tool.

### Assignment artifacts

| File | What it is |
| --- | --- |
| `output_for_mission/answers.json` | 11 public answers and citations |
| `output_for_mission/transcripts.json` | Gather / retrieve / tool / grade / answer turns for those runs |
| `pyproject.toml` | Dependency manifest (`uv sync`) |

Recorded local-GT quality for the public path: `tests/live_e2e_gt` `TOTAL.task_success` = 100 on `outputs/metrics_2026-08-29_15-36-04.csv` (and earlier 11/11 on `13-52-52` / `14-09-32`). Schema audit: `tests/answers_transcripts_evaluation`.

### Selected inputs

Both `facts.json` and `corpus.json` are indexed. Answer-time retrieval in the agent loop uses **Facts only** (`search_facts`). Facts are sentence-level, already aligned to `article_title` / `url`, and cheap to rank. Corpus passages exist as a second store for rebuild and for the unused `search_corpus` tool. They are not bound in the answering loop: on this 11-question set, gold evidence for answerable items is in Facts, and unanswerable items (Q04, Q09) have no supporting facts. Binding corpus would add nearest-passage noise without a gold sentence.

Citation contract on every retrieved item: `article_title`, `snippet` (stored document), plus `url` and `published_at` for filtering and Answer’s clock. The public `answer` dict copies only `article_title` and `snippet`.

## Traceable Retrieval Indexes

This section records the current retrieval decisions in full. They can be shortened later, but changes to these decisions must be intentional because they affect index compatibility and retrieval behavior.

### Retrieval strategy

The first retrieval implementation is semantic search with embeddings. This is the simplest useful baseline for questions whose wording differs from the evidence wording. Lexical or hybrid search, query expansion and additional entity or temporal logic remain possible accuracy improvements.

Facts and Corpus are both retrievable, but they serve different purposes:

- Facts provide compact, curated evidence and should usually be searched first when a direct answer may exist.
- Corpus passages provide broader source context, cross-article evidence and supporting details that are absent from the curated facts.
- A retrieval flow may query one or both stores. Results must remain bounded before they are placed in an LLM context.

The full parent article is not duplicated into Chroma at this stage. Corpus stores passages only, while `src/data/corpus.json` remains the deterministic source used to rebuild the index. Article-level storage can be added later if retrieval evaluation shows that passage expansion is required.

### Query contract and confidence

At query time, only the question is sent to the embedding API. Facts and Corpus embeddings are read from their existing persistent indexes and are never regenerated by retrieval. The one question embedding is reused for two independent cosine-similarity queries: one Facts candidate and one Corpus passage candidate. The result keeps both ranked lists separate and returns `article_title`, the exact stored document as `snippet`, `url`, `published_at` and a `match_percentage`.

Optional inclusive `published_from` and `published_to` values are applied as numeric filters over `published_at_epoch` before Chroma ranks the remaining candidates. This is date filtering, not chronological sorting: retained results are still ordered by semantic similarity. Optional `source` is resolved against a JSON source catalog written at facts index time (exact name, then unique substring, then nearest catalog embedding with a similarity floor and a margin over the runner-up); unresolved names drop the source filter rather than guessing. Explicit newest-first or oldest-first ordering and category filters are not part of the current baseline.

`match_percentage` is cosine similarity multiplied by 100 and is not a probability that an answer is correct. Facts keep the single `RETRIEVAL_TOP_K` hit with no cosine drop floor. Corpus still drops below `RETRIEVAL_CORPUS_MIN_SIMILARITY` (0.35). A result is `ok` when either store contains a match of at least 40% (`RETRIEVAL_HIGH_CONFIDENCE_SIMILARITY`), `low_confidence` when retained matches sit below that 40% cut, and `empty` when neither store retains a match. These remain retrieval diagnostics only; answer sufficiency is judged from the evidence list, not from a second numeric cutoff.

The 0.35 corpus floor was calibrated on the GT union Top-5 runs with the current sub-questions, not guessed. Raising it would drop the Q06 Guardian CORPUS hit (35.17). The 0.40 cut is status only and is not a drop filter.

GT `sub_questions` were rewritten on Q03, Q05, Q06, and Q07 (less outlet-specific wording). On the raw index that left FACTS macros unchanged (Success@5 0.7778, Recall@5 0.9074, Precision@5 0.8222). CORPUS Success@5 rose 0.5556 → 0.6667 and Recall@5 0.7778 → 0.8333, mainly because Q06 reached both gold URLs; Q03 CORPUS recall fell without TechCrunch/Fortune in the query. Those rewrites remain the live GT queries.

The baseline still performs no lexical fusion, per-article cap or answer generation inside retrieval. Gather decomposes the question; retrieve calls `search_facts` per hop. Each hop returns only the top Facts chunk. Temporal comparison remains possible because every result preserves `published_at`.

### Ranking: what we tried

ASSIGNMENT.md asks for retrieval-layer reasoning, not only the final knob. We did not start at Top-1.

1. **Top-5 + Facts cosine floor 0.35.** Bounded the context, then missed Q05 (The Age, 30.7%) and Q08 (Tremblant, 25.3%). Cosine vs the hop sub-question is not a success rate; that floor threw gold.
2. **Optional `source`.** Exact / unique-substring / catalog-embedding resolve, else drop the filter. With a relaxed floor after a resolved outlet, Top-5 closed those hops (`tests/live_search_facts_gt_calls` `metrics_2026-08-27_19-41-17.csv`, 9/9 recall). The union was still large (often 8–22 facts).
3. **Drop the Facts floor.** Weak golds must survive when Gather omits `source`. Corpus keeps 0.35. Status `ok` / `low_confidence` still uses 0.40 and is not a drop.
4. **Rerank the Gather union vs the original question.** Local MiniLM / FlashRank were rejected (free API only). The only free dedicated OpenRouter rerank was `nvidia/llama-nemotron-rerank-vl-1b-v2:free`. Scores sat around `1e-5`–`0.17` and were not a confidence: the weakest gold (Q06, `0.00024`) sat below 31/74 noise rows, keep-8 by embedding cosine already retained every gold snippet, and Q03 gold went from embedding rank 3 to rerank rank 7. Q04/Q09 still forwarded all retrieved noise. **Removed.** Tests: `tests/_archive/rerank_evidence/`.
5. **One fact per URL.** Repeated *titles* in those CSVs were different sentences from the same article, which is allowed. Collapsing by URL (`20-55-40`) was reverted.
6. **Rank inside the hop, not the union.** Every answerable gold is already rank 1 of *its* sub-question. A weak sibling score (for example Lions at 16.75%) was the *other* hop retrieving that gold as rank 4.

Shipped: `RETRIEVAL_TOP_K=1`, no reranker. Live GT args `metrics_2026-08-27_22-25-11.csv`: 9/9 gold URL+snippet, 0 extra URLs on answerable questions, two or three facts to Answer. Q04/Q09 still return one nearest noise sentence per hop; cosine cannot drop those without also dropping Q08 gold (25.3%). That leftover is Gather/Answer (the store has no Pets Best / Forerunner facts), not a retrieval cutoff. Working log: `plans/pda-knowledge-retrieval-assignment/TASK-03-decisions.md`.

The agent-facing retrieval surface is two typed tools in `src/tools/retrieval_tools.py`: `search_facts` (curated facts) and `search_corpus` (passages). LLM arguments are `question` plus optional inclusive `published_from` / `published_to` and optional `source`. There is no third article-by-title tool, no MCP, and no extra filters (`limit`, category, entity, pagination). Each call returns `status`, the query, and a bounded citation-ready `results` list. Status values are `ok`, `low_confidence`, `empty`, and `invalid` (bad arguments only). `RetrievalTools.as_langchain_tools()` wraps instance methods as `StructuredTool` objects so Chroma paths, `task_data`, and `flow_id` never enter the LLM schema. The answering loop binds only `search_facts` on the retrieve agent; `search_corpus` stays on the class and is not in that allowlist. At answer time, knowledge is reached only through the bound tool: it calls `run_retrieval` and does not read `corpus.json` or `facts.json`. Chronological sorting is still not implemented and is not advertised.

## Agentic grounded answering

Answering is a LangGraph loop, not a single LLM call over pre-fetched hits. `src/orchestration/grounded_answering_workflow.py` owns budgets and stop conditions. `src/agents/gather_agent.py` emits standalone sub-questions and has no tools. `src/agents/retrieve_agent.py` sees one sub-question, binds `search_facts`, and fills `source` / publication dates. `src/agents/answer_agent.py` has no tools and emits structured `answered` / `refused` output. `search_corpus` is out of this loop.

Chat and embeddings stay on OpenRouter. Gather reads `openai/gpt-4.1` from `OPENAI_GATHER_AGENT_MODEL`. Grade reads `openai/gpt-4.1-mini` from `OPENAI_GRADE_AGENT_MODEL`. Retrieve reads `openai/gpt-4o-mini` from `OPENAI_RETRIEVE_AGENT_MODEL`. Answer reads `openai/gpt-4o-mini` from `OPENAI_ANSWER_AGENT_MODEL`. Embeddings stay on `OPENAI_EMBEDDING_MODEL`. Each agent constructs `ChatOpenAI` from env as runtime, not through a GPT repository.

State keeps the gather/retrieve message thread plus an `evidence` list of `RetrievedItem` dicts. Retrieve and Answer see the per-hop top-1 Facts hits. Gather stops when it emits no sub-questions, retrieve stops when it emits no `tool_calls`, or orchestration hits 6 gather LLM turns or 5 tool calls, then Answer runs. A non-refusal answer must copy the supporting evidence `snippet` and `url` verbatim. Orchestration keeps a citation only when both fields match an evidence item from that run; otherwise the run is coerced to `refused`.

Prompts live in `src/prompts/gather_agent.md`, `src/prompts/retrieve_agent.md`, and `src/prompts/answer_agent.md`. Gather decomposes and must not answer or call tools. Retrieve calls `search_facts` once per sub-question and must not answer. Optional `source` is resolved against the facts source catalog after the hop fills it; unresolved names drop the filter. If facts are not enough, the loop stops; it does not call `search_corpus`. Answer claims or refuses and must not search. Raw `facts.json` / `corpus.json` are never placed in the answer-time prompt.

Answer and retrieve stay on GPT-4o-mini; Gather uses GPT-4.1. Production prompts follow OpenAI's developer-message outline (`# Identity`, `# Instructions`, optional `# Examples`) instead of the older project `ROLE:` / `TASK:` / `RULES:` / confidence-score template. That older template, plus a 4–5 refuse band, treated a supported `No` and any conclusion that is not written in one snippet as a refusal. Putting the 11 evaluation questions (or toy clones of the same traps) into the prompt produces a fake 11/11 and is rejected. The production Answer prompt is short, uses only this-run evidence, treats `published_at` as the clock for before/after, allows combining hops, and requires verbatim `snippet` and `url` because orchestration drops any citation that is not an exact match. The one example is a fake-domain entity extract, not an exam item. Oracle Answer with gold facts injected is 11/11 on that prompt (`tests/oracle_answer_gt` metrics `2026-08-27_21-56-37`, `21-58-37`, `22-16-19`). Gather and retrieve use the same vendor outline.

Retrieve uses an ordered field-by-field prompt: copy the isolated user message into `question` before independently deciding `source` and publication dates. Two contrastive format examples are deliberately fictional (Mosswhistle/Lumen Pond): one contains a fictional newspaper and one contains no outlet. They contain no evaluation entity, fact, URL, date, or renamed decision trap. This longer 24-line / 264-word prompt was chosen over the best 10/11 short zero-shot prompt because two stronger source-wording candidates made omissions worse. On `tests/live_retrieve_gt`, the final prompt passed 11/11 twice (`metrics_2026-08-28_18-12-29.csv`, `18-18-29`; 25/25 isolated retrieve hops in each, zero leakage or argument failures). Gather then passed first-hop gold coverage 11/11 twice against that frozen Retrieve (`tests/live_gather_first_hop` `metrics_2026-08-29_11-16-45.csv`, `11-19-10.csv`): standalone strings, no invented outlets, 3+ abilities on the first named outlet, non-ability event on the second. That closes first-batch gold facts, not Grade stop, citations/refusal, or e2e. Full decision and experiment log: `project/plans/pda-knowledge-retrieval-assignment/TASK-04-decisions.md`.

## How refusal works

The public refusal string is exactly `Insufficient information`. An empty `answer` from the loop is rewritten to that string at the `solution.py` boundary.

Answer sees only this-run `evidence` (Top-1 Facts hits). It does not read `facts.json` or `corpus.json`. It refuses when that list is empty or a needed fact is missing. A supported `No` is an answer, not a refusal.

Orchestration then keeps a citation only when both `snippet` and `url` match an evidence item from the same run. If the model marks `answered` but no citation survives, or it already marked `refused`, the run is coerced to `refused` and `citations` is cleared. The assignment allows leftover citations on a refusal; this implementation does not keep them.

Q04 and Q09 have no supporting facts in the store. Retrieval still returns the nearest sentence (`RETRIEVAL_TOP_K=1`, no Facts cosine drop). Refusal on those questions is Answer’s job, not a retrieval floor.

## Known failure modes

- **Q09 extra gather/retrieve turns.** Grade asks for another hop after the first batch. Live e2e scores this `stop_verdict=too_late` (`grade_success` 0), including after the Chroma query lock (`metrics_2026-08-29_16-09-55.csv`, 4 gather turns / 5 tool calls). The public answer is still `Insufficient information`.

A previous Q01 false refusal came from concurrent `PersistentClient` construction on chromadb 1.5.9, not from Gather/Retrieve. `query_records` now reuses one client per path and serializes sqlite/rust access. That crash did not recur on `16-09-55`.

## What I'd do with two more days

- Cut end-to-end latency (fewer serial waits, cheaper hops, less extra Grade looping).
- Retry Gather / Grade / Retrieve / Answer on smaller or `:free` OpenRouter models and keep a candidate only if live e2e stays at 11/11.
- Write additional ground-truth questions (same corpus, not the current 11) and run the same boards, so the prompts are not tuned to one exam set.
- Run the existing local logs and OTLP JSONL behind Docker so traces are easier to browse than raw files and the HTML dashboard.

## Cost-aware LLM usage

Numbers below use the dashboard rate table in `observability/logging_dashboard/build_dashboard.py` (`MODEL_USD_PER_MILLION`) on the 11 `flow_id`s from `tests/live_e2e_gt/outputs/metrics_2026-08-29_16-09-55.csv`. That is an estimate, not an OpenRouter invoice. The Cost tab’s 20-minute window was not used: it mixes runs and prices spans with no `model` at a fallback $1 / $3 per million tokens (workflow, tools, retrieval char counts). Those rows are omitted here.

Embeddings in that run are the free Nemotron model (`OPENAI_EMBEDDING_MODEL`); the table rates them at $0. Chat was Gather `openai/gpt-4.1`, Grade `openai/gpt-4.1-mini`, Retrieve and Answer `openai/gpt-4o-mini`.

| Slice | Est. USD | Notes |
| --- | --- | --- |
| All 11 questions | $0.023 | Sum of chat spans with a model id |
| Mean per question | $0.002 | $0.023 / 11; range $0.0012 (Q10) – $0.0067 (Q09) |
| Full answering pass | $0.023 over 141 s | First to last span among those 11 flows; question `duration_ms` sums to 105 s |

Q09 is the expensive question because Grade kept looping. No reranker. No `search_corpus` in the loop. Index text is not pasted into prompts. These 11 flows include per-hop query embeddings only (rated $0), not a Facts/Corpus rebuild.

By chat agent on that pass: Gather $0.015, Grade $0.004, Answer $0.002, Retrieve $0.002.

## Working at 100× scale

At ~25k facts and ~760k passages, a local Chroma/SQLite store plus a process lock on `query_records` cannot serve parallel hops. Replace it with a vector index that allows concurrent queries.

A full rebuild would embed ~100× more passages. Do it in batches off the request path, not as one synchronous `build_index` with a free-tier embedding model.

Top-1 cosine per hop gets noisier as the store grows. Add lexical/hybrid search (or a bounded Top-k), not a single nearest fact.

### Agent loop: what we tried

ASSIGNMENT.md asks for agent-loop reasoning, not only the final graph. We did not start with two retrieval agents.

1. **One Gather with `search_facts`.** Decompose and fill `source` / dates in the same `bind_tools` turn. Grade after tools decides `enough`, `missing_hop`, or `empty_stop`; all retrieved chunks remain accumulated for Answer. Prompt-only Gather stalled at 7/11; Gather+Grade reached 9/11 (`tests/live_gather_gt`). First-hop-only board (no Grade) peaked at 9/11 (`tests/live_gather_first_hop` `metrics_2026-08-28_14-44-01.csv`).
2. **The pairing vs Q05 wall.** Instructing Gather to copy a named outlet onto every pairing call fixed Q02 and copied `The Age` onto Q05’s TechCrunch hops. Instructing it to omit `source` unless the clause names the outlet fixed Q05 and left `source` empty on “Did TechCrunch report…”. Same model, same context, opposite bugs.
3. **Stronger model vs split.** Cross-claim leakage is structural. Retrieve stays on `OPENAI_RETRIEVE_AGENT_MODEL` (`gpt-4o-mini`). Answer stays on `OPENAI_ANSWER_AGENT_MODEL` (`gpt-4o-mini`). Gather uses `OPENAI_GATHER_AGENT_MODEL` (`gpt-4.1`). Grade uses `OPENAI_GRADE_AGENT_MODEL` (`gpt-4.1-mini`) so coverage judging does not move Retrieve or Answer.
4. **Top-2 Facts chunks.** Closed some rank-1 / packed-query gold misses (`16-04-44` 9/11, `16-09-10` 10/11). Did not fix Q05 (wrong `source` filter). Reverted to Top-1 so Answer still sees one fact per hop. Ranking path: `TASK-03-decisions.md`.
5. **Isolated retrieve hop.** Gather emits standalone sub-questions and cannot call tools. Retrieve sees one sub-question, fills filters, calls `search_facts`. Source catalog resolve stays in retrieval (exact / unique substring / embedding among matches, drop if unresolved). First live first-hop score: 8/11 (`metrics_2026-08-28_16-44-21.csv`). Q05 gold complete. Then Q01 rank-1, Q04 packed outlets, and Q07 over-split remained Gather/retrieval issues to close on the chunk board.
6. **Retrieve prompt isolation and reopening.** `tests/live_retrieve_gt` removed Gather, Chroma, Grade, Answer, ranking, and `agent: "unbound"` rows from the score. Four honest short-prompt candidates scored 8/11, 10/11, 5/11, and 2/11. The last two source-specific candidates repeatedly omitted Q07 sources, so the stop rule fired and production returned to the 10/11 candidate. We reopened only to test one new architectural prompt hypothesis: ordered independent field decisions plus required invented source-present/source-absent examples. That unchanged candidate then passed 11/11 twice. The lesson is not that longer prompts are generally better; the useful change was separating copy/classification operations and demonstrating optional-field contrast without evaluation leakage.
7. **Gather strings for frozen isolated Retrieve.** One-agent packaging was already split. Remaining work was making each Gather string a valid isolated user message: one outlet, distinctive nouns, 3+ abilities on the first named outlet, leftover event on the second, never invent an outlet. Batch Retrieve over the whole list scored 8/11 and was rejected. Hop-inventory wording was not the score. Production Gather (`candidate_featured_in_abilities_first_outlet.md`) passed first-hop gold URL+snippet **11/11 twice** (`metrics_2026-08-29_11-16-45.csv`, `11-19-10.csv`) with Retrieve unchanged. Grade stop vs rewrite is still open.

Working log: `plans/pda-knowledge-retrieval-assignment/TASK-04-decisions.md`.

### Retrieval evaluation

Retrieval is evaluated against the per-question ground truth by stable source URL. Document Precision@10 measures how many distinct returned sources are expected, Document Recall@10 measures how many expected sources were reached, and MRR@10 measures the rank of the first correct result. Facts additionally use Exact Fact Recall@10 after whitespace normalization. Q04 and Q09 have no supporting sources in GT. After Top-1, those hops still return the nearest store sentence; they do not pass as `empty`. Refusal on those questions is Answer's job, not a cosine floor.

The 2026-08-23 baseline produced a strict question pass rate of 54.55%: Q01, Q06, Q07 and Q11 retrieved all required evidence, while Q04 and Q09 correctly returned empty. Facts achieved 87.04% macro Document Recall@10 and 87.04% Exact Fact Recall@10; Corpus achieved 77.78% macro Document Recall@10. Q02, Q03, Q05, Q08 and Q10 missed at least one required source.

This result shows that a single semantic query embedding usually ranks one relevant source highly but does not reliably cover every source in multi-part questions. The current baseline is therefore suitable as a measured starting point, not yet as proof of complete multi-source evidence coverage. Query decomposition, hybrid retrieval or evidence expansion should be evaluated before the answer layer treats retrieved evidence as sufficient.

### Vector database decision

Chroma was selected as the local vector database.

- It is free, local, persistent and straightforward to install with Python.
- It supports explicit embeddings, metadata storage and metadata filtering.
- Collections use cosine distance so query distances can be converted into consistent similarity percentages.
- A persistent database is stored as a directory containing SQLite and vector-index files, so it can be rebuilt locally without production infrastructure.
- It fits the assignment's scale and keeps the first semantic-search implementation small.

LanceDB was considered because its table-oriented, columnar model is attractive when typed columns, larger analytical datasets or richer table operations are central. Chroma was preferred here because the immediate requirement is simple local semantic retrieval with metadata filters, not analytical table processing.

Metadata inside one Chroma collection could distinguish Facts from Corpus, but two physical stores were deliberately selected:

- `output_for_mission/facts_chroma` contains the active `facts` collection.
- `vector_stores/corpus_chroma` contains the active `corpus` collection.

This creates an explicit system-level boundary between curated facts and source passages rather than relying only on a metadata filter or collection name. The trade-off is that searches across both evidence types require two queries and result coordination.

Chroma is not a relational database and does not enforce a foreign key between the stores. Referential integrity is therefore deterministic and application-validated: both stores derive the same `article_id` from the exact article title, and the Facts build fails if a referenced title does not exist in Corpus.

### Embedding API decision

Embeddings are generated through the OpenAI-compatible Python client and an API endpoint, not a local model. The endpoint and model are environment-configurable:

- `OPENAI_API_KEY` supplies the API credential.
- `OPENAI_BASE_URL` currently points to the OpenRouter OpenAI-compatible endpoint.
- `OPENAI_EMBEDDING_MODEL` currently defaults to `nvidia/nemotron-3-embed-1b:free`.

The model is not hard-coded into the index logic. Changing it rebuilds all vectors and may change their dimensions, while IDs, documents and traceability metadata remain fixed. API responses are validated for count, order and consistent dimensions before storage.

Index and query text are sent raw. NVIDIA-style `query: ` / `passage: ` prefixes and OpenRouter `extra_body={"input_type": "query"|"passage"}` were measured on the same GT union Top-5 protocol (`tests/gt_union_topk_retrieval_report/README.md`, experiments A/B/C, n=3 identical repeats). A probe showed OpenRouter honors `input_type`: default raw cosine-matches `input_type=query`, while `input_type=passage` is a different vector (cosine 0.771 vs raw), and the string prefix `passage: ` is not the same as `input_type=passage`. Neither prefixes (B) nor `input_type` (C) raised Success@5 or recall versus raw (A); some FACTS precision and CORPUS recall fell. Live code and both Chroma indexes were rebuilt on raw text.

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

Copy `.env.example` to `.env` and set these values:

```dotenv
OPENAI_API_KEY=<FILL_ME>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b:free
OPENAI_GATHER_AGENT_MODEL=openai/gpt-4.1
OPENAI_GRADE_AGENT_MODEL=openai/gpt-4.1-mini
OPENAI_ANSWER_AGENT_MODEL=openai/gpt-4o-mini
OPENAI_RETRIEVE_AGENT_MODEL=openai/gpt-4o-mini
```

- `OPENAI_API_KEY` is the OpenRouter (or compatible) credential.
- `OPENAI_BASE_URL` is the OpenAI-compatible API endpoint.
- `OPENAI_EMBEDDING_MODEL` embeds index text and query text.
- `OPENAI_GATHER_AGENT_MODEL` decomposes a question into standalone sub-questions.
- `OPENAI_GRADE_AGENT_MODEL` judges whether retrieved evidence is enough to stop gathering.
- `OPENAI_ANSWER_AGENT_MODEL` writes the final answer or refusal from this-run evidence.
- `OPENAI_RETRIEVE_AGENT_MODEL` fills `search_facts` arguments for one sub-question.

From the `project` directory, install dependencies and rebuild either store:

```bash
uv sync
uv run python -m src.services.facts_chroma_index_service
uv run python -m src.services.corpus_chroma_index_service
```

The generated Chroma files are local artifacts and are not required in source control. The committed scripts, source JSON files, dependency lock and manifest fingerprints are sufficient to reproduce the same logical databases. Physical SQLite/HNSW files are not expected to be byte-for-byte identical, and vectors may differ when the configured embedding model changes.
