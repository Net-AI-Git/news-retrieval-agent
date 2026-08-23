---
name: code-review
description: Review every file changed on the current branch against every rule under `.Codex/rules` and the branch implementation plan. Read-only and never fixes. Use after coding, before committing, or for branch and pre-commit rule reviews.
---

# code-review

## Purpose

Drive a slow, explicit **file-by-file loop** that validates **every** file changed on the current git branch — measured as the branch diff against its merge-base with the base branch, not the working-tree status — against **every** rule under [`.Codex/rules/`](../../../.Codex/rules/), read fresh each run. Interlock with the plan produced by `/goal` (the [`create-plan`](../create-plan/SKILL.md) skill): read [`project/plans/<branch-name>.md`](../../../project/plans/), confirm in-scope files, verify the branch changes satisfy the plan's Success Criteria, and flag scope drift. Read-only — reports violations and a plan verdict, never fixes. Use after a coding session, before committing.

Partial coverage is a failure, not a shortcut: no file is skipped, no rule is skipped, and the loop advances to the next file only after the current file is fully verified against every loaded rule.

## Required Input

None up front. The skill discovers scope from the branch diff (Step 1) and the `/goal` plan (Step 2).

- **Base branch** — the branch this one diverged from. Auto-detect in Step 1; if it cannot be resolved → ask the user, then continue. Do NOT guess.
- **`/goal` plan** — [`project/plans/<branch-name>.md`](../../../project/plans/), written by `create-plan`. Located in Step 2. If missing → follow Step 2's branch.
- **Explicit file list** (optional) — if the user supplies one, review those files instead of the diff-derived list, but still run the full per-rule loop against every listed file. The plan interlock (Step 2, Step 5, scope-drift) is then skipped unless the user also names the branch to check against.

## Procedure

Run the steps in order; each is a gate — complete Step N fully before Step N+1. Steps 4–5 are the loop: process ONE file per iteration, update the ledger, verify against every rule, and only then advance. Do not batch files. Do not exit the loop until the ledger's `remaining` list is empty.

### Step 1 — Discover the branch diff
- Determine the current branch: `git rev-parse --abbrev-ref HEAD` (e.g. `FEATURE/8582`).
- Determine the base branch. If the user named one, use it; else auto-detect — first that resolves: `origin/HEAD`, `main`, `master`, `develop`. If none resolve → ask the user for the base branch, then continue.
- Find the divergence point: `git merge-base HEAD <base-branch>`.
- List every file changed since divergence: `git diff --name-status <merge-base>...HEAD`.
- Parse every listed path. For renames (`R`), use the post-rename path. For deletes (`D`), record as deleted and skip (nothing to read).
- Filter to `*.py` files under `project/src/`. Skip everything else (tests, configs, docs, `AGENTS.md` files) unless the user explicitly requested them.
- This branch diff REPLACES any prior `git status`-only scope. The branch diff is the scope.
- If the filtered set is empty → report "Nothing to review on this branch" and stop. Do NOT touch any rule.

### Step 2 — Read the `/goal` plan (interlock)
- Resolve the plan path: [`project/plans/<branch-name>.md`](../../../project/plans/), sanitizing the branch name the same way `create-plan` does — replace `/` with `-` (e.g. `FEATURE/8582` → `FEATURE-8582.md`).
- Read the plan file directly.
- If it exists → extract verbatim: **Goal**, **Success Criteria** (each bullet), **Scope → In**, **Scope → Out**, **Final Deliverable**. These drive Step 4's scope-drift check and Step 5's verdict. Do NOT invent criteria the plan does not state.
- If it is missing → ask the user once: **run `/goal` (create-plan) now, or continue rules-only?** Do NOT default. Wait for the choice.
  - `run /goal` → invoke the [`create-plan`](../create-plan/SKILL.md) skill; resume this skill at Step 2 after the plan exists.
  - `rules-only` → set the run to rules-only (Success-Criteria verdict = `NO PLAN`); skip the plan-scope and Success-Criteria checks (Step 4 interlock, Step 5); still run the full per-rule loop against every file.

### Step 3 — Load the FULL ruleset, fresh, this run
- Enumerate [`.Codex/rules/`](../../../.Codex/rules/) and read **every** `.md` file in numerical order.
- Auto-discover: if a rule file exists that this skill has never seen, load it anyway. Do NOT assume there are exactly six rule files — enumerate the directory every run.
- Read them FRESH this run. Do NOT hardcode, cache, or summarize rules from memory.
- Do NOT skip any rule. Do NOT prioritize one rule over another. Every rule, and every section within it, applies to every file in scope.
- For files under `project/src/repositories/`, also load the binding [`project/src/repositories/AGENTS.md`](../../../project/src/repositories/AGENTS.md) and, for `gpt_<feature>_repository.py` files, the canonical [`reference/gpt_feature_name_repository.py`](../../../.Codex/rules/reference/gpt_feature_name_repository.py) — a repository file that passes the ruleset can still violate its directory standard.
- Output the loaded set: list each rule file loaded and confirm the count against the directory listing. If they disagree → stop and re-enumerate; a missed rule file is a failure.

