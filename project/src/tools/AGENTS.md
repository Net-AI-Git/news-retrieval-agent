# tools/ — Agent Tool Guide

## Purpose
Typed, LLM-callable adapters that expose approved business capabilities to agents. Tools translate validated model arguments into service calls and return bounded structured results.

## Contains
- Related tools grouped by domain in `<domain_name>_tools.py`.
- Tool input and output models in [`../schemas/`](../schemas/) when Pydantic contracts are required.

## Coding Rules
- Each tool performs one narrow action with a clear name and runtime-consumed description.
- Tool parameters and return values use the annotations required for schema generation and validation.
- Validate model-provided arguments before calling a service.
- Tools call services only. External clients and persistence remain in [`../repositories/`](../repositories/).
- Return only the data the agent needs. Bound large results by count or size.
- Read-only behavior is the default. Mutating or irreversible tools declare an approval requirement and must be resumable through orchestration.
- Mutating operations are idempotent where possible and carry `task_data` and `flow_id` through the service boundary.
- Timeouts and failures return the documented tool error contract without exposing secrets or stack traces to the model.

## Forbidden
- No prompts, agent definitions, routing, or delegation.
- No direct repository, database, HTTP, Redis, CRM, OpenAI, or filesystem access.
- No generic execute-anything tool.
- No hidden side effects or mutation without the declared approval policy.
- No unbounded output or raw external-system response dumps.

## See Also
- [`../agents/AGENTS.md`](../agents/AGENTS.md) — tool assignment and agent boundaries.
- [`../orchestration/AGENTS.md`](../orchestration/AGENTS.md) — approvals, budgets, and resumable execution.
- [`../services/AGENTS.md`](../services/AGENTS.md) — business capabilities called by tools.
- [`../schemas/AGENTS.md`](../schemas/AGENTS.md) — typed tool contracts.
