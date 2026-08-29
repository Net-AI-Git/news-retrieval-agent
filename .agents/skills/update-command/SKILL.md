---
name: update-command
description: Update the repository skill that replaced a legacy project slash command. Updates every affected mention for consistency. Use when the user asks to change an existing custom command; do not edit or create `.Codex/commands` files.
---

# update-command

## Purpose

Apply a command change requested by the user to its corresponding repository skill under [`.agents/skills/`](../), updating every affected mention so the skill stays internally consistent.

If the targeted command-style skill does not exist → STOP and tell the user to run `create-command` instead. This skill does not create new skills.

## Required Input

- The target command name (with or without leading slash). If missing or ambiguous → list all skills under [`.agents/skills/`](../) and ask, do not pick.
- The change the user wants, in their own words. Example: "the /connect-branch command must also report a final summary row count".

If the wording is too vague to compress without losing meaning → ask one focused question, then stop.

## Procedure

### Step 1 — Locate the target skill
- Confirm exactly one [`.agents/skills/<name>/SKILL.md`](../) matches.
- If no match → STOP and redirect to `create-command`.
- If multiple plausible matches → ask, do not pick.

### Step 2 — Find every existing mention
- Read the target skill in full.
- List every section/line that mentions the subject of the change (front-matter `description`, argument line, procedure step, prohibition).

### Step 3 — Decide scope of edits
- For every hit that contradicts or overlaps with the requested change → it MUST be updated for consistency.
- If the subject is absent and the user wants it added → add it in the single most relevant section.
- If two sections seem equally relevant → ask, do not pick.

### Step 4 — Write each addition/modification
- Use the **fewest words** that convey the change.
- Match the bullet style, indentation, and numbering of neighbouring content.
- Keep the frontmatter `name` and `description` fields valid. Update the description only if the user's change affects the skill's purpose or activation scope.
- Write generically — never bind the skill to a specific feature name, service, or project. Use placeholders (e.g. `<feature_name>`, `<name>`) and general phrasing.
- No examples, no rationale, no preamble — unless the user explicitly asked for them.

### Step 5 — Apply in one pass
- Apply all edits to the single target skill together.
- Touch ONLY the lines that mention the subject — do not "harmonize" unrelated sections.
- Do NOT touch any other skill.

### Step 6 — Report
Reply in chat with: the file changed, every section touched, and each new/modified bullet verbatim. Nothing else.

## Hard Prohibitions

- Do NOT create a new skill — redirect to `create-command`.
- Do NOT modify any skill other than the one named by the user.
- Do NOT create or edit `.Codex/commands` or `.claude/commands` files.
- Do NOT extend the change to cover cases the user didn't mention.
- Do NOT add corollaries, exceptions, or "while we're at it" edits.
- Do NOT rephrase unrelated sections.
- Do NOT add explanations or rationale into the skill itself.
- Do NOT hard-code a specific feature name or project-specific identifier — keep the command general and portable across projects.
- Do NOT introduce destructive defaults (force flags, mutating remotes, deletes) unless the user explicitly asked for them.
- Do NOT delete, rewrite, or reorganize (move between sections, open new sections, or open new files) content unrelated to the requested change unless the user explicitly approved it.

## When to Ask Instead of Acting

- The target command name is missing or matches more than one file.
- The change contradicts an existing prohibition or procedure step in the same command.
- The target section inside the command is ambiguous.
- The wording the user gave is too vague to compress without losing meaning.
- The requested change would make the skill too large or mix unrelated responsibilities — propose a reorganization or split and stop.

Ask one focused question, then stop.
