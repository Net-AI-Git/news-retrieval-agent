# GT Union Top-5 Retrieval Report

## Goal

Record retrieval experiment configs and results for FACTS and CORPUS union Top-5, so later configs can be compared to these numbers.

## Scope

Compares three embedding setups of the same evaluation:

- Experiment A: raw text, no NVIDIA `query:` / `passage:` prefixes, no `input_type`
- Experiment B: string prefixes `query: ` / `passage: ` on index and query
- Experiment C: raw text plus OpenRouter/NVIDIA `extra_body={"input_type": "query"|"passage"}` (no string prefixes)

Runners: `tests/gt_facts_union_topk/run_gt_facts_union_topk.py`, `tests/gt_corpus_union_topk/run_gt_corpus_union_topk.py`. Retrieval path: `src/services/retrieval_service.py` + Chroma stores.

## How to run

```text
cd project
uv run python -m tests.gt_facts_union_topk.run_gt_facts_union_topk
uv run python -m tests.gt_corpus_union_topk.run_gt_corpus_union_topk
```

Rebuild indexes after changing embedding input handling:

```text
uv run python -m src.services.facts_chroma_index_service
uv run python -m src.services.corpus_chroma_index_service
```

## Inputs

No files in `inputs/`. Queries are `sub_questions` in `src/data/ground_truth/Q01.json`–`Q11.json`. Gold is URL overlap with GT `facts` or `corpus`. Q04 and Q09 have empty gold (unanswerable); they are excluded from Success/Recall/Precision macros.

## Expected outcome

This file lists config, per-run artifacts, and averages. Experiments A, B, and C are averaged over repeated runs on a frozen index where repeats exist. A originally had one run; after reverting the live index to raw it was repeated n=3.

## Status

Active — 2026-08-24. Live index is Experiment A (raw text, no prefixes, no `input_type`). B and C are recorded ablations. A/B/C repeats were identical across n=3.

---

## Shared evaluation protocol

| Item | Value |
|---|---|
| Questions | Q01–Q11 (9 answerable + Q04, Q09 unanswerable) |
| Query source | GT `sub_questions` (not the agent) |
| Per sub-question retrieve `k` | `RETRIEVAL_TOP_K = 10` |
| Union then keep | Top 5 by `match_percentage` |
| Similarity | cosine (`CHROMA_DISTANCE_METRIC`) |
| Drop below | `RETRIEVAL_FACTS_MIN_SIMILARITY = 0.35`, `RETRIEVAL_CORPUS_MIN_SIMILARITY = 0.35` (A/B/C and the rewritten-sub-question run used the previous shared `0.3`) |
| Hit | returned `url` is in that question's gold URL set |
| Success@5 | 1 iff every gold URL appears at least once in the top 5 |
| Date filters | not applied by this eval runner |
| Extra retrievers | none (no BM25, no RRF, no rerank) |
| Source / entity filters | none |
| Chat / gather LLM | not used (`OPENAI_MODEL` unused here) |

Macros average the 9 answerable questions equally.

---

## System config

### Experiment A — raw text (current code)

