---
name: feature-test-doc
description: Research a named feature end-to-end and write or update its Technical Test Design Specification for engineering readers. Use when the user asks to document or explain how a feature is tested. Technical prose only, with no code.
---

# feature-test-doc

## Purpose

Produce a single technical document — a Technical Test Design Specification (TDS) — written for an engineering reader, that explains end-to-end how one FEATURE is tested: the mechanism, how it is built and how it runs. It describes precise technical detail in prose (no code, no snippets, no configuration blocks) — the exact inputs and outputs, the comparison logic, and (where the feature uses one) how the LLM prompt is used. The document lives in a dedicated, purpose-named folder under the repository's `docs/` directory — one file per feature. On every invocation the skill re-researches the feature's current code and either creates the document (if none exists) or updates the existing one wherever the code has changed since it was last written. Every statement in the document MUST trace to what the feature's code actually does — nothing invented.

## Required Input

- The FEATURE name. If missing, ambiguous, or it matches more than one feature in the codebase → STOP and ask; never infer or guess which feature is meant.
- (Optional) The dedicated docs folder. Default to `docs/testing-process/`. If the repository has no obvious `docs/` directory, or has several → ask where the folder should live; do not pick silently.

If the feature name cannot be resolved to exactly one feature with certainty → ask one focused question, then stop.

## Procedure

### Step 1 — Resolve the feature (no assumptions)
- Confirm the feature name maps to exactly one feature. Search the service, repository, route, schema, and test-data layers for that name.
- If zero or more than one candidate matches → STOP and ask which feature; do not proceed on a guess.

### Step 2 — Research the feature end-to-end (read-only)
The layers below are independent read-only lookups — fan them out with the `Agent` tool (`Explore` subagent), one subagent per layer (route/entry-point, service, each repository, GPT/LLM, test data), each returning a structured summary of what that layer does for this feature; then synthesize the summaries yourself. For a small feature, tracing inline is fine — the fan-out is an efficiency mechanism, never a change to what is researched. Trace the full path the feature takes through the code and note, in plain terms, what each layer does:
- the route / entry point that starts the feature's test;
- the service that orchestrates the test run;
- the repositories it calls (external API, GPT / LLM, database, OpenSearch, etc.);
- if the feature uses an LLM: what is sent to it (the instruction it is given and the values it compares) and how the verdict is read back out of the response;
- how the feature's output is validated — structure, field types, any format / exact-match rules, and string / value matching;
- how batched or multi-part inputs inside one case are handled (if applicable);
- the test data used — where the example / expected files live, how many, and their shape;
- how pass / fail is decided, which metrics the result report shows, and where reports are stored.
Read only — never modify feature or application code.

### Step 3 — Check for an existing document
- Look in the dedicated docs folder for a file named for this feature.
- If none exists → this run creates it.
- If one exists → read it, compare each claim against the current code from Step 2, and update only the parts the code has changed. Update the file in place; do not create a second file for the same feature.

### Step 4 — Write the document (technical, engineering-facing, zero code)
Write, in precise technical prose for an engineering reader, describing HOW the mechanism is built and runs, covering:
- what the feature does, in one short paragraph;
- what test data we use and where it comes from;
- how a test runs end-to-end, from submitting the input to comparing the result against the expected answer — describe the actual mechanism (what is extracted, and how the comparison happens);
- what each check verifies at a technical level — the exact fields checked, structure matching, field types, any format / exact-match rules, and string / value matching;
- if the feature uses an LLM: what the prompt talks about, what values are sent to it to judge a match, and how the verdict is read back out of the response;
- how batched or multi-part inputs inside one case are handled (if applicable);
- how we decide the test passed or failed, and what the report shows.
No code, snippets, pseudocode, SQL, JSON, or configuration blocks anywhere in the document — technical prose (and simple lists) only. Naming exact field names in prose is allowed; reproducing code, JSON structures, or prompt text verbatim is not.

### Step 5 — Report
Reply in chat with: the file path written, whether it was created or updated, and (if updated) a one-line-per-item list of which parts changed because the code changed. Nothing else.

## Hard Prohibitions

- Do NOT infer, guess, or default the feature name — if it is missing or ambiguous, ask (Step 1).
- Do NOT put any code, code snippet, pseudocode, SQL, JSON, or configuration block in the document — it is technical prose for an engineering reader; naming exact field names in prose is allowed, reproducing code / JSON / prompt text verbatim is not.
- Do NOT invent testing behavior — every statement must trace to what the feature's code actually does.
- Do NOT modify feature or application code; this skill only reads code and writes the document.
- Do NOT write the document outside the dedicated docs folder.
- Do NOT create a new file when one already exists for the feature — update it in place.
- Do NOT add feature detail this skill was not asked about, or generalize beyond the feature named.

## When to Ask Instead of Acting

- The feature name is missing, or matches zero or more than one feature.
- You cannot locate the feature's code with confidence.
- The dedicated docs folder is unclear — no `docs/` directory, or several plausible ones.
- The existing document and the current code disagree in a way you cannot reconcile from the code alone.

Ask one focused question, then stop.
