---
name: update-skill
description: Modify an existing named skill under `.agents/skills` based on the user's exact request — minimal wording, no inference, no scope creep. Updates every existing mention of the subject inside the skill for consistency. Use when the user asks to change, tighten, relax, rephrase, extend, or remove skill behavior.
---

# update-skill

## Purpose

Apply a skill change requested by the user to a single existing `SKILL.md` under [`.agents/skills/`](../), updating every mention of the subject inside that skill (description — including its "Use when ..." activation clause —, procedure, prohibitions, ask-instead clauses) so the skill stays internally consistent.

If the targeted skill does not exist → STOP and tell the user to run `create-skill` instead. This skill does not create new skills.

## Required Input

- The target skill name. If missing or ambiguous → list all skills under [`.agents/skills/`](../) and ask, do not pick.
- The change the user wants, in their own words. Example: "the sync-sdd skill must also reject changes to repository AGENTS.md without explicit approval".

If the wording is too vague to compress without losing meaning → ask one focused question, then stop.

## Procedure

### Step 1 — Locate the target skill
- Confirm exactly one [`.agents/skills/<name>/SKILL.md`](../) matches.
- If no match → STOP and redirect to `create-skill`.
- If multiple plausible matches → ask, do not pick.

### Step 2 — Find every existing mention
- Read the target `SKILL.md` in full.
- List every section/bullet that mentions the subject of the change (description including its "Use when ..." activation clause, procedure step, prohibition, ask-instead clause, examples).

### Step 3 — Decide scope of edits
- For every hit that contradicts or overlaps with the requested change → it MUST be updated for consistency.
- If the subject is absent and the user wants it added → add it in the single most relevant section of the target skill.
- If two sections seem equally relevant → ask, do not pick.

### Step 4 — Write each addition/modification
- Use the **fewest words** that convey the change.
- Match the bullet style, indentation, and heading conventions of neighbouring content.
- Keep the `name` / `description` front-matter format intact (two fields only — no `trigger`; the activation context lives in `description`'s "Use when ..." clause). Update `description` only if the user's change affects the skill's purpose or activation.
- Frontmatter constraints are hard platform requirements — a violation silently breaks skill discovery. After editing, the file MUST still satisfy: `---` on line 1 **and a closing `---` line** before the `# <name>` heading; `name` lowercase letters/numbers/hyphens only, ≤ 64 chars, matching the directory, no XML tags, and free of the reserved words `anthropic` / `Codex`; `description` non-empty, ≤ 1024 chars, third person, stating what **and** when; body ≤ 500 lines; forward-slash relative paths only; every MCP tool named fully qualified as `ServerName:tool_name`; no time-sensitive wording ("new", "currently", "as of <version>").
- Write generically — never bind the skill to a specific feature name, service, or project. Use placeholders (e.g. `<feature_name>`, `<name>`) and general phrasing so it stays reusable when `.Codex/` is copied to another project.
- No examples, no rationale, no preamble — unless the user explicitly asked for them.

### Step 5 — Apply in one pass
- Apply all edits to the single target `SKILL.md` together.
- Touch ONLY the bullets/lines that mention the subject — do not "harmonize" unrelated sections.
- Do NOT touch any other skill.

### Step 6 — Report
Reply in chat with: the file changed, every section touched, and each new/modified bullet verbatim. Nothing else.

## Hard Prohibitions

- Do NOT create a new skill — redirect to `create-skill`.
- Do NOT leave the file with unclosed frontmatter, a `name` that breaks the Step 4 constraints, an empty `description`, or a bare (unqualified) MCP tool name.
- Do NOT modify any skill other than the one named by the user.
- Do NOT extend the change to cover cases the user didn't mention.
- Do NOT add corollaries, exceptions, or "while we're at it" edits.
- Do NOT rephrase unrelated sections.
- Do NOT add explanations or rationale into the skill itself.
- Do NOT hard-code a specific feature name or project-specific identifier — keep the skill general and portable across projects.
- Do NOT create or delete files inside the skill directory beyond editing the existing `SKILL.md`, unless the user explicitly asked for it.
- Do NOT delete, rewrite, or reorganize (move between sections, open new sections, or open new files) content unrelated to the requested change unless the user explicitly approved it.

## When to Ask Instead of Acting

- The target skill name is missing or matches more than one directory.
- The change contradicts an existing prohibition or procedure step in the same skill.
- The target section inside the skill is ambiguous.
- The wording the user gave is too vague to compress without losing meaning.
- The requested change would make the skill too large or mix unrelated responsibilities — propose a reorganization (move between sections, new section, or splitting into a new skill) and stop.

Ask one focused question, then stop.
