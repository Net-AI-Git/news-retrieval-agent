# repositories/ — Agent Guide

> Directory-scoped standards for all external-system access (Oracle / CRM / GPT / shared infra). Loaded by Codex and binding for every file under `project/src/repositories/`.

## Purpose
All external-system access. Three repository categories live here, **never mixed**:
- **Oracle DB** → single `oracle_repository.py` (shared by all features; add when first Oracle feature is needed).
- **CRM** → single `crm_repository.py` (shared by all features; add when first CRM feature is needed).
- **GPT / LLM** → one file per feature: `gpt_<feature_name>_repository.py`.
- **Shared infra** → [`redis_repository.py`](redis_repository.py:1), [`local_logging_repository.py`](local_logging_repository.py:1). Optional vendor-client stubs shipped as reusable examples: [`pinecone_repository.py`](pinecone_repository.py:1), [`embeddings_repository.py`](embeddings_repository.py:1) — delete any your service does not use.

If a feature needs Oracle + CRM + GPT, the **service** coordinates between them — never the repositories themselves.

---

## SECTION A — Oracle (`oracle_repository.py`)
- Single class `OracleRepository` with engine as class-level attribute.
- All methods `@staticmethod`. SQL `text(...)` strings written **inside the method body** — never at class or module scope.
- Methods grouped by feature, new features appended at the bottom. Each method handles its own connection + commit.
- Every method accepts `task_data` and `flow_id`. Logs the full `task_data` via [`local_logging_repository.py`](local_logging_repository.py:1) for batch traceability.
- **No business logic** — no threshold comparisons, no conditional derivations, no data transformations. The service computes values; the repository persists them ready-made.
- Imports: `os`, `dotenv`, `sqlalchemy` (`create_engine`, `text`, `Engine`), `LocalLoggingRepository`.

## SECTION B — GPT (`gpt_<feature_name>_repository.py`)
- One file per feature. Class name: `Gpt<FeatureName>Repository`.
- `OpenAI` client as a class-level attribute. No factory, no dataclass, no `lru_cache`.
- All methods `@staticmethod`. Each method accepts `task_data` (and extracts what it needs internally) + `flow_id`.
- The active production prompt lives under [`../prompts/`](../prompts/). Repository code loads its fixed file and contains no authored prompt text.
- Model params (`seed`, `top_p`, `temperature`) passed **directly** in the API call. No `MODEL_PARAMS` constants. Deployment name via `os.getenv()` inline.
- `json.loads()` happens **in the same method**, immediately after `response.choices[0].message.content`. Parsing is part of the GPT contract, never offloaded to the service.
- Plain-text responses: return `response.choices[0].message.content` as-is, no parsing.
- Header comment at the very top of the file describing input/output examples — **the only comment exception** in the codebase.
- Imports: `os`, `json`, `re`, `Path`, `httpx`, `OpenAI`, `dotenv`, `LocalLoggingRepository`.

## SECTION C — CRM (`crm_repository.py`)
- Single class `CrmRepository` with session/cert as class-level mechanism.
- Shared infra at the top: `get_session`, `reset_session`, `resolve_cert_path`, `send_to_crm`.
- `@classmethod` for session-state methods; `@staticmethod` for stateless ones.
- Simple payloads (**1–3 lines** of construction) → the service calls `CrmRepository.send_to_crm()` directly (no wrapper).
- Complex body (**4+ lines** of payload construction or logic) → a dedicated method on `CrmRepository`.
- No trivial per-feature wrappers that only construct a dict and delegate.
- Imports: `os`, `ssl`, `tempfile`, `time`, `requests`, `urllib3`, `cryptography`, `dotenv`, `LocalLoggingRepository`.

## SECTION D — General (every repository)
- No abstractions, no indirection (no dataclasses, factories, generic callers).
- Code duplication across repositories is acceptable — simplicity beats DRY.
- Each repository owns its client/engine/session; logic lives directly in the methods.
- Single top-level `try/except Exception` per method. STARTING log before `try`, ERROR log inside `except`, FINISHED log after the block (see [`.Codex/rules/04-error-and-logging.md`](../../../.Codex/rules/04-error-and-logging.md:1)).
- ERROR log content: `{"error": repr(err), "task_data": task_data}`.
- `LocalLoggingRepository.log_event` is the foundational shared sink and keeps its six-field event signature; it does not emit lifecycle events for its own write operation.

---

## SECTION E — Prompt Consumption
- Production prompt authoring and structure rules live in [`../prompts/AGENTS.md`](../prompts/AGENTS.md); experiment rules live in [`../../tests/AGENTS.md`](../../tests/AGENTS.md).
- GPT repositories load their fixed production prompt, pass runtime input separately as structured user data, and parse the response in the same method.
- The repository returns the full unfiltered result. Confidence filtering remains service business logic.

---

## Forbidden in this directory
- No cross-mixing: the Oracle file has no GPT/CRM code; CRM has no SQL/GPT; GPT has no SQL/CRM.
- No module-level / class-level SQL or prompt constants.
- No inline prompt text or runtime experiment selection.
- No `DELETE` + `INSERT` for idempotent writes — use MERGE/UPSERT or check-then-insert.
- No type hints, no docstrings, no inline comments (the GPT-file header comment is the only exception).
- Validate external responses; do not add speculative checks for controlled internal inputs.
- No abstractions, no factories, no dataclasses for "configuration".

## See Also
- [`.Codex/rules/02-code-layout.md`](../../../.Codex/rules/02-code-layout.md:1) — file layout, naming, layer placement.
- [`.Codex/rules/03-code-quality.md`](../../../.Codex/rules/03-code-quality.md:1) — function size, formatting, minimal code.
- [`.Codex/rules/04-error-and-logging.md`](../../../.Codex/rules/04-error-and-logging.md:1) — single try/except + local event shape.
- [`.Codex/rules/reference/gpt_feature_name_repository.py`](../../../.Codex/rules/reference/gpt_feature_name_repository.py:1) — canonical GPT repository.
- [`../prompts/AGENTS.md`](../prompts/AGENTS.md) — production prompt content and naming.
- [`../../tests/AGENTS.md`](../../tests/AGENTS.md) — offline prompt experiments.
- [`project/docs/AGENTS.md`](../../docs/AGENTS.md:1) — per-feature SDD layout (no global SDD).
