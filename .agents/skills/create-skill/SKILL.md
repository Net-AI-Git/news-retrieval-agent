---
name: create-skill
description: Add a brand-new named skill under `.agents/skills` based on the user's exact request — minimal wording, no inference, no scope creep. If a skill with overlapping purpose already exists, stop and redirect to `update-skill`. Use when the user asks to add, introduce, or define a new skill.
---

# create-skill

## Purpose

Create a single new skill directory and `SKILL.md` under [`.agents/skills/`](../) that does not already exist. Refuse overlapping additions — those belong to `update-skill`.

## Required Input

- The exact skill purpose the user wants, in their own words.
- A skill name (kebab-case). If missing → derive the shortest accurate name from the user's purpose and confirm it back in one line before writing.

If the purpose is too vague to compress without losing meaning → ask one focused question, then stop.

## Procedure

### Step 1 — Confirm the skill is new
- List every existing skill directory under [`.agents/skills/`](../).
- Read each existing `SKILL.md` `name` and `description` field.
- If any existing skill's purpose overlaps with the requested one → STOP. Tell the user to run `update-skill` instead. Do not proceed.

### Step 2 — Confirm the skill name and path
- Path: [`.agents/skills/<name>/SKILL.md`](../) — kebab-case `<name>`, no extra files.
- If the name collides with an existing directory → ask, do not pick.

### Step 3 — Write `SKILL.md`
Use this exact structure, in this order, with the fewest words that convey the skill. Match the tone and bullet style of neighbouring skills (e.g. [`sync-sdd/SKILL.md`](../sync-sdd/SKILL.md:1)).

```
---
name: <name>
description: <what the skill does, then a "Use when ..." clause naming the user phrasing or task context that activates it — this is Codex's only auto-invocation surface, so make it precise>
---

# <name>

## Purpose
<one short paragraph>

## Required Input
<bullets — exactly what the user must provide; what to ask for if missing>

## Procedure
<numbered steps — each step is one focused action>

## Hard Prohibitions
<bullets — what the skill must NEVER do>

## When to Ask Instead of Acting
<bullets — ambiguity cases that must trigger a single focused question, then stop>
```

- Write generically — never bind the skill to a specific feature name, service, or project. Use placeholders (e.g. `<feature_name>`, `<name>`) and general phrasing so it stays reusable when `.Codex/` is copied to another project.
- No examples, no rationale, no preamble — unless the user explicitly asked for them.
- Do NOT add sections the user didn't request.

### Step 4 — Validate the frontmatter before writing
These are hard platform constraints — a violation silently breaks skill discovery, so check each one:
- The frontmatter opens with `---` on line 1 and **closes with its own `---` line** before the `# <name>` heading. A missing closing delimiter makes the whole file unparseable and the skill never loads.
- `name`: lowercase letters, numbers, and hyphens only; ≤ 64 characters; matches the directory name; contains no XML tags and neither of the reserved words `anthropic` / `Codex`.
- `description`: non-empty, ≤ 1024 characters, written in the third person, and states both **what** the skill does and **when** to use it.
- Body ≤ 500 lines. Longer content goes in a bundled reference file, referenced one level deep.
- All paths use forward slashes, relative to the skill directory — never Windows separators or absolute paths.
- Every MCP tool is named fully qualified as `ServerName:tool_name`; a bare tool name will not resolve.
- No time-sensitive wording ("new", "currently", "as of <version>") — it goes stale silently.

### Step 5 — Create in one pass
- Create exactly one file: [`.agents/skills/<name>/SKILL.md`](../).
- Do NOT create supporting files (scripts, references, READMEs) unless the user explicitly asked for them.

### Step 6 — Report
Reply in chat with: the new file path, the skill name, and the `description` line verbatim. Nothing else.

## Hard Prohibitions

- Do NOT proceed if an overlapping skill was found in Step 1 — redirect to `update-skill`.
- Do NOT write the file with unclosed frontmatter, a `name` that breaks the Step 4 constraints, an empty `description`, or a bare (unqualified) MCP tool name.
- Do NOT create supporting files alongside `SKILL.md` unless the user explicitly asked for them.
- Do NOT add sections beyond the structure in Step 3.
- Do NOT extend the skill's behavior to cover cases the user didn't mention.
- Do NOT add explanations or rationale into the skill itself.
- Do NOT hard-code a specific feature name or project-specific identifier — keep the skill general and portable across projects.
- Do NOT touch any file outside the new skill's directory.
- Do NOT delete, rewrite, or reorganize (move between sections, open new sections, or open new files) existing content as part of the new addition unless the user explicitly approved it.

## When to Ask Instead of Acting

- The skill name is ambiguous or collides with an existing directory.
- The requested purpose overlaps with an existing skill in a non-trivial way.
- The user's wording is too vague to compress into a `description` (including its "Use when ..." activation clause).
- The activation context cannot be stated unambiguously (multiple unrelated trigger conditions).
- The requested purpose would make the skill too large or mix unrelated responsibilities — propose splitting into multiple skills and stop.

Ask one focused question, then stop.
