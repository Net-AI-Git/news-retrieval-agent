# prompts/ — Prompt Guide

## Purpose
Single source of truth for all authored LLM instructions. Prompt text is versioned and reviewed here, never embedded in Python code.

## Contains
- One active production prompt per consumer: `<consumer_module_name>.md`.
- The filename matches the agent or GPT repository module stem exactly.

## Placement and Loading
- Python code loads the prompt file at runtime and passes dynamic input separately as structured user data.
- Prompt text is English only.
- Prompt files contain no executable code, environment lookups, secrets, or production credentials.
- No authored instruction, role, rule, response-format text, or example may be duplicated in Python.
- Do not create feature subdirectories, a second prompt location, or multiple prompt formats.

## Prompt Structure
- Match the consuming model's vendor prompt shape. Keep the prompt short.
- For OpenAI GPT developer/system messages, sections appear in this order:
  1. `# Identity`
  2. `# Instructions`
  3. `# Examples` (optional)
- Context is not written into the prompt file. The consumer sends it as the user message.
- Inside `# Examples`, use `<user_query>` … `</user_query>` and `<assistant_response>` … `</assistant_response>`.
- Do not use `[INSTRUCTIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, or `[EXAMPLE 01]` as the outline.
- Do not use Claude-style XML instruction tags such as `<role>` or `<decision_policy>` as the main outline.
- Do not put evaluation-set questions, answers, gold citations, or isomorphic few-shot of those items in the prompt.
- Prefer zero-shot. Add examples only for format (verbatim field copy, empty refuse), using invented data and fake URLs.

## Prompt Experiments
- Control, candidates, datasets, runners, and results live in one named experiment under [`../../tests/`](../../tests/).
- Production code never selects an experimental variant.
- After approval, copy only the winning prompt content into the consumer's production prompt file.
- Historical experiment inputs and results remain in [`../../tests/`](../../tests/).

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