| Key | Value |
|---|---|
| Embedding model | `nvidia/nemotron-3-embed-1b:free` |
| Embedding API | OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`) |
| Query prefix | none (raw question text) |
| Passage prefix | none (raw fact / title+chunk text) |
| API `input_type` | none |
| Facts index text | fact sentence only |
| Corpus index text | `{title}\n\n{chunk}` |
| Facts count | 251 |
| Corpus passages | 7629 |
| Chat model (idle) | `openai/gpt-4o-mini` |
| Index rebuilt | 2026-08-24 after reverting off `input_type` (251 facts, 7629 passages) |

First run (pre-ablation):

- FACTS `tests/gt_facts_union_topk/outputs/metrics_2026-08-24_17-30-43.csv`
- CORPUS `tests/gt_corpus_union_topk/outputs/metrics_2026-08-24_17-19-59.csv`

Repeated runs after raw rebuild (identical to the first run):

| Store | Runs |
|---|---|
| FACTS | `22-26-09`, `22-26-18`, `22-26-26` |
| CORPUS | `22-26-35`, `22-26-44`, `22-26-52` |

### Experiment B — string prefixes

Same as A except:

| Key | Value |
|---|---|
| Query prefix | `query: ` |
| Passage prefix | `passage: ` |
| API `input_type` | none |
| Index rebuilt | 2026-08-24 after prefix change (251 facts, 7629 passages) |

Repeated runs (identical metrics):

| Store | Runs |
|---|---|
| FACTS | `21-43-34`, `21-49-08`, `21-49-27` |
| CORPUS | `21-43-53`, `21-49-18`, `21-49-36` |

### Experiment C — API `input_type`

Same as A except:

| Key | Value |
|---|---|
| Query prefix | none |
| Passage prefix | none |
| Query `extra_body` | `{"input_type": "query"}` |
| Passage `extra_body` | `{"input_type": "passage"}` |
| Index rebuilt | 2026-08-24 after `input_type` change (251 facts, 7629 passages) |

Repeated runs (identical metrics):

| Store | Runs |
|---|---|
| FACTS | `22-12-30`, `22-13-54`, `22-14-03` |
| CORPUS | `22-12-55`, `22-14-12`, `22-14-21` |

Averages below equal each A/B/C run because all repeats matched.

---

## API check before C

Same raw sentence, OpenRouter `nvidia/nemotron-3-embed-1b:free`:

| Pair | Cosine |
|---|---|
| raw vs `input_type=query` | 1.000 |
| raw vs `input_type=passage` | 0.771 |
| `input_type=query` vs `input_type=passage` | 0.771 |
| `input_type=query` vs string `query: ` | 0.990 |
| `input_type=passage` vs string `passage: ` | 0.783 |
| string `query: ` vs string `passage: ` | 0.985 |

`input_type` is honored. Default raw ≈ query. String `passage: ` is **not** the same as `input_type=passage`. Experiment B therefore did not put documents in NVIDIA passage space.

---

## FACTS results

| Metric | A mean (raw, n=3) | B mean (prefixes, n=3) | C mean (`input_type`, n=3) |
|---|---|---|---|
| Success@5 | 0.7778 | 0.7778 | 0.7778 |
| Macro Recall@5 | 0.9074 | 0.9074 | 0.9074 |
| Macro Precision@5 | 0.8222 | 0.7852 | 0.8000 |

Failed Success@5 in all three: Q05 (missing The Age URL), Q08 (missing Independent Canada URL). Q04 returned 0 facts in all three. Q09 returned 0 in A/B and 2 false positives in C.

| Q | A P@5 | B P@5 | C P@5 | A R@5 | B R@5 | C R@5 | A Succ | B Succ | C Succ |
|---|---|---|---|---|---|---|---|---|---|
| Q01 | 1.0 | 0.6667 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q02 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q03 | 0.6 | 0.8 | 0.6 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q05 | 0.6 | 0.6 | 0.6 | 0.6667 | 0.6667 | 0.6667 | 0 | 0 | 0 |
| Q06 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q07 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q08 | 1.0 | 1.0 | 1.0 | 0.5 | 0.5 | 0.5 | 0 | 0 | 0 |
| Q10 | 0.8 | 0.6 | 0.6 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q11 | 0.4 | 0.4 | 0.4 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |

C restored Q01 precision to A. It did not recover Q05/Q08. Precision sits between A and B.

---

## CORPUS results

| Metric | A mean (raw, n=3) | B mean (prefixes, n=3) | C mean (`input_type`, n=3) |
|---|---|---|---|
| Success@5 | 0.5556 | 0.5556 | 0.5556 |
| Macro Recall@5 | 0.7778 | 0.7407 | 0.7407 |
| Macro Precision@5 | 0.8000 | 0.7778 | 0.8000 |

| Q | A P@5 | B P@5 | C P@5 | A R@5 | B R@5 | C R@5 | A Succ | B Succ | C Succ |
|---|---|---|---|---|---|---|---|---|---|
| Q01 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q02 | 1.0 | 1.0 | 1.0 | 0.5 | 0.5 | 0.5 | 0 | 0 | 0 |
| Q03 | 0.4 | 0.2 | 0.2 | 0.6667 | 0.3333 | 0.3333 | 0 | 0 | 0 |
| Q05 | 1.0 | 1.0 | 1.0 | 0.3333 | 0.3333 | 0.3333 | 0 | 0 | 0 |
| Q06 | 1.0 | 1.0 | 1.0 | 0.5 | 0.5 | 0.5 | 0 | 0 | 0 |
| Q07 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q08 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q10 | 0.4 | 0.4 | 0.6 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |
| Q11 | 0.4 | 0.4 | 0.4 | 1.0 | 1.0 | 1.0 | 1 | 1 | 1 |

Q04 returned 0 in all three. Q09 false positives: 3 in A/B, 5 in C. Success@5 unchanged. C matches B on Q03 recall (worse than A) and recovers A precision via Q10.

---

## Reading the averages

Repeating A, B, and C three times on a frozen Chroma index produced the same per-question scores. Difference A vs B vs C is the embedding contract, not run noise. String prefixes (B) were the wrong NVIDIA recipe for this OpenRouter endpoint. API `input_type` (C) is the contract that actually changes the vector; it did not raise Success@5 or FACTS/CORPUS recall versus A. Live code and index were reverted to A.
