---
name: sync-sdd
description: Reconcile code changes with a chosen SDD file. After applying any change, ensure the code still satisfies that SDD. If the user request and the SDD cannot both be satisfied, surface the conflict to the user — never silently override either side. Use on any task that touches files under `src/services/`, `src/repositories/`, `src/routes/`, `src/schemas/`, the orchestrator, or any architectural boundary described in the chosen SDD.
---

# sync-sdd

## Purpose

Keep the codebase aligned with a **specific SDD file chosen by the user**. A project may contain multiple SDDs (e.g. per microservice, per domain, per major feature) — this skill is always scoped to **one** SDD per invocation.

For every code change in scope:
1. Apply the user's request.
2. Verify the result still satisfies the chosen SDD.
3. If the SDD is violated → fix the code so **both** the user request and the SDD hold.
4. If both cannot hold simultaneously → STOP and surface the conflict for a user decision. Never pick a side silently.

## Required Input — Which SDD?

This skill **must** know which SDD to reconcile against. Resolve the target SDD in this order:

1. **User provided a path explicitly** → use it.
2. **The task context names one SDD unambiguously** (e.g. the user said "the auth service SDD" and only one matches) → use it.
3. **Otherwise** → list every SDD candidate under [`project/docs/SDD/`](../../../project/docs/SDD/) (any file/folder under that directory, regardless of extension — `.md`, `.docx`, `.pdf`, etc.), present the candidates to the user, and ask which one to sync. Do **not** default.

If zero SDDs exist → ask the user where the SDD lives or whether to abort.

## SDD Format — No Assumptions

- The SDD can be **any format the team uses** (`.md`, `.docx`, `.pdf`, mixed `.md` + diagrams). Read it as plain text where possible; if the format is binary, ask the user to summarize the relevant sections or convert to text.
- This skill does **not** assume a fixed section layout. It does not require sections numbered 1-6 or any specific headings.
- The skill extracts whatever architectural claims the SDD actually makes — file paths, layer rules, integrations, data-flow expectations — by reading the document. If the SDD is silent on a topic, the skill falls back to [`.Codex/rules/`](../../../.Codex/rules/) only.

## Scope (when this skill activates)

Activate when the task touches **any** architectural surface described in the **chosen** SDD. Typical surfaces:
- the project's `services/`, `repositories/`, `routes/`, `schemas/` directories.
- the orchestrator entry-point.
- any external integration listed in the chosen SDD.

The exact paths come from the chosen SDD itself — not hard-coded here. If the SDD does not specify a path, ask the user.

Out of scope: tests, notebooks, static assets, docs other than the chosen SDD, prompt **content** (only prompt **placement** matters here).

## Constraints Extracted from the SDD (whatever the SDD covers)

The SDD is the source of truth for whatever it chooses to define. The skill extracts and enforces, in order of priority:

1. **Layer / file placement claims** — which file lives where; what each layer is allowed to contain.
2. **Data-flow contracts** — required arguments through layers (e.g. `task_data`, `flow_id`), persistence boundaries.
3. **External integration claims** — which external systems are used and which repository owns each.
4. **Feature lifecycle claims** — what creating a new feature must include.
5. **Decision log** — informational only; explicitly-recorded legacy items are allowed exceptions.

If the SDD does not cover one of these, the skill simply does not check it. It does NOT invent constraints.

## Procedure

### Step 0 — Identify the target SDD
- Resolve the SDD path per **Required Input — Which SDD?** above.
- Confirm the path back to the user in one line before reading.
- All subsequent steps operate against this single file.

### Step 1 — Read the chosen SDD before writing any code
- Read the SDD in full (or have the user summarize it if the format is binary).
- Extract the architectural claims it actually makes — do not assume claims it does not contain.
- When verifying those claims against a change that spans many files/layers, fan out the read-only code inspection with the `Agent` tool (`Explore` subagent) — one subagent per SDD claim or per layer — each returning whether the current code matches that claim. Synthesize the results yourself. This is an efficiency mechanism only; it does not change which claims are checked or the conflict-resolution flow.
- If the SDD is silent on the area the change touches → fall back to [`.Codex/rules/`](../../../.Codex/rules/) and proceed; do not block.

