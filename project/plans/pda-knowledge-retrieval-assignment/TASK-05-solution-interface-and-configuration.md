# TASK 05 — Solution Interface and Configuration

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-5-solution-interface-configuration`

## Goal

Integrate indexing, tools, and agent behavior behind the exact public interface required by the evaluation harness, with environment-based credentials and stable output contracts.

## Product Requirements

- Repository root contains `solution.py` with exactly the required public functions `build_index(data_dir: str) -> object` and `answer(index: object, question_id: str, question: str) -> dict`.
- `build_index` returns an opaque handle accepted by `answer`.
- `answer` returns only the required `answer` string and `citations` list shape.
- Each citation contains `article_title` and `snippet` strings.
- LLM credentials and provider configuration come from environment variables and are never hardcoded.
- The imported interface can run from an external harness without relying on an interactive development environment.

## Research Before Implementation

- Determine the minimum stable boundary between the mandatory `solution.py` functions and developer-selected internals.
- Define validation and failure behavior for unknown question IDs, malformed arguments, missing configuration, and unavailable model access.
- Decide which configuration values must be environment-driven and which safe defaults are acceptable.
- Investigate how to preserve the answer-time tool-only rule across the integration boundary.
- Determine whether index build should occur live or load a committed artifact, and document the rebuild implications.

## Implementation Autonomy

The developer chooses all internal module boundaries, configuration mechanisms, libraries, and index-handle representation. Only the evaluator-facing file, function names, signatures, and output shape are fixed.

## Scope

**In:**

- Root `solution.py` and developer-selected integration and configuration files.
- Importability, argument handling, opaque index passing, and output-schema enforcement.
- Environment-based credential and provider configuration.

**Out:**

- Generating the final eleven answers and transcripts.
- Choosing new retrieval or agent behavior not needed for integration.
- CI/CD or deployment infrastructure.

## Success Criteria

- A clean Python 3.11+ process can import both required functions from root `solution.py`.
- A valid `data_dir` can be indexed and passed to `answer` without knowledge of the handle's internal type.
- Every success and refusal response conforms exactly to the required dictionary schema.
- No secret or access key exists in tracked source or documentation.

## Definition of Done

- [ ] Root `solution.py` exposes both required functions with the exact signatures.
- [ ] An evaluator-style import and call path passes end to end.
- [ ] Output validation covers answer type and citation field types.
- [ ] Refusal responses are schema-valid and may use an empty citation list.
- [ ] Missing or invalid environment configuration fails clearly without revealing secrets.
- [ ] Answer-time raw-data access remains restricted to retrieval tools.
- [ ] No provided OpenRouter key or other credential is present in committed files.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

An evaluator-compatible root interface that connects the implemented system end to end, uses safe external configuration, and returns the assignment's exact answer schema.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — no production deployment is part of this assignment.

## Open Questions

- none
