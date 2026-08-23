# TASK 03 — Retrieval Tool Surface

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-3-retrieval-tool-surface`

## Goal

Expose the retrieval capability through a small, typed, LLM-usable tool surface that lets an agent discover and gather evidence without direct access to raw articles, raw facts, or internal index details.

## Product Requirements

- Tools have clear typed signatures and docstrings written for an LLM consumer.
- The tool set is small enough for reliable selection but expressive enough for the question intents from TASK 02.
- Tool results are bounded, structured, and source-traceable.
- The agent can discover what evidence exists, narrow a search, and follow up across entities, dates, or related articles when needed.
- All answer-time knowledge access can be routed through these tools.

## Research Before Implementation

- Derive tool operations from the actual query intents rather than mirroring internal storage APIs.
- Compare one general search tool with several purpose-specific tools for discovery, filtering, follow-up, and exact evidence retrieval.
- Determine useful parameters for entity, time, source, category, result limit, and pagination or continuation where justified.
- Decide how tools communicate confidence, empty results, ambiguity, identifiers, and citation-ready metadata.
- Evaluate context-size controls and safeguards against returning entire articles unnecessarily.

## Implementation Autonomy

The developer chooses tool names, count, schemas, runtime framework, and internal delegation. This task does not prescribe MCP, function calling, a particular agent SDK, or a retrieval library.

## Scope

**In:**

- Developer-selected tool definitions, schemas, adapters, and tests.
- LLM-facing descriptions and structured response contracts.
- Enforcement of bounded, traceable, answer-time access.

**Out:**

- The agent loop and model choice.
- Final answer wording and refusal policy execution.
- Optional MCP server packaging.
- Changes to supplied source data.

## Success Criteria

- An LLM consumer can infer when and how to call each tool from its signature and description.
- Tool calls cover the identified discovery, narrowing, temporal, entity, and multi-hop evidence needs.
- Tool outputs never require the agent to inspect raw data files directly.
- Results consistently include the metadata needed for citations and remain within explicit size limits.

## Definition of Done

- [ ] A small set of typed retrieval tools is implemented.
- [ ] Every tool has an LLM-facing docstring that explains purpose, parameters, and output.
- [ ] Tool outputs are structured, bounded, and citation-ready.
- [ ] Empty, ambiguous, and no-match responses are explicit and machine-readable.
- [ ] Tests cover valid calls, invalid inputs, empty results, limits, and source traceability.
- [ ] A check proves answer-time knowledge access can occur only through the tool surface.
- [ ] The tool design and trade-offs are recorded for the README.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

A compact, typed retrieval API designed for an LLM agent, capable of supporting all required question intents while hiding raw data and implementation details.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — no production deployment is part of this assignment.

## Open Questions

- none
