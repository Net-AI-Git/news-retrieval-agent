# Oracle Answer GT

## Goal

Run `run_answer` with gold GT facts injected as evidence (empty list for Q04/Q09), no Gather and no tools, and measure whether Answer matches local GT short answers and citation titles.

## Scope

Exercises `src/agents/answer_agent.py`, `src/prompts/answer_agent.md`, `src/orchestration/grounded_answering_workflow.py` (`filter_answer_citations` only), and `src/schemas/agent.py`. Evidence is built from `src/data/ground_truth/Q01.json`–`Q11.json` facts. Retrieval, Gather, and live Chroma are out of scope.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.oracle_answer_gt.run_oracle_answer_gt
```

Needs `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`. The runner pauses `ORACLE_ANSWER_PAUSE_SECONDS` between questions so an 11-question pass stays under the OpenRouter free-tier chat rate.

## Inputs

`inputs/control.md` is a snapshot of the previous production Answer prompt. The runner does not load it; `run_answer` loads `src/prompts/answer_agent.md`. Questions and gold facts come from `src/data/questions.json` and `src/data/ground_truth/Q01.json`–`Q11.json`. The production prompt must not contain those questions, their answers, or toy clones of the same traps.

## Expected outcome

`outputs/metrics_*.csv` has one row per question. `oracle_success=1` when:

- answerable: predicted short answer matches GT and every GT citation title is present
- unanswerable (Q04, Q09): status is refused and citations are empty

Pass is 11/11 `oracle_success=1` (9 answers + 2 refusals) with no evaluation items and no isomorphic few-shot in the prompt.

## Status

Active — Gate 3 closed 2026-08-27. Production prompt `src/prompts/answer_agent.md` (OpenAI `# Identity` / `# Instructions` / format-only `# Examples`). Passing CSVs: `outputs/metrics_2026-08-27_21-56-37.csv`, `21-58-37`, independent re-run `22-16-19` (all 11/11, no eval items, no isomorphic few-shot). Invalid: CSVs through `20-11-54` (eval items) and `20-57-32` / `21-30-46` (toy clones of Q08/Q10). Honest 8/11 baseline: `20-31-49`. Spec: `project/plans/gate3-oracle-answer-prompt-goal.md`.
