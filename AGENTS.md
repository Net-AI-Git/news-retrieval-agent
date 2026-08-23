# AGENTS.md — Project Memory (Codex)

> Auto-loaded by Codex at session start. This is a **pointer index only** — the canonical, binding ruleset lives under [`.Codex/rules/`](.Codex/rules/) and is the single source of truth. Do NOT duplicate or paraphrase those rules here.

## Read Before Writing Any Code (binding, in order)

1. [`.Codex/rules/00-overview.md`](.Codex/rules/00-overview.md) — ruleset map + enforcement order.
2. [`.Codex/rules/01-teach-lesson.md`](.Codex/rules/01-teach-lesson.md) — Phase 0: what to read before each task type.
3. [`.Codex/rules/02-code-layout.md`](.Codex/rules/02-code-layout.md) — Phase 1: file structure, naming, layer placement.
4. [`.Codex/rules/03-code-quality.md`](.Codex/rules/03-code-quality.md) — Phase 2: function size, formatting, minimal code.
5. [`.Codex/rules/04-error-and-logging.md`](.Codex/rules/04-error-and-logging.md) — Phase 3: single try/except, OpenTelemetry logging.

Reference implementation: [`.Codex/rules/reference/gpt_feature_name_repository.py`](.Codex/rules/reference/gpt_feature_name_repository.py) — canonical GPT repository shape.

## Skills (auto-invoked)

Skill definitions live in [`.agents/skills/`](.agents/skills/). Each reads its rules fresh from [`.Codex/rules/`](.Codex/rules/):
- `create-skill` / `update-skill` — manage skills under `.agents/skills/`.
- `create-rule` / `update-rule` — manage rules under `.Codex/rules/`.
- `create-command` / `update-command` — redirect legacy command requests to repository skills.
- `code-review` — validate changed files against every rule (read-only).
- `sync-sdd` — reconcile code changes with a chosen SDD.
- `create-opensearch-tech-dashboard` — build an OpenSearch technical dashboard from a service's emitted `OpenSearchRepository.log_event` events.

## Directory-Scoped Standards

Each subdirectory under [`project/src/`](project/src/) has a nested `AGENTS.md` that is binding inside that directory. Codex auto-loads a subdirectory's `AGENTS.md` when it reads files in that directory. Runtime agent boundaries live in `orchestration/`, `agents/`, `tools/`, and `prompts/`; external-system rules live in `repositories/`. Start at [`project/src/AGENTS.md`](project/src/AGENTS.md).

## Communication & Behavior

- Default to the shortest correct answer; show the diff, don't narrate it.
- Skip preamble, filler, and request recaps; use bullets for three or more items.
- Work peer-to-peer as a senior AI/backend engineer; reliability and clarity beat cleverness.
- Read the relevant code/rules before proposing changes — never edit blind.
- For multi-file changes, list the intended files before editing; stop before touching files outside the requested scope.
- Never invent APIs, names, or rule clauses; inspect the source or state the uncertainty.
- Match the language the user writes in (Hebrew → Hebrew); code and identifiers stay English.
- When a request conflicts with a rule → state the conflict in one sentence and stop; the rule wins.
- Report verification precisely: distinguish verified results from untested changes and name the check that would confirm them.

## Enforcement

On any conflict between this file and [`.Codex/rules/`](.Codex/rules/), the canonical ruleset wins. This file never overrides it.
