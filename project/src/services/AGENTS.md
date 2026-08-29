# services/ — Agent Guide

## Purpose
Business capability execution. Each file owns one feature end-to-end. Services coordinate repositories and may be called by routes, orchestration, or agent tools.

## Contains
- One file per feature: `<feature_name>_service.py` (e.g. [`example_feature_service.py`](example_feature_service.py:1)).
- One service entry-point: `run_<feature>(task_data, flow_id)`.
- Sub-functions defined **above** the entry-point — entry-point is always the last function in the file.

## Coding Rules (specific to this directory)
- The entry-point signature is `run_<feature>(task_data, flow_id)` — both arguments flow through every layer below.
- Entry-point body = sequential calls only. Zero inline logic, zero conditionals beyond simple gating.
- Max 2 levels deep (entry-point + direct sub-functions). No `A → B → C → D` chains — flatten.
- Sub-functions have **no** `try/except` — errors bubble to the entry-point's single top-level handler (see [`.Codex/rules/04-error-and-logging.md`](../../../.Codex/rules/04-error-and-logging.md:1) Section 1-2).
- Entry-point returns a safe default on error (`[]`, `""`, `None`) — never re-raises.
- The logging dashboard service may call `observability.logging_dashboard.build_dashboard`.
- Confidence-score filtering for GPT results happens **here**, not in the GPT repository.

## Forbidden in this directory
- No SQL, no `text(...)`, no SQLAlchemy calls — those live in [`../repositories/`](../repositories/) only.
- No `openai` / `AzureOpenAI` client construction — that is a GPT repository's job.
- No HTTP calls to CRM / external APIs — use [`../repositories/`](../repositories/) wrappers.
- No prompt strings — prompts live in [`../prompts/`](../prompts/).
- No agent routing, handoffs, checkpoints, approvals, or workflow state — those live in [`../orchestration/`](../orchestration/).
- No ad hoc `current_step` variables.
- No type hints, no docstrings, no comments.

## See Also
- [`.Codex/rules/02-code-layout.md`](../../../.Codex/rules/02-code-layout.md:1) Sections 4-5.
- [`.Codex/rules/03-code-quality.md`](../../../.Codex/rules/03-code-quality.md:1) Section 1 (function size).
- [`.Codex/rules/04-error-and-logging.md`](../../../.Codex/rules/04-error-and-logging.md:1) — error/log shape for `run_*` functions.
- [`project/docs/AGENTS.md`](../../docs/AGENTS.md:1) — per-feature SDD layout (no global SDD).
- [`../tools/AGENTS.md`](../tools/AGENTS.md) — agent-callable adapters into services.
- [`../orchestration/AGENTS.md`](../orchestration/AGENTS.md) — multi-agent workflow control.
