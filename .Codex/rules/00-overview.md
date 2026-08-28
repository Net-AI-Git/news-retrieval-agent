# Official Project Ruleset — Microservices

> These rules are MANDATORY. Codex reads them through the root `AGENTS.md` before code tasks. They are not reference documents — they are binding standards. All generated and reviewed code MUST comply.

## Rule Files (apply in order)

1. [`01-teach-lesson.md`](01-teach-lesson.md) — Phase 0: pointer index — what to read before building a feature, agent, tool, orchestration flow, prompt, repository, service, or external integration. Consult its Section 2 map to find the files that govern the task type at hand.
2. [`02-code-layout.md`](02-code-layout.md) — Phase 1: file structure, naming conventions, layer placement, orchestrator + service entry-point contracts. Apply when **writing new code, creating files, or implementing a feature**.
3. [`03-code-quality.md`](03-code-quality.md) — Phase 2: function size, formatting, variable hygiene, control flow, minimal code, data safety. Apply **after code is written**.
4. [`04-error-and-logging.md`](04-error-and-logging.md) — Phase 3: single try/except pattern, local structured logging, local agent telemetry, no silent failures. Apply **after code works (hardening)**.

## Directory-Scoped Standards (nested AGENTS.md)

Directory-specific standards live in each runtime layer's `AGENTS.md`. Repository separation rules live in [`project/src/repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md); prompt standards live in [`project/src/prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md).

## Reference Implementation

- [`reference/gpt_feature_name_repository.py`](reference/gpt_feature_name_repository.py) — the canonical GPT repository implementation that all `gpt_<feature_name>_repository.py` files MUST mirror.

## Enforcement

- When generating code: read Phase 0 → follow Phase 1 → review against Phase 2 → harden with Phase 3.
- When touching any code under [`project/src/repositories/`](../../project/src/repositories/), the directory's [`AGENTS.md`](../../project/src/repositories/AGENTS.md) is binding in addition to the rules above.
- When touching agents, tools, orchestration, prompts, or tests, the target directory's `AGENTS.md` is binding in addition to the rules above.
- When any conflict arises, the stricter, more specific rule wins.
- An approved waiver document under [`project/docs/spec/`](../../project/docs/spec/) may explicitly waive a named standard for the file(s) it scopes; that waiver overrides the standard only where stated.
