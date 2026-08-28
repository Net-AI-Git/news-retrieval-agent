# TASK 04 — Agentic Grounded Answering

**Status:** In Progress  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-4-agentic-grounded-answering`

## Goal

Implement a genuinely agentic answering flow in which an LLM chooses retrieval tools, performs follow-up calls when evidence requires multiple hops, evaluates sufficiency, and returns a grounded short answer or an honest refusal.

## Current approach (2026-08-28)

Gate 4 no longer uses one Gather agent that both splits the question and calls `search_facts`. That one-agent design hit a pairing-vs-Q05 wall: the same context either copied a named outlet onto every hop (Q05 Age-on-TechCrunch) or omitted `source` on pairing questions. Prompt-only first-hop peaked at 9/11. k=2 raised some gold ranks and left Q05 failing. Production loop:

1. **Gather** (`gather_agent.py`, no tools, `GatherResult.sub_questions`) — hop inventory only. User JSON `{question, prior_queries, grade_note}`. Copy outlet/date into the string of the claim they belong to. Must not answer or search.
2. **Retrieve** (`retrieve_agent.py`, `search_facts` only, `tool_choice` forced) — one isolated sub-question per invoke; no parent question, no siblings. Fill `source` / ISO dates from **this** string. Must not answer. Catalog resolve is `run_resolve_source`, not this agent.
3. **Tools** — `ToolNode` runs the batched `search_facts` calls. Sequential retrieve invokes stay under OpenRouter rate limits.
4. **Grade** — stop vs rewrite vs missing hop. Continue returns to Gather with `grade_note`.
5. **Answer** — claim or refuse from this-run evidence.

First live first-hop score on the split: 8/11 (`tests/live_gather_first_hop` `metrics_2026-08-28_16-44-21.csv`). Q05 gold complete. Remaining: Q01 rank-1 (retrieval), Q04 packed (Gather), Q07 over-split (Gather).

Follow-up optimization is two tasks, not one prompt: Gather decompose vs retrieve filter-fill. Do not merge them. Details: [`TASK-04-decisions.md`](TASK-04-decisions.md) “Isolated retrieve hop”. Local-GT ladder: [`TASK-06-answers-transcripts-and-evaluation.md`](TASK-06-answers-transcripts-and-evaluation.md) Phase D.

This remains TASK 04 work: the LLM still directs tool arguments; orchestration still owns budgets; `search_corpus` stays unbound.

## Product Requirements

- Gather emits the hop list; retrieve decides `search_facts` arguments (`question`, optional `source`, optional dates) and may produce multiple hops per user question. Follow-up hops go through Grade → Gather again.
- The agent receives knowledge only through `search_facts`. `search_corpus` exists from TASK 03 but is not bound in this loop.
- A single LLM call with pre-baked retrieval does not satisfy this task.
- Final answers are limited to an entity name, `Yes`, `No`, or an explicit insufficient-information refusal.
- Every non-refusal answer cites only evidence actually returned by tools during that run.
- The loop has explicit stopping, tool-call, context, cost, and failure boundaries.

## Research Before Implementation

- Compare tool-calling loop patterns and determine how the chosen model will request, receive, and reason over tool results.
- Define evidence-sufficiency rules for direct, yes/no, temporal, and multi-article questions.
- Determine when the agent should reformulate a query, follow a related entity, request more evidence, stop, or refuse.
- Investigate protections against unsupported synthesis, citation mismatch, repeated calls, and budget exhaustion.
- Select a model and prompting strategy based on tool-use reliability, context needs, cost, and available credentials.

## Implementation Autonomy

The developer chooses the LLM provider, model, agent framework, loop implementation, prompts, budgets, and state representation. This task specifies observable agent behavior only.

## Scope

**In:**

- Developer-selected agent, prompt, loop, state, and test files.
- Multi-step tool selection and evidence accumulation.
- Evidence sufficiency, citation selection, refusal, and stopping behavior.

**Out:**

- Replacing the retrieval representation or tool contracts without a documented need.
- Batch generation of the final `answers.json` and transcripts.
- Binding `search_corpus` in the answering loop.
- Optional bonus features unrelated to required answer quality.

## Success Criteria

- At least one representative multi-hop case shows multiple LLM-directed tool calls before answering.
- Direct cases can stop without unnecessary calls.
- Unsupported cases return an insufficient-information refusal rather than a guess.
- Every returned citation is drawn from evidence observed in the same run and supports the answer.
- The loop terminates predictably under success, insufficient evidence, tool failure, and budget limits.

## Definition of Done

- [ ] The LLM controls hop decomposition (Gather) and `search_facts` arguments (retrieve).
- [ ] The loop supports multiple `search_facts` calls. Corpus is out of this task.
- [ ] Raw corpus and facts are never inserted directly into the answer-time prompt.
- [ ] Evidence-sufficiency and refusal behavior are implemented and tested.
- [ ] Answer and citation claims are validated against retrieved evidence.
- [ ] Call, step, context, and cost limits prevent unbounded loops.
- [ ] Tool failures produce a controlled answer or refusal without fabricated claims.
- [ ] Model and prompting decisions are recorded for the README.
- [ ] The branch is independently reviewable and ready to merge.

## Final Deliverable

A bounded LLM-controlled tool-use loop that can solve direct and multi-hop questions, cite its retrieved support, and refuse when the available evidence does not justify an answer.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — no production deployment is part of this assignment.

## Open Questions

- none
