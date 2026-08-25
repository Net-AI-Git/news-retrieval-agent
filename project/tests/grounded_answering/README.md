# Grounded Answering

## Goal

Verify citation filtering, empty-evidence refusal, gather stop routing, and layer boundaries for the TASK 04 loop without live model or Chroma calls.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py`, `src/agents/gather_agent.py`, `src/agents/answer_agent.py`, `src/schemas/agent.py`, and `src/prompts/`.

## How to run

```text
cd project
uv sync
uv run python -m unittest tests.grounded_answering.test_grounded_answering
```

## Inputs

No files in `inputs/`. Tests use in-memory evidence from the ChatGPT TechCrunch fact already in `src/data/facts.json`.

## Expected outcome

A citation whose url is in evidence is kept. A citation whose url is not in evidence forces refusal. A missing url may match `article_title`. Empty evidence skips the answer LLM and refuses. Gather routes to tools only while budget remains. Agents do not import services or repositories. Prompts exist and forbid source-file access. Graph failures return a refused payload.

## Status

Active — 2026-08-24
