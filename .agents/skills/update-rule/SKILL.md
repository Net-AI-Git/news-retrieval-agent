---
name: update-rule
description: Add or modify a rule in `.Codex/rules/` based on the user's exact request — minimal wording, no inference, no scope creep. Updates every existing mention of the subject for consistency. Use when the user asks to change, tighten, relax, rephrase, extend, or remove an existing rule under `.Codex/rules/` (typical phrasing — "update the rule", "change the rule", "the rule should now ...").
---

# update-rule

## Purpose

Apply a rule change requested by the user to [`.Codex/rules/`](../../../.Codex/rules/), updating every existing mention of the subject (rule text, examples, checklists, reference snippets) so the ruleset stays internally consistent.

If the subject does not exist anywhere in [`.Codex/rules/`](../../../.Codex/rules/) and the user intent is to introduce something brand new → this skill still adds it, in the single most relevant file/section. (For a strict "must-not-exist" check, use `create-rule`.)

## Required Input

The rule change the user wants, in their own words. Example: "prompts must always include a [DEFINITIONS] block".

If the wording is too vague to compress without losing meaning → ask one focused question, then stop.

## Procedure

### Step 1 — Find every existing mention
- Search **all files** in [`.Codex/rules/`](../../../.Codex/rules/) for every existing mention of the subject (rule text, examples, checklists, reference snippets).
- List every hit before editing anything.

### Step 2 — Decide scope of edits
- For every hit that contradicts or overlaps with the requested change → it MUST be updated for consistency.
- If no hit exists → add the rule in the single most relevant file/section.
- If two files seem equally relevant for a brand-new rule → ask, do not pick.

### Step 3 — Write each addition/modification
- Use the **fewest words** that convey the rule.
- Match the bullet style, indentation, and numbering of neighbouring rules.
- Write generically — never bind the rule to a specific feature name, service, or project. Use placeholders (e.g. `<feature_name>`, `<name>`) and general phrasing so it stays reusable when `.Codex/` is copied to another project.
- No examples, no rationale, no preamble inside the rule bullet itself — unless the user explicitly asked for them. A rule bullet states the requirement, nothing more.
- **Exception — section-level motivation:** several sections in [`.Codex/rules/`](../../../.Codex/rules/) open with a `> Why ...` blockquote directly under the heading, explaining the constraint the section enforces. That block is part of the established format — preserve it, and update it when the requested change alters what the section enforces.

### Step 4 — Apply in one pass
- Apply all changes together.
- Touch ONLY the bullets/lines that mention the subject — do not "harmonize" unrelated rules.

### Step 5 — Report
Reply in chat with: every file changed, every section touched, and each new/modified bullet verbatim. Nothing else.

## Hard Prohibitions

- Do NOT extend the rule to cover cases the user didn't mention.
- Do NOT add corollaries, exceptions, or "while we're at it" edits.
- Do NOT rephrase neighbouring rules.
- Do NOT add explanations or rationale into the rule bullet itself — the only exception is the section-level `> Why ...` blockquote described in Step 3.
- Do NOT hard-code a specific feature name or project-specific identifier — keep the rule general and portable across projects.
- Do NOT touch any file outside [`.Codex/rules/`](../../../.Codex/rules/).
- Do NOT delete, rewrite, or reorganize (move between sections, open new sections, or open new files) content unrelated to the requested change unless the user explicitly approved it.

## When to Ask Instead of Acting

- The target file is ambiguous.
- The rule contradicts an existing rule.
- The wording the user gave is too vague to compress without losing meaning.
- The requested change would make the target file too large or mix unrelated subjects — propose a reorganization (move between sections, new section, or new rule file) and stop.

Ask one focused question, then stop.
