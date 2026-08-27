# Answers, Transcripts, and Evaluation

## Goal

Produce the assignment `answers.json` and tool-call transcripts through the public `solution.py` path, then audit schema, citation traceability, and tool-only evidence. Answer-vs-ground-truth quality is recorded, not optimized.

## Scope

Exercises root `solution.py`, `src/orchestration/grounded_answering_workflow.py`, `src/schemas/agent.py`, and the local JSONL lifecycle log. Live calls go through `build_index` only when the Facts Chroma store is missing; otherwise the existing index handle is passed to `answer`. Questions run one at a time (`WORKERS` in `src/conts.py`) so embedding calls stay under the OpenRouter free-tier per-minute limit.

## How to run

```text
cd project
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.answers_transcripts_evaluation.run_answers_transcripts_evaluation
uv run python -m unittest tests.answers_transcripts_evaluation.test_answers_transcripts_evaluation
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and `src/data/ground_truth/Q01.json` through `Q11.json`.

## Expected outcome

- Root `answers.json` contains all eleven IDs in the public schema.
- Root `transcripts.json` contains gather/tool/answer turns and retrieved evidence for each question.
- `outputs/evaluation.md` records contract checks and defers GT accuracy as a known quality limitation.

## Status

Active — 2026-08-26
