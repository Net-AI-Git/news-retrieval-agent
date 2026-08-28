# Phase 1 — Code Layout

> Phase 0 → [`01-teach-lesson.md`](01-teach-lesson.md) | Next → [`03-code-quality.md`](03-code-quality.md) → [`04-error-and-logging.md`](04-error-and-logging.md)
> Repository specifics → [`project/src/repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md) | Prompt specifics → [`project/src/prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md)
> **Scope:** *where* code lives — files, directories, layers, placement, layer contracts. Per-function quality (size, formatting, variables, minimalism, data safety) lives in [`03-code-quality.md`](03-code-quality.md).

## SECTION 1: FILE & DIRECTORY STRUCTURE — FLAT, NOT NESTED

> Why flat: a feature's blast radius must be readable from the file tree alone. One predictable path per artifact means a reviewer finds any feature without searching, and deleting a feature touches a known, finite set of files.

- Services: `services/<feature_name>_service.py` — one file per feature, directly in `services/`.
- Orchestration: `orchestration/<flow_name>_workflow.py` — one file per multi-agent flow.
- Agents: `agents/<agent_name>_agent.py` — one file per agent.
- Tools: `tools/<domain_name>_tools.py` — related LLM-callable tools grouped by domain.
- Prompts: `prompts/<consumer_module_name>.md` — one active production prompt per consuming agent or GPT repository.
- GPT repos: `repositories/gpt_<feature_name>_repository.py` — one file per feature.
- Oracle DB: all features share `repositories/oracle_repository.py` (methods added to same class).
- CRM: all features share `repositories/crm_repository.py`.
- Shared infra: `redis_repository.py`, `local_logging_repository.py` in `repositories/`.
- Pydantic schemas: all `BaseModel` classes MUST live under `schemas/`.
- Prompt experiments: `tests/<experiment_name>/` — control, candidates, dataset, runner, and results stay outside runtime.
- Do NOT create subdirectories per feature. Feature files are self-contained — all logic stays in its own file(s).
- New feature scope: touch only the participating layer files, its prompt if LLM-backed, and its orchestration registration.

## SECTION 2: NAMING CONVENTIONS

> Why names must be self-explaining: annotations and runtime metadata appear only where required, so names remain the primary documentation. `feature_10` forces a hunt through Jira to answer a question the name should have answered.

- Classes: `OracleRepository`, `CrmRepository`, `Gpt<FeatureName>Repository`.
- Features named by purpose only — never by number (`feature_10` → `<meaningful_name>`).
- Functions MUST NOT start with `_` and MUST have descriptive, meaningful names that convey their purpose.
- Constants use `UPPER_SNAKE_CASE`, descriptive names.

## SECTION 3: LAYER PLACEMENT — WHERE DOES X LIVE

> Why one home per concern: every dependency, prompt, and runtime responsibility stays swappable and auditable from a predictable path.

- **SQL** → `oracle_repository.py` only. `text(...)` defined inside the function body — never at class or module level. SQL MUST NOT appear in service or GPT files.
- **CRM API** → `crm_repository.py` only. CRM calls MUST NOT appear in service/GPT/Oracle files. Payload body of **1–3 lines** → service calls `CrmRepository.send_to_crm()` directly with the payload inline (no wrapper method — see [`03-code-quality.md`](03-code-quality.md) Section 5). Payload body of **4+ lines** → dedicated method in `crm_repository.py`.
- **Agent definitions** → `agents/` only. Agents use assigned tools or delegated agents and never access services or repositories directly.
- **LLM-callable tools** → `tools/` only. Tools call services and never own external clients.
- **Multi-agent coordination** → `orchestration/` only. Routing, state transitions, budgets, retries, checkpoints, and approvals live here.
- **Prompts** → external files under `prompts/` only. No authored prompt text in Python code. Outline matches the consuming model's vendor shape. Full prompt standards → [`prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md).
- **Pydantic `BaseModel`** → `schemas/` only.
- **Constants** → `conts.py` per microservice. Never inline in functions/classes.

## SECTION 4: ORCHESTRATION CONTRACT

> Why `task_data` + `flow_id` travel whole: every participating layer keeps one correlated execution context, so a `flow_id` reconstructs the full run.

- Agentic routes call one orchestration entry point; non-agent routes may call one service entry point directly.
- Orchestration calls agents or services only. It contains coordination policy, never prompts, tool implementations, business logic, or external access.
- Agents call assigned tools or delegated agents only. Tools call services only. Services call repositories.
- `task_data` and `flow_id` MUST flow through every invoked runtime layer. Each layer extracts only what it needs from `task_data`.

**BAD:** `run_<feature_name>(field_a, field_b, flow_id)`
**GOOD:** `run_<feature_name>(task_data, flow_id)`

## SECTION 5: SERVICE ENTRY-POINT CONTRACT

> Why the entry-point stays logic-free and last: reading the bottom of the file gives the whole feature flow in one screen, and every step above it can be read or changed in isolation.

- Entry-point: `run_<feature_name>(task_data, flow_id)` — MUST be the LAST function in the file.
- Contains zero inline logic — only calls sub-functions sequentially (readable "table of contents").
- All helpers defined above it. Max 2 levels deep. No deep chains `A→B→C→D` — flatten. Each sub-function does one complete, self-contained piece of work.
- `run_` prefix reserved for the single entry-point only.
