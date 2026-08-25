# docs/ — Agent Guide

## Purpose
Architectural and operational documentation. The authoritative source for **what each feature is and why it is the way it is** — distinct from [`.Codex/rules/`](../../.Codex/rules/), which governs **how to write code**.

## Layout — One SDD per Feature

```
docs/
├── AGENTS.md                         ← THIS FILE
├── local_logging.md                  ← cross-cutting observability guide
├── spec/                             ← approved spec/waiver documents
├── testing-process/                  ← one manager-facing test-process doc per feature (feature-test-doc skill)
│   └── <feature_name>.md             ← plain-English, no code
└── SDD/                              ← all SDDs live here
    ├── <feature_name>/               ← one directory per feature
    │   ├── SDD.<ext>                 ← the feature's Software Design Document
    │   ├── diagrams/                 ← optional Mermaid / images
    │   └── notes.md                  ← optional extra context
    └── another_feature/
        └── SDD.<ext>
```

- **All SDDs live under [`SDD/`](SDD/)** — never at the top of [`docs/`](.).
- **Each feature owns its own SDD**, not the project as a whole. A "feature" here means a coherent business capability (e.g. `<feature_name>/`, `another_feature/`).
- The SDD file format is **not constrained by this directory** — `.md`, `.docx`, or any other format produced by the team's tooling is acceptable. The internal structure of the SDD is decided by its authors, not enforced here.
- Cross-feature concerns (local logging conventions, deployment runbooks) live as top-level `*.md` files in [`docs/`](.).
- When the [`sync-sdd`](../../.agents/skills/sync-sdd/SKILL.md#L1) skill runs, it asks **which** SDD to reconcile against — there is no single global SDD.
- **Approved spec/waiver documents live under [`spec/`](spec/)** — authored by [`document-spec`](../../.agents/skills/document-spec/SKILL.md#L1). Each records intentional, approved decisions (approved deviations from a named standard, or business logic to preserve) scoped to specific files, and directs code review to honor them.
- **Manager-facing test-process docs live under [`testing-process/`](testing-process/)** — authored by [`feature-test-doc`](../../.agents/skills/feature-test-doc/SKILL.md#L1). One `<feature_name>.md` per feature, plain-English (no code), explaining end-to-end how that feature is tested; updated in place when the feature's code changes.

## Coding Rules (specific to this directory)
- One SDD per feature, all under [`SDD/`](SDD/). Do NOT create a single project-wide `SDD.*`. Cross-feature material goes into a topic-specific `.md` at the top of [`docs/`](.) (like [`local_logging.md`](local_logging.md#L1)).
- Feature directory name = feature name in `snake_case`, matches the service file name where reasonable (e.g. `SDD/example_feature/` ↔ [`../src/services/example_feature_service.py`](../src/services/example_feature_service.py#L1) if that is the entry-point).
- The SDD's **internal structure is the author's choice** — markdown, Word, hand-drawn diagrams, whatever the team uses. This `AGENTS.md` does NOT prescribe sections.
- Every architectural change in code requires a paired update to the **relevant** SDD — or, if the change spans features, to every SDD it touches.
- Diagrams: prefer Mermaid inline when authoring in `.md`; place binary assets in `SDD/<feature>/diagrams/`.
- Markdown links use workspace-relative paths.

## Forbidden in this directory
- No code, no executable scripts, no test data.
- No duplication of [`.Codex/rules/`](../../.Codex/rules/) content — those rules are operational law and live elsewhere. A [`spec/`](spec/) document may **cite** a named rule it waives, but never restates the ruleset.
- No SDD files outside [`SDD/`](SDD/), and no "global" SDD inside it — SDDs are per-feature.
- No silent rewrites of any SDD — every change must come from an explicit user decision (per the [`sync-sdd`](../../.agents/skills/sync-sdd/SKILL.md#L1) conflict-resolution flow).
- No two SDDs claiming ownership of the same code path — if a file is shared, one feature owns it and the others cross-reference.

## See Also
- [`.agents/skills/sync-sdd/SKILL.md`](../../.agents/skills/sync-sdd/SKILL.md#L1) — reconciles code against a chosen SDD (asks which one to sync).
- [`.agents/skills/feature-test-doc/SKILL.md`](../../.agents/skills/feature-test-doc/SKILL.md#L1) — writes/updates the manager-facing test-process doc per feature under [`testing-process/`](testing-process/).
- [`.Codex/rules/00-overview.md`](../../.Codex/rules/00-overview.md#L1) — the operational ruleset.
