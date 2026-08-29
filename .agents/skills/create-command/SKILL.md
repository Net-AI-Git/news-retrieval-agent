---
name: create-command
description: Convert a request for a new project slash command into a named repository skill under `.agents/skills`. If a skill with overlapping purpose already exists, stop and redirect to `update-command`. Use when the user asks to add or define a custom project command.
---

# create-command

## Purpose

Create a single command-style repository skill under [`.agents/skills/`](../) that does not already exist. Refuse overlapping additions — those belong to `update-command`.

## Required Input

- The exact command purpose the user wants, in their own words.
- A skill name (kebab-case, no leading slash or extension). If missing → derive the shortest accurate name from the user's purpose and confirm it back in one line before writing.
- The expected argument (if any) the command accepts.

If the purpose is too vague to compress without losing meaning → ask one focused question, then stop.

## Procedure

### Step 1 — Confirm the workflow is new
- List every skill under [`.agents/skills/`](../).
- Read each skill's frontmatter `name` and `description`.
- If any existing skill's purpose overlaps with the requested one → STOP. Tell the user to run `update-command` instead. Do not proceed.

### Step 2 — Confirm the skill name and path
- Path: [`.agents/skills/<name>/SKILL.md`](../) — kebab-case `<name>`, exactly one skill directory.
- If the name collides with an existing skill → ask, do not pick.

### Step 3 — Write the skill
Use this exact structure, in this order, with the fewest words that convey the workflow. Match the tone and bullet style of neighbouring skills.

```
---
name: <name>
description: <one sentence — what the skill does and when it applies>
---

# <name>

Argument: <one sentence — what the argument is and a literal example>. Omit this line if the command takes no argument.

## Procedure

1. <numbered, imperative steps — each step is one focused action>

## Hard Prohibitions

- <bullets — what the command must NEVER do, especially destructive operations>
```

- Write generically — never bind the skill to a specific feature name, service, or project. Use placeholders (e.g. `<feature_name>`, `<name>`) and general phrasing.
- No examples, no rationale, no preamble — unless the user explicitly asked for them.
- Do NOT add sections the user didn't request.

### Step 4 — Create in one pass
- Create exactly one file: [`.agents/skills/<name>/SKILL.md`](../).
- Do NOT create supporting files unless the user explicitly asked for them.

### Step 5 — Report
Reply in chat with: the new file path, the skill name, and the `description` line verbatim. Nothing else.

## Hard Prohibitions

- Do NOT proceed if an overlapping skill was found in Step 1 — redirect to `update-command`.
- Do NOT create supporting files alongside the skill unless the user explicitly asked for them.
- Do NOT add sections beyond the structure in Step 3.
- Do NOT extend the skill's behavior to cover cases the user didn't mention.
- Do NOT add explanations or rationale into the skill itself.
- Do NOT hard-code a specific feature name or project-specific identifier — keep the command general and portable across projects.
- Do NOT include destructive defaults (force flags, mutating remotes, deletes) unless the user explicitly asked for them.
- Do NOT create `.Codex/commands` or `.claude/commands` files.
- Do NOT touch any file outside the new [`.agents/skills/<name>/`](../) directory.
- Do NOT delete, rewrite, or reorganize (move between sections, open new sections, or open new files) existing content as part of the new addition unless the user explicitly approved it.

## When to Ask Instead of Acting

- The skill name is ambiguous or collides with an existing skill.
- The requested purpose overlaps with an existing skill in a non-trivial way.
- The user's wording is too vague to compress into a one-sentence `description`.
- The argument contract is unclear (optional vs. required, format, multiplicity).
- The requested purpose would make the skill too large or mix unrelated responsibilities — propose splitting into multiple skills and stop.

Ask one focused question, then stop.
