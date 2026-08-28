---
name: jira-review
description: Verify that the current branch fully implements its PDA task and plan without scope drift or breaking documented logic. Read-only and never fixes. Use for Jira, PDA, or task-completion reviews; use `code-review` for rule compliance.
---

# jira-review

## Purpose
Confirm the PDA task the branch was opened for is actually complete and safe. Read the branch's plan, compare it to what the branch changed, and answer three questions: is every Success Criterion implemented in code, did the changes stay inside the declared Scope, and did any change break logic documented anywhere under [`project/docs/`](../../../project/docs/). Read-only — it produces a spoken/terminal verdict only. Rule compliance (`.Codex/rules/`) is out of scope; that is [`code-review`](../code-review/SKILL.md:1).

## Required Input
- None up front. Scope is discovered from the branch and its plan.
- **Current branch** — resolved in Step 1; it contains `PDA-<number>`.
- **Plan** — [`project/plans/<branch-name>.md`](../../../project/plans/), written by [`create-plan`](../create-plan/SKILL.md:1). If missing → Step 2 stops the skill.

## Procedure

### Step 1 — Resolve the branch and diff
- Get the current branch: `git rev-parse --abbrev-ref HEAD`. Confirm it contains `PDA-<number>`; if it does not → ask the user which branch to review, then continue.
- Find divergence from `develop`: `git merge-base HEAD develop`. If `develop` does not resolve → ask the user for the base branch, then continue.
- List every changed file since divergence: `git diff --name-status <merge-base>...HEAD`. For renames use the post-rename path; for deletes record as deleted.
- This branch diff is the review scope — not `git status`, not the working tree.
- If the diff is empty → report "Nothing changed on this branch" and stop.

### Step 2 — Locate and read the plan
- Resolve [`project/plans/<branch-name>.md`](../../../project/plans/), sanitizing the branch name the same way `create-plan` does — replace `/` with `-` (e.g. `feature/PDA-1234` → `feature-PDA-1234.md`). Read it directly.
- If no matching plan file exists → STOP and report: no plan found for this branch, nothing to review against. Do not guess the task from the diff.
- Extract verbatim: **Success Criteria** (each bullet), **Scope → In**, **Scope → Out**. Do NOT invent criteria the plan does not state.

### Step 3 — Read the full diff and the documented logic
- Read the actual content of every changed file (or the relevant hunks for large files) so criteria are judged against real code, not filenames.
- Enumerate and read every document under [`project/docs/`](../../../project/docs/): the `spec/` files, every SDD under `SDD/`, and top-level `*.md` (e.g. `opensearch.md`). These define the logic that must still hold. Read fresh each run — do not assume a fixed set.
- For a large diff or many docs, fan out the read-only inspection with the `Agent` tool (`Explore` subagent) — one subagent per Success Criterion or per doc — each returning whether the current code satisfies it. Synthesize the results yourself; this changes nothing about coverage.

### Step 4 — Verify the three checks
- **Criteria:** for each Success Criterion decide `MET` / `NOT MET` / `CANNOT VERIFY FROM DIFF`, one-line reason each, citing the file(s). Never mark `MET` without a concrete file citation.
- **Scope:** for each changed file decide if it is inside **Scope → In**. A file under **Scope → Out**, or not covered by the plan, is a `SCOPE-DRIFT` note (file + boundary crossed).
- **Documented logic:** for each doc under `project/docs/`, decide whether the diff breaks a behavior it documents or leaves a documented task no longer correctly fulfilled. Record each as `DOC-BREAK` (doc path + the passage + how the change breaks it). If a change makes code diverge from a doc without breaking it, still flag it as `DOC-DRIFT`.

### Step 5 — Report (terminal + conversation only)
Output exactly this structure and nothing else — no `.md` file, no other file:

```
=== jira-review: <branch> (PDA task) vs develop — <N> file(s) changed ===
Plan: project/plans/<branch-name>.md

Success Criteria:
  - <criterion>: MET (project/src/...) | NOT MET (<reason>) | CANNOT VERIFY FROM DIFF (<reason>)

Scope drift:
  - <file>: <plan boundary crossed>          (or "none")

Documented logic (project/docs/):
  - DOC-BREAK  <doc path>: <what breaks>       (or "none")
  - DOC-DRIFT  <doc path>: <what diverged>      (or "none")

Verdict: DONE | NOT DONE (<one-line reason>)
```

- `DONE` only when every criterion is `MET`, scope drift is `none`, and there is no `DOC-BREAK`.

### Step 6 — Stop
- Do NOT fix anything, do NOT suggest fixes unless the user asks, do NOT re-loop.

## Hard Prohibitions
- Do NOT write any file — no report `.md`, no edits to code, plan, docs, or rules. Output goes to the terminal and the conversation only.
- Do NOT fix, refactor, or "improve" code — read-only verdict only.
- Do NOT re-run the `.Codex/rules/` compliance loop — that is [`code-review`](../code-review/SKILL.md:1); point the user there for rule checks.
- Do NOT scope the review to `git status` / the working tree — scope is the branch diff vs merge-base with `develop`.
- Do NOT invent Success Criteria or Scope the plan does not state; do NOT mark a criterion `MET` without a file citation.
- Do NOT guess the task from the diff when the plan file is missing — stop and report.
- Do NOT inflate the report with commentary — criteria verdicts, drift list, doc findings, and the final verdict only.

## When to Ask Instead of Acting
- The current branch does not contain `PDA-<number>` → ask which branch to review, then stop.
- `develop` does not resolve as the base branch → ask which base branch to diff against, then stop.
- A `git` command is rejected → ask whether to supply the file list and base branch manually.
- A Success Criterion is too vague to judge `MET`/`NOT MET` → ask how to verify it, then continue.
- A documented passage under `project/docs/` is ambiguous about whether the change breaks it → ask, then continue.

Ask one focused question, then stop.
