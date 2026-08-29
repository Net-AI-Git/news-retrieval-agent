# Answers, Transcripts, and Evaluation

## Goal

Produce the assignment `answers.json` and tool-call transcripts through root `solution.py` (`build_index` / `answer` / `python solution.py`), then audit schema, citation traceability, and tool-only evidence. Answer-vs-ground-truth quality is recorded from that same public path.

## Scope

Exercises root `solution.py`, `src/orchestration/grounded_answering_workflow.py`, and `src/schemas/agent.py`. `python solution.py` writes `answers.json` and `transcripts.json` through `answer` / `recorded_answer`. Live calls use the existing Facts Chroma handle when present, otherwise `build_index`. Questions run one at a time.

## How to run

```text
cd project
uv run python solution.py
uv run python -m tests.answers_transcripts_evaluation.run_answers_transcripts_evaluation
uv run python -m unittest tests.answers_transcripts_evaluation.test_answers_transcripts_evaluation
```

## Inputs

No files in `inputs/`. The runner loads `src/data/questions.json` and `src/data/ground_truth/Q01.json` through `Q11.json`.

## Expected outcome

- Root `answers.json` contains all eleven IDs in the public schema.
- Root `transcripts.json` contains gather/retrieve/tools/grade/answer turns and retrieved evidence for each question.
- `outputs/evaluation.md` records contract checks and GT match from the public `solution.py` path.

## Status

Active — 2026-08-29. Passing: contract 11/11, GT match 11/11.