### Step 4 — The loop: one file per iteration, verify before advancing
Initialize the ledger and print it before the first file:

```
=== code-review ledger — branch <branch>, base <base>, 0/<N> files reviewed ===
Rules loaded: <loaded rule files> (fresh this run)
Plan: <project/plans/<branch>.md | NO PLAN>
Queue (alphabetical): 1. <path>  2. <path>  ... N. <path>
Done: (none)
Remaining: <all N paths>
```

`N` = files in scope. The queue is sorted alphabetically by path and is fixed — files are neither added nor dropped once the loop begins.

For a large `N`, the per-file rule-check (substep 3) MAY be fanned out with the `Agent` tool: dispatch one read-only subagent per file, each given the FULL loaded ruleset plus `AGENTS.md`/reference where applicable and instructed to return the same structured violation list `(file_path, line_number, rule_file, rule_section, summary)`. This is an efficiency mechanism only — it changes nothing about coverage: every file is still checked against every rule, none skipped, none prioritized. The main loop still owns the ledger, consumes results in queue order, and applies the verify-before-advance gate (substep 5) to every file before marking it done. If any subagent's coverage is incomplete, re-check that file before advancing. Take the file at the front of `remaining` and do ALL of the following before touching the next file:

1. **Announce**: `--- Reviewing file <index>/<N>: <path> ---`.
2. **Read** the full file content.
3. **Check against every rule.** Walk the file against every rule across ALL loaded rule files, in order — this concrete checklist (rule sections from [`.Codex/rules/`](../../../.Codex/rules/)):
   - `00-overview.md` — enforcement order; stricter/more-specific rule wins; directory-scoped `AGENTS.md` binding for repository files.
   - `01-teach-lesson.md` — architecture/layer flow; correct layer for the change; surface conflicts, never pick a side.
   - `02-code-layout.md` — flat file/dir structure; naming (no leading underscore, `UPPER_SNAKE_CASE` constants); layer placement (SQL in `oracle_repository`, CRM in `crm_repository`, prompts inline in GPT repos, schemas in `schemas/`, constants in `conts.py`); orchestrator contract; `run_<feature>` entry-point contract (last function, no inline logic, ≤2 levels deep).
   - `03-code-quality.md` — function ≤25 lines; single-line signatures/statements; variable hygiene (descriptive names, no single-letter, no `current_step`); control flow (no single-line loops/comprehensions-as-statements, assume valid inputs); minimal code (no docstrings/comments/type-hints except Pydantic, no trivial wrappers); data safety (no DELETE+INSERT, use MERGE/UPSERT).
   - `04-error-and-logging.md` — single try/except per function (STARTING before, ERROR in except with `repr(err)`, FINISHED after); helpers have NO try/except; no silent failures; service entry returns safe defaults, never re-raises; only STARTING/FINISHED/ERROR statuses; INFO/ERROR level policy; single-line `OpenSearchRepository.log_event`, no `process=`, no manual timestamps.
   - Do NOT stop at the first hit; a file may have zero, one, or many violations. Do NOT skip a rule because it "seems unrelated". Record each violation as `(file_path, line_number, rule_file, rule_section, one-line summary)`.
   - If an approved waiver document under [`project/docs/spec/`](../../../project/docs/spec/) explicitly waives a named standard for this file, do NOT record that standard as a violation for the scoped file(s).
4. **Scope-drift check** (skip if `NO PLAN`): is this file inside the plan's **Scope → In**? If it appears under **Scope → Out**, or is not covered by the plan at all → record a `SCOPE-DRIFT` note (file path + which plan boundary it crosses). This is reported, not a rule violation.
5. **Verify-before-advance gate**: confirm you checked this file against every loaded rule plus `AGENTS.md`/reference where applicable. If any loaded rule was not applied to this file → do NOT advance; re-run substep 3 for the missed rule(s).
6. **Update the ledger** and print it:

```
=== code-review ledger — <index>/<N> files reviewed ===
Done: <path> (<v> violations[, SCOPE-DRIFT])  | ...prior entries...
Remaining: <remaining paths, or "(none)">
```

7. **Termination gate**: if `remaining` is empty → go to Step 5. Otherwise loop to the next file. Do NOT stop, summarize, or hand back control while `remaining` is non-empty.