### Step 2 — Plan the change against both contracts
Before any edits:
- State, in one paragraph, what the user asked for.
- State, in bullets, which claims of the chosen SDD the change touches (quote them verbatim).
- Decide if the change can be implemented in a way that satisfies both the user request and the SDD.
- If yes → proceed to Step 3.
- If no → jump to Step 5 (Conflict Resolution).

### Step 3 — Apply the change
- Execute the edits.
- The change must satisfy:
  - the user's intent,
  - the SDD claims listed in Step 2,
  - all [`.Codex/rules/`](../../../.Codex/rules/) (rules win over SDD on style; SDD wins on architecture).

### Step 4 — Verify post-condition
After edits, re-check each SDD claim identified in Step 1 against the new code. For every mismatch, classify and act:
- `MISSING_IN_CODE` — SDD claim no longer matched? → patch the code in the same task.
- `MISSING_IN_SDD` — code now introduces something the SDD does not describe? → STOP and ask the user (Step 5, case "SDD needs update").
- `LAYER_VIOLATION` — change put logic in the wrong layer per the SDD? → move it.
- `SIGNATURE_DRIFT` — new public function violates an SDD-prescribed signature? → fix the signature.

A change is "done" only when every SDD claim still holds.

### Step 5 — Conflict Resolution (when both contracts cannot hold)
When the user request and the chosen SDD conflict in a way the code cannot satisfy both:

1. Stop editing immediately.
2. State the conflict in this exact format:

```
# SDD Conflict — Decision Required

## SDD File
<absolute or workspace-relative path of the chosen SDD>

## User Request
<one sentence>

## SDD Constraint
<verbatim quote of the relevant SDD passage + a pointer to where it appears in the SDD>

## Why They Conflict
<one paragraph — be specific about the file/function/layer involved>

## Options
A. Change the code to honor the SDD (rejects part of the user request) — concrete description.
B. Update the SDD to reflect the new reality (the user request becomes the new contract) — concrete description.
C. Drop the user request entirely.

## Recommendation
<one sentence — which option preserves the most architectural integrity, and why>
```

3. Wait for the user's choice. Do not pick a default.

### Step 6 — Acting on the decision
- Option A → revert/avoid the conflicting code; finish the rest of the user request.
- Option B → ask the user to confirm the exact SDD edit; only then update **the chosen SDD file**. If the SDD has a decision-log section, append the change there; otherwise, propose where to record it. Do NOT touch any other SDD in the repo.
- Option C → abort the task cleanly.

## Hard Prohibitions

- Do NOT default to a single SDD path — always confirm which SDD applies (Step 0).
- Do NOT touch any SDD file that was not chosen for this invocation.
- Do NOT edit the chosen SDD without explicit user approval (Option B).
- Do NOT silently choose between the user request and the SDD — Step 5 is mandatory when they conflict.
- Do NOT invent SDD content to "patch" a check.
- Do NOT use this skill to enforce style/formatting — that is [`.Codex/rules/03-code-quality.md`](../../../.Codex/rules/03-code-quality.md:1).
- Do NOT report a drift as "fixed" without rerunning Step 4 end-to-end.
- Do NOT touch files outside scope (tests, notebooks, static).

## When to Ask Instead of Acting

- The target SDD is ambiguous (multiple candidates, no clear winner).
- The chosen SDD is missing or empty.
- The SDD passage the change touches is ambiguous (multiple readings possible).
- Step 4 surfaces a `MISSING_IN_SDD` — the code is now ahead of the SDD; only the user can decide if the SDD should catch up.
- A conflict in Step 5 has more than three plausible resolutions.

Ask one focused question, then stop.
