# End-to-end GT evaluation

## Goal

Run the full Gather → retrieve → tools → Answer pipeline on all 11 questions, score every stage against `src/data/ground_truth`, and write one CSV row per question so a failure can be attributed to decomposition, RAG, Gather, Answer, or citations — without an LLM-as-a-judge.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py`, `src/agents/gather_agent.py`, `src/agents/retrieve_agent.py`, `src/agents/answer_agent.py`, `src/tools/retrieval_tools.py`, `src/services/retrieval_service.py`, and `src/data/ground_truth/Q01.json`–`Q11.json`. Isolated RAG already living in `tests/gt_facts_union_topk` is not imported; this runner re-queries facts with the GT sub-questions only to split “agent asked a bad query” from “the retriever cannot surface gold”.

## How to run

```text
cd project
uv sync
uv run python -m tests.end_to_end_gt_evaluation.test_end_to_end_gt_evaluation --smoke
uv run python -m tests.end_to_end_gt_evaluation.test_end_to_end_gt_evaluation
```

Needs `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_AGENT_MODEL`, `OPENAI_GRADE_AGENT_MODEL`, `OPENAI_ANSWER_AGENT_MODEL`, `OPENAI_RETRIEVE_AGENT_MODEL`, and `OPENAI_EMBEDDING_MODEL`, plus existing `output_for_mission/facts_chroma` and `vector_stores/corpus_chroma`. Live LLM and embedding calls. `--smoke` runs Q01 only.

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and the matching ground-truth file for each id.

## Expected outcome

`outputs/stage_eval_<timestamp>.csv` — 11 rows (one per question) and **11 columns**, utf-8-sig:

1. `question_id` — Q01–Q11.
2. `e2e_success` — 1 only when the filtered answer matches GT (including refusal on unanswerable) and, for answerable questions, every GT citation title is present in the system citations.
3. `tool_calls` — JSON: how Gather called tools — `pattern` (`parallel` / `sequential` / `mixed` / `no_tools`), `gather_count`, `tool_count`, `parallel_batch_sizes`, per-turn gather/tools log (queries, `next_route`, hit URLs), plus the flat `calls` list (name, query, date filters, hit count, gold-hit count, empty).
4. `wasted_tool_calls` — JSON: calls that did not help — `duplicate`, `after_gold_complete`, or `extra_tool` (not in GT required/conditional tools). A required call that missed gold is a RAG/query miss, not waste.
5. `rag_gold_recall` — JSON: isolated facts retrieval on GT required `search_facts` queries (oracle). `url_recall` / `snippet_recall` vs GT facts. Empty recalls on Q04/Q09; false-positive count still recorded.
6. `answer_vs_gt` — JSON: GT answer vs raw Answer-agent output vs orchestration-filtered output, plus `correct`.
7. `gather_missing` — JSON: gold fact URLs/sentences that never appeared in Gather evidence (`url_recall` blank on unanswerable); per-hop `hops`; `stopped_with_missing_hop`; `stop.verdict` = `on_time` | `too_early` | `too_late` | `budget_forced`.
8. `decomposition` — JSON: GT `sub_questions` vs agent tool queries (token overlap ≥ 0.4), unmatched GT sub-questions, extra agent queries, required-tool coverage, date-filter counts.
9. `citations_vs_gt` — JSON: GT citation titles/snippets vs Answer citations (`title_recall` / `snippet_recall`).
10. `failure_stage` — first blocking stage: `none` | `rag` | `decompose` | `gather` | `answer` | `citation` | `runtime_error`.
11. `answer_error_type` — `none` | `wrong_answer` | `false_refusal` | `false_answer` | `citation_stripped` | `missing_citations` | `runtime_error`.

`outputs/traces_<timestamp>.json` — the same rows with JSON cells parsed, for inspection outside Excel.

Scoring is deterministic string/URL/token overlap only. No second LLM.

### Failure-stage order (answerable)

1. `rag` — oracle facts search on GT sub-questions misses a gold URL (retriever/index).
2. `decompose` — oracle is complete, but agent queries miss a GT sub-question and Gather also misses gold (query plan).
3. `gather` — queries cover GT sub-questions (or oracle is complete) but gold never lands in evidence (did not call, budget, or tool choice).
4. `answer` — gold is in evidence, final answer does not match GT (includes false refusal). `citation_stripped` means Answer produced `answered` and orchestration refused it because snippet+url were not copied from evidence.
5. `citation` — answer text matches, citation titles do not cover GT.
6. `none` — `e2e_success` is 1.

Unanswerable (Q04, Q09): a non-refusal is `answer` / `false_answer`. A refusal is success.

### Additional metrics worth adding next

These did not get their own CSV column; several are already nested in the JSON cells.

- **Hop coverage** — each GT sub-question has at least one matching tool call; `gold_hit_count` on that call is in `gather_missing.hops`.
- **Stop timing** — `gather_missing.stop.verdict`: stopped after gold was complete (`on_time`), stopped with a hop still missing (`too_early`), kept calling after gold was complete (`too_late`), or hit `GATHER_MAX_LLM_TURNS` / `GATHER_MAX_TOOL_CALLS` with gold still missing (`budget_forced`).
- **Tool call pattern** — `tool_calls.pattern` and `turns`: one Gather turn with several `search_facts` is `parallel`; one call per Gather turn is `sequential`.
- **Evidence precision** — retrieved URLs that are not gold (noise into Answer).
- **Gold rank / MRR** — position of the first gold hit in each tool result (threshold vs ranking).
- **Date-filter exactness** — Q08 required windows vs agent `published_from`/`published_to` (counts are in `decomposition`).
- **Snippet-in-evidence rate** — Answer snippets that are exact evidence copies before the orchestrator filter.
- **Turn count / tool latency** — cost of a question, not just correctness. `gather_count` / `tool_count` are in `tool_calls`.
- **Alias/entity normalization** — `SBF` vs `Sam Bankman-Fried` currently fails exact+containment unless the GT string is contained in the prediction.

## Status

Active — full 11-question run 2026-08-26 (`outputs/stage_eval_2026-08-26_19-54-27.csv`). Smoke Q01 still `on_time` / `parallel`.

Gate 0 GT audit (2026-08-27): keep all 11 vs `facts.json`; corpus not audited. Full write-up: `project/plans/pda-knowledge-retrieval-assignment/TASK-06-answers-transcripts-and-evaluation.md` (section “Gate 0 audit — 2026-08-27”).
