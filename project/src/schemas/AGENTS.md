# schemas/ — Agent Guide

## Purpose
All Pydantic `BaseModel` declarations. Schemas describe data shapes flowing between layers and across the API boundary — they have no behavior.

## Contains
- A shared API `Request` in [`request.py`](request.py:1) and `Response` in [`response.py`](response.py:1).
- Shared agent context, workflow state, tool input/output, and structured result models in `agent.py` when required.
- Do NOT create a schema file per feature, agent, tool, or workflow.
- `BaseModel` subclasses only.

## Coding Rules (specific to this directory)
- **Type annotations are mandatory here** because Pydantic requires them.
- Field defaults expressed via `Optional[...] = None` or `Field(...)` — keep it minimal.
- Reuse shared API and agent contracts rather than declaring one pair per feature.
- All `BaseModel`s live in [`schemas/`](.). Do **not** add `BaseModel` declarations inside agents, tools, orchestration, repositories, services, or routes.

## Forbidden in this directory
- No business logic — no methods beyond Pydantic validators when strictly necessary.
- No DB session imports, no HTTP clients, no OpenAI imports.
- No constants — those belong in [`../conts.py`](../conts.py:1).
- No inheritance chains deeper than one level beyond `BaseModel`.

## See Also
- [`.Codex/rules/02-code-layout.md`](../../../.Codex/rules/02-code-layout.md:1) Section 1 (all `BaseModel`s live here).
- [`.Codex/rules/03-code-quality.md`](../../../.Codex/rules/03-code-quality.md:1) Section 5 (the type-hint exception).
- [`project/docs/AGENTS.md`](../../docs/AGENTS.md:1) — per-feature SDD layout (no global SDD).
