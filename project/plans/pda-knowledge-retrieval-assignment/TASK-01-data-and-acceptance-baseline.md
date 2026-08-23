# TASK 01 — Data and Acceptance Baseline

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-1-data-acceptance-baseline`

## Goal

Establish a verified understanding of the supplied data and the eleven question IDs, and turn the assignment's hard rules into testable acceptance conditions before choosing a retrieval architecture, library, or model.

## Product Requirements

- The system can read `corpus.json`, `facts.json`, and `questions.json` from a caller-provided data directory.
- The expected fields and all eleven question IDs are validated without modifying the supplied data.
- The baseline records the mandatory answer-time constraints as the written acceptance cases below. Later tasks must satisfy them; this task does not implement them as automated tests.
- The input strategy is recorded below: both articles and facts, selected at answer time by the agent through tools.
- Citation traceability is recorded below: every retrieved item carries `article_title`, `snippet`, and optional `url` / `published_at`. Index implementation is TASK 02.

## Input Strategy

**Choice:** both `corpus.json` (articles) and `facts.json` (pre-extracted facts).

**How it is used:** retrieval is exposed as separate tool families (facts vs articles). At answer time the agent chooses which tool to call. This task does not define those tools — that is TASK 03.

**Reason:**
- Facts are short, already sentence-level, and fully contained in their source articles, so they are a cheap first look-up.
- Articles remain available when a needed sentence is missing from the 251 facts, or when more context is required for a citation.
- The two sources are not independent corpora: every fact maps to an article by title and URL. Both paths must keep `article_title` and supporting text so citations stay valid.

This wording is the source for the README input-choice paragraph.

## Citation Traceability

**Choice:** every retrievable item, from facts or from articles, must carry the fields needed to cite without reopening raw source files at answer time.

**Required on each retrieved item:**
- `article_title`
- `snippet` — the sentence or passage actually used

**Optional, for filtering and follow-up:**
- `url`
- `published_at`

Index layout, chunking, and retrieval algorithms are TASK 02. This task only records the citation contract.

## Acceptance Constraints

Written acceptance cases only. Not automated in TASK 01. Not a submitted `answers.json` artifact.

1. At answer time, data may be accessed only through retrieval tools — never by reading `corpus.json` or `facts.json` directly into the answering prompt or context.
2. A non-refusal answer must include at least one citation with `article_title` and `snippet`.
3. `answer` is exactly one of: an entity name or short term, `Yes`, `No`, or `Insufficient information`.
4. Yes/no answers are exactly `Yes` or `No` — no other casing, language, or synonym.
5. A refusal answer is exactly `Insufficient information`.
6. A refusal may include non-empty `citations` (for example, evidence that was retrieved but was not sufficient). Empty `citations` remain allowed.
7. An entity answer is the name or term only — no preamble and no unrelated wording. There is no numeric length cap.

## Research Before Implementation

- Inspect the distributions, missing values, duplicate content, date formats, source fields, and links between facts and articles.

## Implementation Autonomy

The developer chooses all internal structures, validation mechanisms, libraries, models, and analysis artifacts. This task defines only the observable baseline and the decisions that must be recorded.

## Scope

**In:**

- Developer-selected ingestion, validation, analysis, and test files.
- A recorded input strategy that later tasks can rely on.
- A recorded citation-traceability contract (`article_title`, `snippet`, optional `url` / `published_at`).
- Written acceptance cases for the assignment's mandatory data and output constraints.

**Out:**

- Building the final retrieval index.
- Defining the agent-facing retrieval tools.
- Answering the eleven questions.
- Per-question intent and evidence-needs classification — owned by TASK 02.
- Automated tests for the acceptance constraints above — later tasks own execution.
- Cost-aware LLM budget strategy and how it is documented — owned by TASK 07.
- Implementing optional knowledge-graph or MCP bonuses.

## Success Criteria

- All three supplied files can be loaded from an arbitrary valid `data_dir`.
- All eleven unique question IDs are discovered.
- The articles+facts input strategy and its rationale are recorded in this plan.
- The citation-traceability contract is recorded in this plan.
- Traceability, tool-only access, grounding, and refusal are recorded as the written acceptance cases in this plan.
- No retrieval architecture, model, or vendor is imposed by this plan.

## Definition of Done

- [ ] Input schemas and failure behavior for malformed or missing data are verified.
- [x] The article/fact/both input decision and its reasoning are recorded in this plan for the README.
- [x] Citation traceability (`article_title`, `snippet`, optional `url` / `published_at`) is recorded in this plan.
- [x] Mandatory constraints are captured as explicit written acceptance cases in this plan.
- [ ] Supplied source data remains unchanged.
- [ ] No credential is committed or hardcoded.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

A merged baseline that proves the input data is understood and loadable, and supplies objective acceptance conditions for the remaining tasks without committing the project to an architecture.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — planning and pre-implementation baseline only.

## Open Questions

- none
