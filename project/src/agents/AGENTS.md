# agents/ — Agent Guide

## Purpose
Runtime definitions for specialized AI agents. Each agent declares one bounded responsibility, its external prompt, its allowed tools or delegated agents, and its structured output contract.

## Contains
- One file per agent: `<agent_name>_agent.py`.
- Shared agent guardrails in `guardrails.py` only when used by multiple agents.
- Agent-specific prompts in [`../prompts/`](../prompts/), never in Python code.
- Shared context and result contracts in [`../schemas/`](../schemas/).

## Coding Rules
- One agent owns one clear capability. Split agents by responsibility, context, or tool access — never by arbitrary workflow step number.
- The filename and agent name are descriptive and stable. The production prompt filename matches the consuming module stem.
- Each agent receives an explicit minimal allowlist of tools and delegated agents. No global all-tools registry.
- Agents call assigned tools or delegated agents only. They never import services or repositories.
- Instructions are loaded from [`../prompts/`](../prompts/). No authored prompt text, prompt constants, or embedded examples in code.
- Pass only the context required for the delegated task. Do not forward full history or state by default.
- Use structured outputs defined in [`../schemas/`](../schemas/) when downstream code consumes the result.
- Model settings come from runtime configuration; secrets come from environment-backed settings.
- Lifecycle hooks and guardrails may use the type annotations required by the agent runtime.

## Forbidden
- No business logic, SQL, external clients, filesystem access, or direct network calls.
- No inline prompts. Experimental prompt copies are allowed only inside a named scenario under [`../../tests/`](../../tests/).
- No unrestricted tool access.
- No mutable module-level conversation state.
- No routing, retries, checkpoints, budgets, or approval workflows — those belong in [`../orchestration/`](../orchestration/).

## See Also
- [`../orchestration/AGENTS.md`](../orchestration/AGENTS.md) — system-level coordination.
- [`../tools/AGENTS.md`](../tools/AGENTS.md) — LLM-callable capabilities.
- [`../prompts/AGENTS.md`](../prompts/AGENTS.md) — prompt source of truth.
- [`../schemas/AGENTS.md`](../schemas/AGENTS.md) — agent context and output contracts.
