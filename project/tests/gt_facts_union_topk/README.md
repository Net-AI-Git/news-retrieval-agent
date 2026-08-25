# GT Facts Union Top-5

## Goal

For each ground-truth question, search the facts store with every GT sub-question, union the hits, keep the top 5 scores, and measure whether those facts come from the question's gold fact articles.

## Scope

Exercises `src/services/retrieval_service.py` with `evidence_store=facts` against `vector_stores/facts_chroma`. Queries are `sub_questions` from `src/data/ground_truth/Q01.json` through `Q11.json`. Corpus retrieval is out of scope.

## How to run

```text
cd project
uv run python -m tests.gt_facts_union_topk.run_gt_facts_union_topk
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and matching ground-truth files. Facts are already indexed in `vector_stores/facts_chroma`.

## Expected outcome

`outputs/` receives timestamped files:

- `metrics_*.csv` — Precision@5, Recall@5, Success@5, false positives per question
- `chunks_*.csv` — the top 5 union facts with HIT/MISS and full fact text
- `inspection_*.md` — the same facts in readable form for visual review

A hit is a returned fact whose URL belongs to that question's GT `facts` entries. Success@5 is 1 only when every gold fact URL appears at least once in the top 5. Q04 and Q09 have empty gold sets: recall is not scored; returned facts count as false positives.

## Status

Active — last run 2026-08-24 (raw index, n=3 identical to original A). 9 answerable questions: Success@5 0.7778, macro Recall@5 0.9074, macro Precision@5 0.8222. Q04 and Q09 returned 0 facts. Q05 and Q08 missed a gold URL.
