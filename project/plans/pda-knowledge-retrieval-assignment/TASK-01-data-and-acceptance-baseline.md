# TASK 01 — Data and Acceptance Baseline

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-1-data-acceptance-baseline`

## Goal

Establish a verified understanding of the supplied data and the eleven question types, and turn the assignment's hard rules into testable acceptance conditions before choosing a retrieval architecture, library, or model.

## Product Requirements

- The system can read `corpus.json`, `facts.json`, and `questions.json` from a caller-provided data directory.
- The expected fields and all eleven question IDs are validated without modifying the supplied data.
- The questions are classified by product need, including entity lookup, temporal reasoning, cross-article reasoning, yes/no answers, and potentially unanswerable questions.
- The baseline records the mandatory answer-time constraints: tool-only data access, evidence citations, short answers, and refusal when evidence is insufficient.
- The developer records whether the solution will use articles, facts, or both, together with the reason for that choice.

## Research Before Implementation

- Inspect the distributions, missing values, duplicate content, date formats, source fields, and links between facts and articles.
- Determine which query intents the eleven questions require and how many evidence sources each intent may need.
- Compare the product trade-offs of article chunks, supplied facts, or a combined corpus without selecting a specific library in this task definition.
- Decide how supporting text and article titles will remain traceable through indexing, retrieval, and final citation output.
- Identify a cost-aware development strategy that stays within the available LLM budget.

## Implementation Autonomy

The developer chooses all internal structures, validation mechanisms, libraries, models, and analysis artifacts. This task defines only the observable baseline and the decisions that must be recorded.

## Scope

**In:**

- Developer-selected ingestion, validation, analysis, and test files.
- A recorded input strategy and question-intent map that later tasks can rely on.
- Acceptance checks for the assignment's mandatory data and output constraints.

**Out:**

- Building the final retrieval index.
- Defining the agent-facing retrieval tools.
- Answering the eleven questions.
- Implementing optional knowledge-graph or MCP bonuses.

## Success Criteria

- All three supplied files can be loaded from an arbitrary valid `data_dir`.
- All eleven unique question IDs are discovered and their required answer shapes are represented in the baseline.
- Traceability, tool-only access, grounding, and refusal are expressed as testable conditions.
- No retrieval architecture, model, or vendor is imposed by this plan.

## Definition of Done

- [ ] Input schemas and failure behavior for malformed or missing data are verified.
- [ ] The eleven questions have a documented intent and evidence-needs classification.
- [ ] The article/fact/both input decision and its reasoning are recorded for the README.
- [ ] Mandatory constraints are captured as executable checks or explicit acceptance cases.
- [ ] Supplied source data remains unchanged.
- [ ] No credential is committed or hardcoded.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

A merged baseline that proves the input data is understood and loadable, records the retrieval-relevant question needs, and supplies objective acceptance conditions for the remaining tasks without committing the project to an architecture.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — planning and pre-implementation baseline only.

## Open Questions

- none
