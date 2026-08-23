# Phase 3 — Error Handling & OpenTelemetry Logging (Hardening)

> Code generated → [`02-code-layout.md`](02-code-layout.md) | Validated → [`03-code-quality.md`](03-code-quality.md)
> Repos → [`project/src/repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md)
> **Scope:** Sections 1–4 govern services and repositories. Agent, tool, and orchestration lifecycle handling follows the target directory's `AGENTS.md` and MUST preserve framework interrupts, cancellations, checkpoints, and resumable state.

## SECTION 1: THE SINGLE TRY/EXCEPT PATTERN

> Why exactly one, at the top of each function: every failure then produces exactly one ERROR event in OpenSearch, at the level that owns the operation, with the full stack trace intact. Nested handlers multiply events for a single fault and swallow the frames that identify where it started — which makes a production trace unreadable.

- Every function MUST have **exactly one** `try/except Exception` block wrapping all core logic.
- No multiple, nested, or try/except inside helpers.
- Structure: STARTING log → try → except (ERROR log) → FINISHED log → return.
- Catch `Exception` broadly — NOT specific types.
- ALL logic that produces the return value MUST live inside `try` — nothing between `except` and FINISHED except the FINISHED log itself.
- Never catch framework control-flow interrupts or cancellation signals as application failures.

## SECTION 2: HELPER FUNCTIONS — NO TRY/EXCEPT
- Internal helpers (`parse_llm_response`, `format_payload`, etc.) have NO try/except.
- Errors bubble up to the caller's single top-level try/except.

## SECTION 3: NO SILENT FAILURES
- Every `except` MUST log through `OpenSearchRepository` with `level="ERROR"`. No `except: pass` or `except: return`.
- Error content MUST include `repr(err)` (preserves exception type name).
- ERROR format: `content={"error": repr(err), "task_data": task_data}`.
- Any failure = entire function fails. No partial execution or recovery.

## SECTION 4: SERVICE ENTRY FUNCTIONS

> Why entry points absorb their failures: the orchestrator runs several independent features per flow. One feature's exception must cost that feature only — it is already logged as ERROR, so the flow continues and the remaining features still complete.

- `run_*` functions return safe defaults on error (`[]`, `""`, `None`) — NEVER re-raise.
- Single feature failure MUST NOT crash the entire processing flow.

## SECTION 5: LOG STATUSES
- Repositories: ONLY `STARTING`, `FINISHED`, `ERROR`. No intermediate statuses.
- Services: ONLY `STARTING`, `FINISHED`, `ERROR`.
- Orchestrator: ONLY `STARTING`, `FINISHED`, `ERROR`.
- Agents, tools, and orchestration use standard GenAI spans; application lifecycle logs are emitted only at workflow boundaries.

## SECTION 6: LOG LEVEL POLICY
- `level="INFO"`: for STARTING, FINISHED.
- `level="ERROR"`: for ERROR status only.

## SECTION 7: LOG FORMATTING

> Why the shape is fixed: dashboards and monitor queries parse these events by field. `content=task_data` verbatim keeps every event queryable on the same keys — a cherry-picked dict silently drops the field a future query needs, and manual timestamps disagree with the infrastructure's own.

- `OpenSearchRepository.log_event(...)` on a single line.
- Never pass `process=` — it is auto-detected by the repository.
- No manual `time.time()` or duration calculations — timestamps from infrastructure.
- Pass `task_data` directly as `content` — no cherry-picked dicts or `{**base_ctx}` spreads.
- STARTING/FINISHED: `content=task_data`. ERROR: `content={"error": repr(err), "task_data": task_data}`.

## REFERENCE EXAMPLES

```python
# Orchestrator
def perform_main_flow(task_data, flow_id):
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    try:
        matched_feature_codes = task_data.get("matched_feature_codes", [])
        if FEATURE_CODE in matched_feature_codes:
            run_feature_name(task_data, flow_id)
    except Exception as err:
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return

# Service
def run_feature_name(task_data, flow_id):
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    try:
        feature_result = GptFeatureNameRepository.run_feature(task_data, flow_id)
        OracleRepository.save_feature_results(task_data, feature_result, flow_id)
    except Exception as err:
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return

# GPT Repository
@staticmethod
def run_feature(task_data, flow_id):
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    response_text = ""
    try:
        response = GptFeatureNameRepository.client.chat.completions.create(model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"), seed=151, top_p=1, messages=[...])
        response_text = response.choices[0].message.content
    except Exception as err:
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return response_text
```

## HARDENING CHECKLIST
- [ ] Every service/repository function has exactly ONE try/except (catches `Exception`)
- [ ] Agent runtime interrupts, cancellations, checkpoints, and resumable state are preserved
- [ ] STARTING before try, FINISHED after try/except, ERROR inside except
- [ ] No silent failures — every except logs with `repr(err)`
- [ ] Helpers have NO try/except (errors bubble up)
- [ ] Only STARTING/FINISHED/ERROR statuses (no intermediate)
- [ ] INFO for STARTING/FINISHED, ERROR for ERROR
- [ ] Log calls on single line, no manual timestamps
- [ ] `content=task_data` for STARTING/FINISHED — never cherry-picked dicts
- [ ] Service entry functions return safe defaults (don't crash orchestrator)
