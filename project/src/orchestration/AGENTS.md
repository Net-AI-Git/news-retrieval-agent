# orchestration/ — Multi-Agent Orchestration Guide

## Purpose
The system-level control plane for multi-agent flows. This layer owns execution order, routing, state transitions, concurrency, budgets, retries, checkpoints, approvals, and final result assembly.

## Contains
- One flat workflow module per use case: `<flow_name>_workflow.py`.
- Workflow state contracts in [`../schemas/`](../schemas/), not inline models.
- Agent definitions in [`../agents/`](../agents/), imported and composed here.

## Coding Rules
- Agentic routes call exactly one orchestration entry point with `task_data` and `flow_id`.
- Use deterministic code for fixed sequencing, validation, budgets, and routing rules; use an agent decision only where model judgment is required.
- Define explicit start, completion, failure, timeout, approval, and resume states.
- Set maximum turns, tool concurrency, timeout, and retry limits for every workflow.
- Parallelize only independent work and join results at a declared synchronization point.
- Persist checkpoints before waits or human approval and resume from the saved state.
- Preserve framework interrupts and cancellation signals; never absorb them in a broad application exception handler.
- Emit one correlated trace for the workflow and standard GenAI spans for agents, model calls, tools, handoffs, and guardrails.
- Orchestration calls agents or services only. Business operations remain in services.

## Forbidden
- No prompt text, tool implementations, domain calculations, SQL, or external clients.
- No direct repository access.
- No unlimited loops, retries, parallelism, or delegated agents.
- No mutable global workflow state.
- No silent fallback from a failed approval, checkpoint, or validation step.

## See Also
- [`../agents/AGENTS.md`](../agents/AGENTS.md) — specialized runtime agents.
- [`../tools/AGENTS.md`](../tools/AGENTS.md) — agent-callable business adapters.
- [`../prompts/AGENTS.md`](../prompts/AGENTS.md) — external instructions.
- [`../schemas/AGENTS.md`](../schemas/AGENTS.md) — workflow state contracts.
- [`../../docs/opensearch.md`](../../docs/opensearch.md) — trace correlation and GenAI observability.