### Step 5 — Verify the branch against the plan's Success Criteria (interlock)
Skip this step if `NO PLAN`.
- For **each** Success Criterion in the plan, decide against the reviewed diff: `MET` / `NOT MET` / `CANNOT VERIFY FROM DIFF` — one-line reason each, citing the file(s) that satisfy or fail it. Do NOT mark a criterion `MET` without a concrete file citation.
- Aggregate the `SCOPE-DRIFT` notes from Step 4 into one scope-drift list. Also list any **In-scope** area the plan named that the branch never changed.
- This is a verdict, not a fix: never edit code to make a criterion pass.

### Step 6 — Report
Output exactly this structure, nothing else:

```
=== code-review: <N> file(s) changed, <V> violation(s) ===

[file 1] project/src/services/<feature>_service.py
  - <rule_file> §<section>: <one-line violation> (line <n>)
  - <rule_file> §<section>: <one-line violation> (line <n>)

[file 2] project/src/repositories/gpt_<feature>_repository.py
  - <rule_file> §<section>: <one-line violation> (line <n>)

=== files clean: <list of file paths with zero violations> ===

=== /goal plan: project/plans/<branch-name>.md ===
Success Criteria:
  - <criterion>: MET (project/src/...) | NOT MET | CANNOT VERIFY FROM DIFF (<reason>)
Scope drift:
  - <file>: <plan boundary crossed>   (or "none")
```

- If `V == 0`: print `=== code-review: <N> file(s) changed, 0 violations — PASS ===`, then still emit the `=== /goal plan: ... ===` block, then stop.
- If not rules-only: always emit the `=== /goal plan: ... ===` block (even when every criterion is `MET`).
- If rules-only (`NO PLAN`): replace the `=== /goal plan: ... ===` block with `=== /goal plan: NO PLAN (rules-only review) ===`.

### Step 7 — Stop
- Do NOT auto-fix.
- Do NOT suggest fixes unless the user asks.
- Do NOT touch any file.
- Do NOT re-loop or add unsolicited follow-up work. The user decides what to do with the report.

## Hard Prohibitions

- Do NOT scope the review to `git status --porcelain` / the working tree — scope is the **branch diff** against the merge-base with the base branch (Step 1), or the explicit list the user gave. This replaces the old git-status-only scope.
- Do NOT review files the branch did not change. Do NOT review files outside `project/src/` unless explicitly requested.
- Do NOT skip a file, batch multiple files into one iteration, or exit after a "representative sample". Process ALL `N` files, one per iteration, counting explicitly.
- Do NOT advance to the next file until the current file has been checked against every loaded rule (Step 4 gate).
- Do NOT stop early — the loop ends only when the ledger's `remaining` list is empty.
- Do NOT skip a rule because it "seems unrelated", and do NOT prioritize one rule over another — every rule is checked against every file.
- Do NOT hardcode, cache, or assume the ruleset — enumerate [`.Codex/rules/`](../../../.Codex/rules/) and read every file fresh every run.
- Do NOT report coverage you did not perform — no clearing the Step 4 gate unless every loaded rule was applied.
- Do NOT modify any file, including files under review, the plan, or any rule; do NOT invoke `create-plan` without the user choosing that branch in Step 2.
- Do NOT invent Success Criteria or Scope the plan does not state; do NOT mark a criterion `MET` without a file citation.
- Do NOT inflate the report with "looks good!" commentary. Pure violation list, plan verdict, and PASS/clean lines only.

## When to Ask Instead of Acting

- The `/goal` plan file is missing → ask once: run `/goal` (create-plan) now, or continue rules-only? Then stop for the answer.
- The base branch cannot be auto-detected (no `origin/HEAD`, `main`, `master`, `develop`) → ask which branch to diff against, then stop.
- A `git` command (branch, merge-base, diff) is rejected → ask whether the user wants to supply the file list and base branch manually.
- The repo is not a git repo (no `.git/`) → ask the user for the file list.
- A rule's intent is ambiguous when applied to a specific construct → ask how to interpret it, then continue the same file (do not advance past it).
- A Success Criterion is too vague to judge `MET`/`NOT MET` → ask how to verify it, then continue.

Ask one focused question, then stop.

## Output Format Contract

- Violations grouped by file (file path = relative from workspace root).
- Each violation: one line, format `<rule_file> §<section>: <summary> (line <n>)`.
- Sort violations within a file by line number ascending.
- Sort files alphabetically by path.
- The ledger lines (Step 4) are progress output emitted during the run; the report block (Step 6) is the single terminal artifact.
- The `=== /goal plan: ... ===` block lists every Success Criterion with exactly one verdict (`MET` / `NOT MET` / `CANNOT VERIFY FROM DIFF`) plus the scope-drift list; replace the whole block with the `NO PLAN` line only in rules-only mode.
- No emojis, no decorations, no severity ratings. Either it violates a rule or it doesn't.
