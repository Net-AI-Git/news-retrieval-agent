# GT Corpus Union Top-5

## Goal

For each ground-truth question, search the corpus store with every GT sub-question, union the hits, keep the top 5 scores, and measure whether those chunks come from the question's gold articles.

## Scope

Exercises `src/services/retrieval_service.py` with `evidence_store=corpus` against `vector_stores/corpus_chroma`. Queries are `sub_questions` from `src/data/ground_truth/Q01.json` through `Q11.json`. Facts retrieval is out of scope.

## How to run

```text
cd project
uv run python -m tests.gt_corpus_union_topk.run_gt_corpus_union_topk
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and matching ground-truth files. Corpus chunks are already indexed in `vector_stores/corpus_chroma`.

## Expected outcome

`outputs/` receives timestamped files:

- `metrics_*.csv` — Precision@5, Recall@5, Success@5, false positives per question
- `chunks_*.csv` — the top 5 union chunks with HIT/MISS and full snippet text
- `inspection_*.md` — the same chunks in readable form for visual review

A hit is a returned chunk whose URL belongs to that question's GT `corpus` articles. Success@5 is 1 only when every gold article URL appears at least once in the top 5. Q04 and Q09 have empty gold sets: recall is not scored; returned chunks count as false positives.

## Status

Active — last run 2026-08-24 (raw index, n=3 identical to original A). 9 answerable questions: Success@5 0.5556, macro Recall@5 0.7778, macro Precision@5 0.8000. Q04 returned 0 chunks; Q09 returned 3 false positives.
