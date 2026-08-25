# docs/ — Index & Navigation

Navigation map only. The binding rules for this directory (layout, naming, what is forbidden) live in [`AGENTS.md`](AGENTS.md#L1) — read it before creating or editing anything here.

## What this directory holds

Feature intent and operational knowledge — **what each feature is, why it is that way, and how it is operated/tested**. It never holds code, and never restates [`.Codex/rules/`](../../.Codex/rules/), which governs **how to write code**.

## Where to go, by question

| I need to know… | Go to | Written by |
| --- | --- | --- |
| What a feature does and why it is designed that way | [`SDD/<feature_name>/`](SDD/) | the team; reconciled by [`sync-sdd`](../../.agents/skills/sync-sdd/SKILL.md#L1) |
| Whether a deviation from a rule is approved for a file | [`spec/`](spec/) | [`document-spec`](../../.agents/skills/document-spec/SKILL.md#L1) |
| How a feature is tested, end to end, in plain English | [`testing-process/<feature_name>.md`](testing-process/) | [`feature-test-doc`](../../.agents/skills/feature-test-doc/SKILL.md#L1) |
| How this service writes, queries, and visualizes local logs | [`local_logging.md`](local_logging.md#L1) | the team |
| The rules for this directory itself | [`AGENTS.md`](AGENTS.md#L1) | the team |

## Current contents

```
docs/
├── README.md                          ← THIS FILE — index only
├── AGENTS.md                          ← binding rules for this directory
├── local_logging.md                   ← JSONL storage + SQLite query conventions
├── SDD/                               ← one directory per feature (currently empty)
├── spec/                              ← one approved spec/waiver document per decision (currently empty)
└── testing-process/                   ← one <feature_name>.md per feature (currently empty)
```

`SDD/`, `spec/`, and `testing-process/` being empty is expected in the template — they fill up per feature.

## How agents must use it

- **Before changing feature code** → read that feature's SDD under [`SDD/`](SDD/); an architectural change requires a paired SDD update.
- **Before flagging a rule violation in review** → check [`spec/`](spec/) for a waiver scoped to that file ([`.Codex/rules/00-overview.md`](../../.Codex/rules/00-overview.md#L1) — a waiver overrides the standard only where stated).
- **Before touching local logging** → read [`local_logging.md`](local_logging.md#L1); the event field shape there is the contract.
- **When feature code changes** → update the feature's [`testing-process/`](testing-process/) doc in place.
- **Every document here is read fresh each run** — never assume a fixed set of files; enumerate the directory.
