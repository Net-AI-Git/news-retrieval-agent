---
name: document-spec
description: Authors an approved specification document under the project's discovered docs/spec/ folder that records intentional, approved decisions — both approved deviations from named governing standards and business logic that must be preserved — scoped to specific files, so code review honors them instead of flagging or "fixing" them. Use when the user asks to record an approved deviation from the project's coding/prompt standards, or to document intentional business logic that must not be changed/simplified/removed, for specific file(s).
---

# document-spec

## Purpose
Author a single, approved specification document that records intentional, explicitly approved decisions for explicitly scoped file(s), so the project's code-review process honors them. A spec holds two record types: **approved deviations** from named governing standards (review must not flag the named standard for the scoped files), and **business logic to preserve** (review and future refactors must not change, simplify, reorder, or remove the recorded behavior for the scoped files). All standards and behaviors not recorded remain in full force. A spec records existing approval — it never grants approval, and never edits or weakens the standards themselves.

## Required Input
- The exact file(s)/path(s) to scope the spec to. If missing → ask; do not infer or broaden.
- For each record, its type: **deviation** or **preserved logic**.
- For a **deviation**: each specific standard being waived, precisely enough to cite. If named vaguely → ask which named rule(s).
- For **preserved logic**: the exact behavior/decision that must be kept, precisely enough for review to recognize it (what it does and what must not be done to it).
- The reason for each record. If missing → ask.
- Explicit confirmation the decision is intentional AND the approver's name/identity AND the approval date. If any is missing or implicit → ask, then STOP. Never infer, self-grant, or default the date.
- Any output/behavior contract the scoped code must honor (optional; ask only if the decision implies one).

## Procedure
Run in order; each step is a gate — complete Step N before Step N+1.

1. Confirm approval is explicit: intentional decision stated, approver identified, approval date given. If any is absent → ask one question naming exactly what is missing, then STOP. Never draft on assumed approval or a defaulted date.
2. Confirm the scope: enumerate the exact file(s)/path(s). If unstated, vague, or broader than the affected code → ask, then STOP. Never scope to a directory, glob, or "the project" unless the user names it explicitly.
3. Classify every record as **deviation** or **preserved logic**. If a record's type is unclear → ask, then STOP.
4. Discover where the project's governing standards live. Search, do not assume: a rules directory, `AGENTS.md`, `AGENT.md`/`AGENTS.md` (any depth), `CONTRIBUTING`, style/convention docs, linter/formatter configs, an SDD, or equivalent. When the repo is large, fan this discovery out with the `Agent` tool (`Explore` subagent) — each subagent sweeping one candidate source family and returning what it found — then consolidate the candidate list yourself; the fan-out changes nothing about what must be located. List candidates. If none can be found AND there is at least one deviation record → ask where standards live, then STOP.
5. For each **deviation**, locate the named standard within the discovered sources and read it fresh. Capture a citation the code-review process can match verbatim: source file + section/heading/rule identifier (and line/bullet if present). If a named standard maps to more than one candidate, or to none → ask which, then STOP. Never paraphrase an unread standard or invent a citation.
6. For each deviation, confirm the named standard actually applies to the scoped file(s); if it does not apply, a deviation record is unnecessary — report and ask whether to drop it.
7. Discover the project's docs root and its spec folder, keyed to the path the code-review process actually reads (e.g. `docs/spec/`, `project/docs/spec/`, or the nearest existing spec layout). Search; do not assume. If two docs roots are equally plausible → ask which, then STOP. If no spec folder exists → propose the path and WAIT for approval before creating it.
8. Choose one descriptive, generic spec filename under the spec folder. Do not overwrite an existing file without confirmation; if a spec for the same scope exists, update it rather than duplicating.
9. Write the spec document containing, in this order:
   - Title: a short generic title.
   - Scope: the exact scoped file path(s), listed verbatim. Nothing wider.
   - Summary: a short description of what the scoped file(s) do and why these decisions were made.
   - Approved deviations (include only if any exist): a table `Standard (citation) | Deviation | Reason`, one row per waived standard, each citation matching step 5 exactly.
   - Business logic to preserve (include only if any exist): a table `Behavior | Must not be changed how | Reason`, one row per preserved decision, described concretely enough for review to recognize it.
   - Output/behavior contract: include only if one applies.
   - Directive to Code Review: two explicit, bounded instructions as applicable — (a) for the listed file(s), do NOT flag the named waived standard(s); (b) for the listed file(s), do NOT change, simplify, reorder, or remove the preserved behavior(s). Each names both the item(s) and the scoped file(s). Never global.
   - All other standards still apply: one line stating every standard and behavior not recorded above continues to apply in full to the scoped file(s).
   - Approval: approver + date, verbatim from step 1.
10. Verify each Directive names only the captured items and only the scoped files — nothing global, nothing unnamed — before finalizing.
11. Optionally add one minimal single-line pointer comment in each scoped file referencing the spec doc path — only if the file type supports comments and the user permits; no logic changes.
12. Report the created spec path, each scoped file, and each record (waived standard citation or preserved behavior). Change nothing else.

## Hard Prohibitions
- NEVER create or finalize a spec without an explicit, recorded approver and approval date; never self-grant, infer, or default them.
- NEVER record a standard, deviation, or preserved behavior the user did not name, or for any file outside the stated scope.
- NEVER widen scope to globs, directories, or the project unless the user names them explicitly.
- NEVER weaken, disable, or globally suppress review; every directive is bounded to named items on scoped files only.
- NEVER edit, rephrase, delete, reorder, or relax the governing standards/rules themselves.
- NEVER fabricate or approximate a citation; cite only what is located in discovered sources.
- NEVER assume project-specific paths, rule filenames, or docs layout; discover them every run.
- NEVER add corollaries, extra deviations, or extra preserved behaviors the user did not request.
- NEVER name any specific project, feature, or domain in the skill's own behavior; the document's content comes only from the user's input.

## When to Ask Instead of Acting
- Approval is implied but the approver or date is not explicitly stated → ask, then STOP.
- A record's type (deviation vs preserved logic) is unclear → ask, then STOP.
- The user names "the standards" or a rule vaguely, without a citable identity → ask which named rule(s).
- A preserved behavior is described too loosely for review to recognize → ask for the concrete behavior.
- The scope is unstated, ambiguous, or wider than the affected code → ask for exact file(s).
- A named standard cannot be uniquely located in any discovered source, or maps to more than one → ask to resolve it.
- The governing standards' location cannot be found and there is a deviation record → ask where they live.
- The docs root or spec folder is ambiguous, or must be created → ask before writing.
- The requested spec would touch anything global or unnamed → ask to narrow it first.
