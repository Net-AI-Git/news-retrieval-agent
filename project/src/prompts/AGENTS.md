# prompts/ — Prompt Guide

## Purpose
Single source of truth for all authored LLM instructions. Prompt text is versioned and reviewed here, never embedded in Python code.

## Contains
- One active production prompt per consumer: `<consumer_module_name>.md`.
- The filename matches the agent or GPT repository module stem exactly.
- Static instructions, definitions, rules, response format, and examples.

## Placement and Loading
- Python code loads the prompt file at runtime and passes dynamic input separately as structured user data.
- Prompt text is English only.
- Prompt files contain no executable code, environment lookups, secrets, or production credentials.
- No authored instruction, role, rule, response-format text, or example may be duplicated in Python.
- Do not create feature subdirectories, a second prompt location, or multiple prompt formats.

## Prompt Experiments
- Control, candidates, datasets, runners, and results live in one named experiment under [`../../tests/`](../../tests/).
- Production code never selects an experimental variant.
- After approval, copy only the winning prompt content into the consumer's production prompt file.
- Historical experiment inputs and results remain in [`../../tests/`](../../tests/).

## Prompt Structure
- Wrap the entire prompt in `[INSTRUCTIONS]...[/INSTRUCTIONS]`.
- Sections appear in this order and use this exact wording:
  1. `[DEFINITIONS]...[/DEFINITIONS]`
  2. `ROLE:`
  3. `TASK:`
  4. `RULES:`
  5. `CONFIDENCE SCORE (integer 1–5):`
  6. `RESPONSE FORMAT:`
  7. `[EXAMPLE 01]...[/EXAMPLE_01]`
- Do not use alternate headings such as `STRICT RULES:`, `CRITICAL RULE:`, `ANSWER FORMAT:`, or `RESPONSE:`.

## Definitions
- Define only domain-specific terms the model cannot infer.
- Domain terms appear in `UPPERCASE` throughout the prompt.
- Terms not listed in `[DEFINITIONS]` are not uppercased as domain terms.

## Examples
- Use two-digit blocks: `[EXAMPLE 01]...[/EXAMPLE_01]`.
- Include at least one empty or edge-case result.
- Use realistic production-shaped English data and varying confidence scores, including a score below `4`.
- Before adding examples, ask the user where approved real examples can be found. Never invent production examples.
- Never include credentials, customer PII, or unapproved production content.

## Confidence Score
- Every result item includes an integer `score` from `1` to `5`.
- The prompt defines the scale exactly:
  - `5 = Certain — explicitly and clearly present in the input`
  - `4 = High confidence — strong evidence supports this`
  - `3 = Moderate — some evidence but ambiguous`
  - `2 = Low — weak or indirect evidence`
  - `1 = Very low — barely mentioned, speculative`
- Filtering by the configured confidence threshold remains service business logic.

## Response Format
- Specify the exact output structure, keys, types, example, and empty-result form.
- Forbid markdown wrappers: `Do NOT wrap the response in markdown code blocks (no ```json or ```).`
- GPT repositories parse JSON immediately after the model call and return the full unfiltered result.
- Plain-text consumers return the raw model text.

## Forbidden
- No Python, YAML, JSON, Jinja, or generated prompt templates in this directory.
- No prompt manager or alternate prompt store.
- No inline dynamic values; runtime data is passed separately by the consumer.
- No control, candidate, dataset, runner, or experiment result in this directory.
- No duplicated prompt text across unrelated production consumers.

## See Also
- [`../agents/AGENTS.md`](../agents/AGENTS.md) — agent consumers.
- [`../repositories/AGENTS.md`](../repositories/AGENTS.md) — direct GPT consumers and parsing.
- [`../../tests/AGENTS.md`](../../tests/AGENTS.md) — offline prompt experiments.
- [`.Codex/rules/reference/gpt_feature_name_repository.py`](../../../.Codex/rules/reference/gpt_feature_name_repository.py) — external-prompt loading reference.
