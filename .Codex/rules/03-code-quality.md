# Phase 2 — Code Quality

> Phase 1 → [`02-code-layout.md`](02-code-layout.md) | Next → [`04-error-and-logging.md`](04-error-and-logging.md)
> Repository specifics → [`project/src/repositories/AGENTS.md`](../../project/src/repositories/AGENTS.md) | Prompt specifics → [`project/src/prompts/AGENTS.md`](../../project/src/prompts/AGENTS.md)
> **Scope:** per-function quality — how each function is written. File / layer / placement decisions live in [`02-code-layout.md`](02-code-layout.md) and are NOT restated here.

## SECTION 1: FUNCTION SIZE & SPLITTING

> Why 25 lines, and why *not* fewer: 25 lines is one screen — a reviewer holds the whole function in their head at once. The limit is a ceiling, not a target. Splitting below it trades one readable unit for a call chain the reader must reassemble, which is the more common failure here.

- Every function MUST be **≤ 25 lines**. No exceptions.
- Maximize the 25-line limit — consolidate related logic. If 4×5-line functions can merge into 1×25 → merge.
- Do NOT extract tiny helpers called from only one place — inline them.
- Split a function into helpers ONLY when it exceeds 25 lines — otherwise keep it as one function.
- **Exception:** sub-functions keeping `run_*` free of business logic are justified even if single-use.

## SECTION 2: FORMATTING

> Why one statement per line, however long: `git diff` and stack traces both work in lines. A wrapped call turns a one-line change into a multi-line diff and points the traceback at a continuation line instead of the statement.

- Function signatures on a **single line** — no splitting parameters.
- All code statements on a single line — no multi-line breaks for calls, assignments, dicts, lists.
- Long lines are acceptable — never break them. Extract variables only when reused, not to shorten.
- No comment-based headers (`# --- Step 1 ---`) inside functions.

## SECTION 3: VARIABLE HYGIENE

> Why names carry the weight: with no type hints and no comments (Section 5), the variable name is the only documentation the next reader gets. A single-use intermediate adds a name to track without adding information.

- Every variable MUST have a descriptive, meaningful name — no single-letter variables (`i`, `r`, `e`, `x`).
- Name must convey purpose: what the variable holds and why it exists.
- Variables declared **close to first use** — not top-of-function blocks.
- No ad hoc `current_step` tracking variables outside declared orchestration state.
- No intermediate variables for single-use values — inline directly in the call.
- Variable justified ONLY when used **more than once** or needed for a conditional.

## SECTION 4: CONTROL FLOW

> Why validate boundaries only: internal calls use controlled contracts; external, model, tool, and persisted-state boundaries require explicit validation because their data is not controlled by the current function.

- No single-line loops or list comprehensions used as statements.
- All `for`/`while` in standard multi-line block format.
- List comprehensions OK only for simple transformations; prefer loops if complex.
- Validate external, model, tool, and persisted-state boundaries. Internal calls follow their declared contracts without speculative edge-case handling.
- Code only for supported runtime states and documented recovery paths.

## SECTION 5: MINIMAL CODE

> Why minimal documentation in code: names carry intent; only framework-consumed metadata and required contracts justify annotations or docstrings.

- Write ONLY what is strictly necessary. Every line must justify its existence.
- No premature abstractions (need 2+ use cases). No boilerplate / scaffolding / stubs.
- No comments or docstrings except required file headers and tool descriptions consumed by the agent runtime.
- Type annotations are allowed only where required by Pydantic, FastAPI, or the agent/tool/orchestration runtime. Services and repositories remain plain Python unless their directory guide states otherwise.
- No unused return values — if no caller reads the result, use a bare `return` (no value).
- No trivial wrappers: if a function only constructs args (**1–3 lines**) and delegates → inline at call site. **4+ lines** of construction justify a dedicated method — the same threshold [`02-code-layout.md`](02-code-layout.md) Section 3 uses for CRM payloads. Wrappers are also justified by complex logic (loops, conditionals, multi-step). If a shared method already logs STARTING/FINISHED/ERROR → wrappers MUST NOT add duplicate logs.

## SECTION 6: DATA SAFETY

> Why: a `DELETE` + `INSERT` pair that fails between the two statements leaves the table short of rows that existed before the run. MERGE/UPSERT makes a re-run harmless.

- Never `DELETE` + `INSERT` for idempotent writes — use MERGE/UPSERT or check-then-insert.

## REVIEW CHECKLIST
- [ ] Every function ≤ 25 lines (Section 1)
- [ ] Minimum functions — no unnecessary splitting (Section 1)
- [ ] All signatures + statements on a single line (Section 2)
- [ ] No comment-header banners inside functions (Section 2)
- [ ] All variables have descriptive, meaningful names — no single-letter (Section 3)
- [ ] Variables close to first use, no single-use intermediates, no ad hoc `current_step` outside orchestration state (Section 3)
- [ ] Loops in multi-line form; comprehensions only for trivial transforms (Section 4)
- [ ] Validation is limited to external, model, tool, and persisted-state boundaries (Section 4)
- [ ] Code targets supported runtime states and documented recovery paths (Section 4)
- [ ] Comments, docstrings, and type hints appear only where explicitly allowed (Section 5)
- [ ] No unused return values — bare `return` if discarded (Section 5)
- [ ] No trivial wrappers (1–3 lines of arg construction → inline), no redundant logging (Section 5)
- [ ] No `DELETE` + `INSERT` for idempotent writes (Section 6)
- [ ] Phase 1 layout rules already enforced (see [`02-code-layout.md`](02-code-layout.md))
