# Phase 3 — Error Handling & Local Structured Logging (Hardening)

> Code generated → [`02-code-layout.md`](02-code-layout.md) | Validated → [`03-code-quality.md`](03-code-quality.md)
> Repos → [`project/src/repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md)
> **Scope:** Sections 1–4 govern services and repositories except the foundational local logging and telemetry sinks named in Section 3. Agent, tool, and orchestration lifecycle handling follows the target directory's `AGENTS.md` and MUST preserve framework interrupts, cancellations, checkpoints, and resumable state. Section 8 governs every agentic workflow, agent, and tool.

## SECTION 1: THE SINGLE TRY/EXCEPT PATTERN

> Why exactly one, at the top of each function: every failure then produces exactly one ERROR event in the local JSONL log, at the level that owns the operation, with the full stack trace intact. Nested handlers multiply events for a single fault and swallow the frames that identify where it started — which makes a production trace unreadable.

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
- Every `except` MUST log through `LocalLoggingRepository` with `level="ERROR"`. No `except: pass` or `except: return`.
- `LocalLoggingRepository.log_event` is the foundational sink: it does not emit its own STARTING/FINISHED events, and a file-write failure reports to stderr instead of recursively logging.
- `local_telemetry_repository.py` is the foundational trace sink: its setup, processor, and write methods do not emit lifecycle logs, and instrumentation setup failures report to stderr instead of recursively tracing.
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
- Agents, tools, and orchestration emit application lifecycle logs only at workflow boundaries; detailed execution belongs to telemetry spans and span events.

## SECTION 6: LOG LEVEL POLICY
- `level="INFO"`: for STARTING, FINISHED.
- `level="ERROR"`: for ERROR status only.

## SECTION 7: LOG FORMATTING

> Why the shape is fixed: dashboards and monitor queries parse these events by field. `content=task_data` verbatim keeps every event queryable on the same keys — a cherry-picked dict silently drops the field a future query needs, and manual timestamps disagree with the infrastructure's own.

- `LocalLoggingRepository.log_event(...)` on a single line.
- Never pass `process=` — it is auto-detected by the repository.
- No manual `time.time()` or duration calculations — timestamps from infrastructure.
- Pass `task_data` directly as `content` — no cherry-picked dicts or `{**base_ctx}` spreads.
- STARTING/FINISHED: `content=task_data`. ERROR: `content={"error": repr(err), "task_data": task_data}`.

## SECTION 8: LOCAL AGENT TELEMETRY

> Why traces complement lifecycle logs: lifecycle events record application state, while one correlated span tree reconstructs the causal workflow, agent, model, retrieval, and tool execution without inventing intermediate log statuses.

- Initialize one OpenTelemetry `TracerProvider` before any agent runtime is used; identify the service with stable resource attributes and register each instrumentor exactly once.
- Every agentic execution MUST start one root workflow span at the orchestration entry point. Agent, model, retrieval, embedding, and tool operations MUST be descendants of that root span.
- Use official framework instrumentation for supported operations. Add manual spans only for uncovered operations; never instrument the same operation twice.
- Follow OpenTelemetry GenAI semantic conventions and standard operation names such as `invoke_workflow`, `invoke_agent`, `chat`, `embeddings`, `retrieval`, and `execute_tool`.
- Span names MUST be stable and low-cardinality. Runtime IDs, user content, queries, and tool arguments belong in attributes, never span names.
- Every span MUST inherit the active context and carry `flow_id`; lifecycle logs MUST derive `trace_id` from the active span. Never generate, copy, or calculate trace or span IDs manually.
- Record full observable inputs and outputs after redaction: workflow and agent identity, model and provider, messages, token usage, finish reason, retrieval query and results, tool name, call ID, type, arguments, result, and outcome. Never record hidden chain-of-thought.
- Independently timed work and retry attempts require child spans. Routing decisions, handoffs, budgets, checkpoints, approvals, and other timestamped occurrences require span events.
- A failed operation MUST record the exception once on its owning span, set span status to `ERROR`, and set `error.type`; successful span status remains unset. Handled retries and framework interrupts or cancellations MUST NOT mark the completed root operation as failed.
- API keys, authorization headers, credentials, session tokens, and secrets MUST never enter telemetry. Sensitive values MUST be redacted before span or event creation.
- Export agent telemetry to append-only local OTLP JSONL through the official file exporter. Runtime telemetry MUST NOT require a Collector, server, Docker, account, or network connection.
- Local tracing MUST sample every root trace and preserve the parent sampling decision; no agent span may be sampled out.
- Use immediate span processing for short-lived jobs. Batch processing is allowed only when shutdown or `force_flush` is guaranteed on every process exit path.
- OpenTelemetry API, SDK, framework instrumentation, semantic-convention, and file-exporter packages MUST be direct, version-compatible dependencies; never rely on a transitive telemetry dependency.
- Telemetry files MUST rotate without dropping spans. Deletion or retention is an explicit operator action, never an implicit exporter behavior.
- Auto-instrumented spans MUST NOT create additional lifecycle log events. Existing STARTING, FINISHED, and ERROR workflow-boundary logs remain unchanged and correlate through `trace_id`.

## REFERENCE EXAMPLES

```python
# Orchestrator
def perform_main_flow(task_data, flow_id):
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    try:
        matched_feature_codes = task_data.get("matched_feature_codes", [])
        if FEATURE_CODE in matched_feature_codes:
            run_feature_name(task_data, flow_id)
    except Exception as err:
        LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return

# Service
def run_feature_name(task_data, flow_id):
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    try:
        feature_result = GptFeatureNameRepository.run_feature(task_data, flow_id)
        OracleRepository.save_feature_results(task_data, feature_result, flow_id)
    except Exception as err:
        LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return

# GPT Repository
@staticmethod
def run_feature(task_data, flow_id):
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    response_text = ""
    try:
        response = GptFeatureNameRepository.client.chat.completions.create(model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"), seed=151, top_p=1, messages=[...])
        response_text = response.choices[0].message.content
    except Exception as err:
        LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
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
- [ ] One root workflow span owns one complete agentic execution
- [ ] Agent, model, retrieval, embedding, and tool spans share the root `trace_id` and carry `flow_id`
- [ ] Full observable content is captured after secret redaction; hidden chain-of-thought is never captured
- [ ] Local OTLP JSONL export works without Collector, server, Docker, account, or network access
- [ ] Short-lived processes flush every completed span before exit
