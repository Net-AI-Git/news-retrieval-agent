# TASK 02 — Traceable Retrieval Layer

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-2-traceable-retrieval-layer`

## Goal

Build the knowledge retrieval capability used by `build_index` so relevant evidence can be found across entities, time, and multiple articles while every retrievable item remains traceable to its source.

## Product Requirements

- `build_index(data_dir)` produces an opaque, reusable handle from the supplied data.
- The eleven questions are classified by product need, including entity lookup, temporal reasoning, cross-article reasoning, yes/no answers, and potentially unanswerable questions. This is a retrieval-design input, not a submitted ground-truth or `answers.json` artifact.
- Retrieval supports those intent classes, including cross-article and temporal evidence needs.
- Every retrievable result retains `article_title`, `snippet`, and optional `url` / `published_at` as recorded in TASK 01, so citations can be produced without reopening raw source files at answer time.
- Results can be kept small and ranked or filtered so they remain useful inside an LLM context window.
- Index construction is reproducible and does not require production-grade infrastructure.

## Research Before Implementation

- Determine which query intents the eleven questions require and how many evidence sources each intent may need.
- Evaluate lexical, semantic, hybrid, metadata-filtered, entity-aware, temporal, and graph-assisted retrieval against the actual question intents.
- Decide the retrieval unit: supplied fact, article passage, article-level record, derived relation, or a justified combination.
- Determine which query operations are required, such as free-text search, entity search, date filtering, source lookup, related-evidence expansion, or exact item retrieval.
- Investigate ranking, deduplication, result limits, and query reformulation needed for multi-hop questions.
- Decide whether index construction uses only deterministic processing or any budgeted LLM-assisted extraction.

## Implementation Autonomy

The developer chooses the representation, algorithms, persistence format, libraries, models, and whether RAG or a graph component is appropriate. The required outcome is evidence retrieval with source traceability, not a prescribed architecture.

## Scope

**In:**

- Developer-selected indexing, retrieval, storage, and test files.
- A documented intent and evidence-needs classification for the eleven questions, used to shape retrieval.
- The `build_index` behavior required by the assignment.
- Retrieval metadata needed for evidence ranking and citation traceability.

**Out:**

- Agent-facing tool definitions.
- Agent planning and answer generation.
- MCP wrapping and knowledge-graph bonus work unless separately approved.
- Remote or production infrastructure.

## Success Criteria

- The index can be built from the provided directory and reused for multiple questions.
- Representative entity, temporal, cross-article, and unanswerable query cases return bounded, source-traceable results.
- Retrieved evidence contains enough information to produce the required citation fields without reopening raw input at answer time.
- The retrieval choice and trade-offs can be explained clearly in the README.

## Definition of Done

- [ ] `build_index` returns a usable opaque handle for valid supplied data.
- [ ] Each retrievable item preserves article title and supporting text.
- [ ] Query results are bounded and suitable for an LLM context window.
- [ ] The eleven questions have a documented intent and evidence-needs classification.
- [ ] Retrieval behavior is tested against every intent class from that classification.
- [ ] Empty and low-confidence result cases are represented without fabricating evidence.
- [ ] Rebuilding the index is documented or a committed prebuilt artifact has a documented rebuild path.
- [ ] Architecture, library, and model choices are recorded as developer decisions.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

A source-traceable retrieval handle and verified retrieval behavior that cover the assignment's entity, time, and multi-article needs while leaving implementation technology under developer control.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — no production deployment is part of this assignment.

## Open Questions

- none

## Ranking decisions (2026-08-27)

Recorded in `TASK-03-decisions.md` (Ranking path) and `project/README.md` (Ranking: what we tried). Closed for this layer: `RETRIEVAL_TOP_K=1`, no Facts cosine drop, no reranker. Live proof: `tests/live_search_facts_gt_calls` `metrics_2026-08-27_22-25-11.csv`.
