---
name: full-review
description: Orchestrate a full branch review by running four skills in sequence — jira-review, code-review, sync-sdd, feature-test-doc — passing shared context (resolved branch, plan, feature name) between them and stopping at each gate for a user decision. Read-only steps report; full-review itself applies code-review's fixes and loops until clean. Use when the user wants an end-to-end review-and-finish pass on the current branch (typical phrasing — "full review", "run the full review", "review and finish the branch", "ריצה מלאה", "בדיקה מלאה").
---

# full-review

## Purpose
Run the project's four review skills back-to-back on the current branch as one gated pipeline: [`jira-review`](../jira-review/SKILL.md:1) → [`code-review`](../code-review/SKILL.md:1) → [`sync-sdd`](../sync-sdd/SKILL.md:1) → [`feature-test-doc`](../feature-test-doc/SKILL.md:1). Resolve the branch and its plan once and pass that context down. The read-only steps report; full-review applies code-review's reported fixes itself and loops until clean. Every gate (task not done, SDD decision, ambiguous feature) stops for one focused question. This skill only orchestrates.

## Required Input
- None up front. Context is resolved in Step 0.
- **Current branch** — resolved in Step 0; it contains `PDA-<number>`.
- **Plan** — [`project/plans/<branch-name>.md`](../../../project/plans/), written by [`create-plan`](../create-plan/SKILL.md:1). If missing → Step 0 stops.

## Procedure

### Step 0 — Resolve shared context
- Get the current branch: `git rev-parse --abbrev-ref HEAD`. Confirm it contains `PDA-<number>`; if not → ask which branch to review, then continue.
- Resolve [`project/plans/<branch-name>.md`](../../../project/plans/), sanitizing `/` → `-` the same way `create-plan` does. Read it directly (existence check is not approval-gated).
- If no matching plan exists → STOP and report: no plan for this branch, nothing to orchestrate against.
- Hold the resolved branch, plan content, and derived feature-name candidate as the shared context passed to every step below.

### Step 1 — jira-review (gate: task done?)
- Run [`jira-review`](../jira-review/SKILL.md:1) against the resolved branch and plan.
- If its verdict is `NOT DONE` → STOP, report exactly what is missing, and wait. Continue only when the verdict is `DONE` or the user explicitly approves continuing.

### Step 2 — code-review + fix loop
- Run [`code-review`](../code-review/SKILL.md:1) (read-only) to get the violation list. Do NOT alter its read-only behavior — full-review is the only actor that edits.
- Apply fixes directly to the reported violations in `services/`/`repositories/` code.
- Re-run `code-review` and loop fix → re-review until it reports clean, or until a max of **5 rounds**. If still not clean at the cap → STOP and report the remaining violations.

### Step 3 — sync-sdd (gate: SDD decision)
- Run [`sync-sdd`](../sync-sdd/SKILL.md:1) to align the code with the chosen SDD.
- If it stops mid-run (SDD missing, ambiguous, or a conflict needing a user decision) → surface its question verbatim and STOP for the answer. `project/docs/SDD/` may be empty, so this step commonly stops asking where the SDD is — that is expected, not an error.

### Step 4 — feature-test-doc (gate: ambiguous feature)
- Derive the FEATURE name from the branch name and run [`feature-test-doc`](../feature-test-doc/SKILL.md:1) to create/update the TDS.
- If the branch name does not resolve to exactly one feature with certainty → STOP and ask the user for the feature name, then continue.

### Step 5 — Aggregated report (terminal + conversation only)
Emit one report — no file:

```
=== full-review: <branch> ===
1. jira-review:      DONE | NOT DONE (stopped)
2. code-review:      <V> violation(s) fixed over <R> round(s) | clean | stopped at cap
3. sync-sdd:         aligned | stopped (<reason>)
4. feature-test-doc: <TDS path> (created | updated) | stopped
```

## Hard Prohibitions
- Do NOT write any report file — the aggregated report goes to the terminal and the conversation only. (Sub-skills that legitimately write files, e.g. `feature-test-doc`'s TDS and `sync-sdd`'s code edits, still do so.)
- Do NOT weaken, bypass, or re-implement any sub-skill's behavior — invoke each as-is; full-review is the only actor that edits code in Step 2.
- Do NOT skip a gate — each stop waits for the user; silence is not approval.
- Do NOT continue past `NOT DONE` in Step 1 without explicit user approval.
- Do NOT loop Step 2 past the max-rounds cap — stop and report instead.
- Do NOT guess the feature name in Step 4 when the branch does not resolve to exactly one feature — ask.
- Do NOT reorder the four steps or add steps beyond this pipeline.

## When to Ask Instead of Acting
- The current branch does not contain `PDA-<number>` → ask which branch to review.
- No plan file exists for the branch (Step 0) → stop and report; do not fabricate the task.
- `jira-review` returns `NOT DONE` → report what is missing and ask whether to continue.
- Step 2 hits the max-rounds cap still dirty → report the remaining violations and ask how to proceed.
- `sync-sdd` raises an SDD-missing/ambiguous/conflict question → surface it and ask.
- The branch name does not resolve to exactly one feature (Step 4) → ask for the feature name.

Ask one focused question, then stop.
