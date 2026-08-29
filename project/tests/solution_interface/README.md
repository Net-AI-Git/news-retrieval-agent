# Solution Interface

## Goal

Verify that a harness-style import of root `solution.py` can call `answer` live and receive only the public answer schema.

## Scope

Exercises root `solution.py`, `src/routes/grounded_answering.py`, `src/orchestration/grounded_answering_workflow.py`, and `src/schemas/agent.py`. Live Q01 goes through `POST`-equivalent `grounded_answering()`. No mocks.

## How to run

```text
cd project
uv run python -m unittest tests.solution_interface.test_solution_interface
```

Live HTTP path:

```text
cd project
uv run uvicorn main:app
```

Then `POST /api/grounded-answering/run` with `{"content": "<question>"}`. The envelope is `{content, flow_id, trace_id}`; `content` is the answer JSON.

## Inputs

No files in `inputs/`. The live test loads Q01 from `src/data/questions.json`.

## Expected outcome

`build_index` and `answer` are importable. A live `answer` returns only `answer` plus citations that contain only `article_title` and `snippet` strings. The HTTP envelope from `grounded_answering()` also returns `flow_id` and the span-derived `trace_id`.

## Status

Active — 2026-08-26
