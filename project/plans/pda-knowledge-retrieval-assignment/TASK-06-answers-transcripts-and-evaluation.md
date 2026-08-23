# TASK 06 — Answers, Transcripts, and Evaluation

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-6-answers-transcripts-evaluation`

## Goal

Run the completed system across all eleven questions, create the required machine-readable answers and decision transcripts, and evaluate grounding, refusals, and multi-step behavior before delivery.

## Product Requirements

- `answers.json` contains exactly one entry for each of the eleven question IDs and matches the required schema.
- Answers are short entity names, `Yes`, `No`, or an explicit refusal.
- Citations contain article titles and supporting snippets actually used by the agent.
- Transcripts capture the actual agent decisions and tool calls for all eleven runs, not only final answers.
- Evaluation distinguishes answer correctness, evidence support, citation traceability, tool-only compliance, and appropriate refusal.

## Research Before Implementation

- Define a repeatable evaluation matrix for direct, yes/no, temporal, multi-hop, and unanswerable questions.
- Decide what transcript detail is needed to prove genuine agent behavior without exposing credentials or unnecessary sensitive data.
- Determine how to audit that each citation supports the exact final claim and came from a tool result in the same run.
- Investigate deterministic settings, retry policy, and run-to-run variance within the available budget.
- Define how failures or incomplete runs are recorded without silently replacing them with hand-written answers.

## Implementation Autonomy

The developer chooses the runner, transcript format, evaluation tooling, model settings, and review workflow. The required artifacts and observable evidence are fixed; the internal evaluation architecture is not.

## Scope

**In:**

- Root `answers.json`.
- Developer-selected transcript and evaluation artifacts.
- A repeatable run across all eleven questions and a documented evidence audit.

**Out:**

- Manually inventing answers that were not produced by the system.
- Hiding failed tool calls or unsupported conclusions from transcripts.
- Redesigning the solution solely to optimize unseen ground truth.

## Success Criteria

- The output contains all and only the eleven expected IDs with no duplicates.
- Every non-refusal answer has at least one supporting citation, and every citation can be traced to its run transcript.
- Refusals occur when retrieved evidence is insufficient and are not padded with unsupported citations.
- Transcripts visibly demonstrate multi-step tool use where the question requires it.
- The full run completes within the documented cost and operational limits, or limitations are recorded honestly.

## Definition of Done

- [ ] `answers.json` passes strict schema and ID-completeness validation.
- [ ] All eleven answers were produced through the public solution path.
- [ ] Transcripts exist for all eleven questions and show actual tool calls and decisions.
- [ ] Each non-refusal citation is checked against the retrieved supporting text.
- [ ] Tool-only answer-time access is verified for the recorded runs.
- [ ] Multi-hop cases show evidence accumulation from the required number of sources when justified.
- [ ] Unanswerable or unsupported cases refuse rather than guess.
- [ ] Cost, retries, failures, and known quality limitations are recorded.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

A schema-valid `answers.json`, complete agent transcripts for all eleven questions, and a repeatable evidence-based evaluation showing how each answer or refusal was produced.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — generated assignment artifacts can be regenerated from the merged system.

## Open Questions

- none
