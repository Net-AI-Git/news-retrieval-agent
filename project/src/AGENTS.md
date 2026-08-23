# src/ — Agent Guide

## Purpose
Root of the application package. Holds cross-cutting modules (config, constants, shared utils, FastAPI dependencies) and the layer directories.

## Contains
- [`config.py`](config.py:1) — runtime configuration (env loading, settings objects).
- [`conts.py`](conts.py:1) — `UPPER_SNAKE_CASE` constants for the whole microservice. New constants go here, never inline.
- [`dependencies.py`](dependencies.py:1) — FastAPI `Depends` factories (auth, request-scoped objects).
- Runtime layer subdirectories: [`orchestration/`](orchestration/), [`agents/`](agents/), [`tools/`](tools/), [`services/`](services/), [`repositories/`](repositories/), [`routes/`](routes/), [`schemas/`](schemas/), [`prompts/`](prompts/). Auxiliary data lives in [`data/`](data/). Each directory has its own `AGENTS.md`.

## Coding Rules (specific to this directory)
- Anything used in ≥2 files moves into [`conts.py`](conts.py:1) (constants). Inline duplication is a smell.
- [`dependencies.py`](dependencies.py:1) is the **only** place FastAPI dependency factories live.
- Flat layout — do not create feature-named subdirectories at this level (see [`.Codex/rules/02-code-layout.md`](../../.Codex/rules/02-code-layout.md:1) Section 1).

## Forbidden in this directory
- No domain logic in [`config.py`](config.py:1) — that is infrastructure.
- No inline constants anywhere in the package — all go to [`conts.py`](conts.py:1).
- No new top-level files that duplicate an existing concern.

## See Also
- [`.Codex/rules/00-overview.md`](../../.Codex/rules/00-overview.md:1) — rule index.
- [`.Codex/rules/02-code-layout.md`](../../.Codex/rules/02-code-layout.md:1) Section 1 (flat layout) and Section 3 (layer placement / constants).
- [`project/docs/AGENTS.md`](../docs/AGENTS.md:1) — per-feature SDD layout (no global SDD).
