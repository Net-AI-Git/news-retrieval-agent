# Grounded Answering

## Goal

Verify that Answer receives every accumulated chunk, copies the exact evidence snippet it uses, orchestration keeps only snippet+url citation matches, and live Q01/Q07/Q09 follow that contract.

## Scope

Exercises `src/orchestration/grounded_answering_workflow.py`, `src/agents/gather_agent.py`, `src/agents/retrieve_agent.py`, `src/agents/answer_agent.py`, `src/schemas/agent.py`, `src/prompts/`, and the retrieval tool surface through a live loop.

## How to run

```text
cd project
uv sync
uv run python -m unittest tests.grounded_answering.test_grounded_answering
```

Live cases call OpenRouter and the local Chroma stores. They need `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_AGENT_MODEL`, `OPENAI_GRADE_AGENT_MODEL`, `OPENAI_ANSWER_AGENT_MODEL`, and `OPENAI_RETRIEVE_AGENT_MODEL`, plus existing `vector_stores/facts_chroma` and `vector_stores/corpus_chroma`.

## Inputs

No files in `inputs/`. Filter fixtures reuse the ChatGPT TechCrunch fact already in `src/data/facts.json`. Live cases load Q01, Q07, and Q09 from `src/data/questions.json`.

## Expected outcome

Answer receives the complete accumulated evidence list, including unrelated chunks. Answered results include at least one citation, and a citation is kept only when `snippet` and `url` both match an evidence item from that run. A mismatched url or paraphrased snippet forces refusal. Grade accepts only `enough`, `missing_hop`, or `empty_stop`. Gather routes to retrieve then tools only while budget remains. Agents do not import services or repositories. Live Q01 answers `Yes` with grounded snippets, live Q07 answers `ChatGPT` with grounded snippets, and live Q09 refuses.

## Status

Active — 2026-08-25
