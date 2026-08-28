# Phase 0 — Teach Lesson (Read Before Writing ANY Code)

> MANDATORY: This file governs every feature, agent, tool, orchestration flow, prompt, repository, service, external call, test, and experiment. It is a **pointer index** — it does not restate rules, only points to where each rule lives. The ruleset stays resident for the whole session; use Section 2 to look up the files that govern the task type at hand rather than re-reading everything per task.
> Next phases: [`02-code-layout.md`](02-code-layout.md) → [`03-code-quality.md`](03-code-quality.md) → [`04-error-and-logging.md`](04-error-and-logging.md).

## SECTION 1: ARCHITECTURE (one-line map)

```
routes/ → orchestration/ → agents/ → tools/ → services/ → repositories/ → external
   └────────────────────────────────→ services/ → repositories/ → external

schemas/ define contracts; prompts/ hold production LLM instructions; tests/ hold prompt experiments.
```

`task_data` + `flow_id` flow through every layer. Constants live in [`project/src/conts.py`](../../project/src/conts.py:1). FastAPI deps live in [`project/src/dependencies.py`](../../project/src/dependencies.py:1).

## SECTION 2: WHAT TO READ BEFORE EACH TASK
For every task type below, read the listed files **in order** before writing code.

- **New non-agent feature** → [`02-code-layout.md`](02-code-layout.md) Sections 1, 4, 5 → [`services/AGENTS.md`](../../project/src/services/AGENTS.md:1) → [`04-error-and-logging.md`](04-error-and-logging.md).
- **New agentic feature** → [`02-code-layout.md`](02-code-layout.md) Sections 1, 3, 4 → [`orchestration/AGENTS.md`](../../project/src/orchestration/AGENTS.md:1) → [`agents/AGENTS.md`](../../project/src/agents/AGENTS.md:1) → [`tools/AGENTS.md`](../../project/src/tools/AGENTS.md:1) → [`prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md:1).
- **New agent** → [`agents/AGENTS.md`](../../project/src/agents/AGENTS.md:1) → [`prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md:1).
- **New agent tool** → [`tools/AGENTS.md`](../../project/src/tools/AGENTS.md:1) → [`services/AGENTS.md`](../../project/src/services/AGENTS.md:1).
- **New orchestration flow** → [`orchestration/AGENTS.md`](../../project/src/orchestration/AGENTS.md:1) → [`04-error-and-logging.md`](04-error-and-logging.md).
- **New or modified prompt** → [`prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md:1) → consuming agent or GPT repository.
- **New prompt experiment** → [`tests/AGENTS.md`](../../project/tests/AGENTS.md:1) → [`prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md:1).
- **New repository (or new repo method)** → [`02-code-layout.md`](02-code-layout.md) Section 1 → [`repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md:1) → [`04-error-and-logging.md`](04-error-and-logging.md).
- **New service** → [`02-code-layout.md`](02-code-layout.md) Sections 4, 5 → [`services/AGENTS.md`](../../project/src/services/AGENTS.md:1) → [`04-error-and-logging.md`](04-error-and-logging.md).
- **DB connection / new Oracle method** → [`repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md:1) → [`02-code-layout.md`](02-code-layout.md) Section 3 (SQL placement).
- **Local structured log** → [`04-error-and-logging.md`](04-error-and-logging.md) → [`local_logging_repository.py`](../../project/src/repositories/local_logging_repository.py:1).
- **Local log audit or dashboard** → [`local_logging_audit_client.py`](../../project/local_logging_audit/local_logging_audit_client.py:1) (`local_logs` SQL view) → [`build_dashboard.py`](../../project/local_logging_dashboard/build_dashboard.py:1) → [`04-error-and-logging.md`](04-error-and-logging.md).
- **Redis usage** → [`redis_repository.py`](../../project/src/repositories/redis_repository.py:1) → [`02-code-layout.md`](02-code-layout.md) Section 3 (constants placement).
- **GPT / LLM repository** → [`repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md:1) → [`reference/gpt_feature_name_repository.py`](reference/gpt_feature_name_repository.py:1).
- **CRM call** → [`repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md:1).
- **Pydantic schema** → [`schemas/AGENTS.md`](../../project/src/schemas/AGENTS.md:1).
- **FastAPI route** → [`routes/AGENTS.md`](../../project/src/routes/AGENTS.md:1).

## SECTION 3: HARD RULE
- Never write code without completing the read list above for the matching task type.
- If a rule file and the existing code disagree → STOP, surface the conflict, do not pick a side.
- If the task does not match any row in Section 2 → ask, do not guess.
