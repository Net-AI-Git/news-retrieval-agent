# routes/ — Agent Guide

## Purpose
FastAPI HTTP boundary. Each router maps URLs to one service or orchestration entry point — nothing more. A file may declare **several routers** grouped by area; each is registered independently in [`api.py`](api.py:1).

## Contains
- [`api.py`](api.py:1) — `api_router` aggregator; registers every other router via `include_router(...)`.
- [`ping.py`](ping.py:1) — liveness probe.
- [`docs.py`](docs.py:1) — Swagger / OpenAPI assets routing.
- [`example_feature.py`](example_feature.py:1) — domain endpoints; may declare several routers grouped by area in the one file.

## Coding Rules (specific to this directory)
- A route handler is a **thin shim**: parse request → generate `flow_id` (`str(uuid4())`) → call exactly one service or orchestration entry point → return its result.
- `response_model=` uses a `BaseModel` imported from [`../schemas/`](../schemas/) (the shared `Response`).
- One or more routers per file — each `<area>_router = APIRouter(prefix="/<area>", tags=["<area>"])`, grouped by area. A single-router file may name it `router`.
- Register every router in [`api.py`](api.py:1) via `api_router.include_router(<module>.<name>_router)` — alphabetical or grouped by domain.
- Dependencies (auth, request-scoped objects) live in [`../dependencies.py`](../dependencies.py:1) and are pulled via `Depends(...)`.

## Forbidden in this directory
- No business logic — deterministic business behavior moves to a service; multi-agent coordination moves to orchestration.
- No SQL, no GPT calls, no CRM HTTP — those belong in [`../repositories/`](../repositories/).
- No inline `BaseModel` declarations — schemas live in [`../schemas/`](../schemas/).
- No `try/except` here — the called service or orchestration entry point owns lifecycle handling.
- No type hints (FastAPI signature annotations are allowed where the framework requires them — that is the only exception).
- No prefix duplication across files.

## See Also
- [`.Codex/rules/02-code-layout.md`](../../../.Codex/rules/02-code-layout.md:1) — file layout.
- [`.Codex/rules/03-code-quality.md`](../../../.Codex/rules/03-code-quality.md:1) — function size, single-line statements.
- [`project/docs/AGENTS.md`](../../docs/AGENTS.md:1) — per-feature SDD layout (no global SDD).
