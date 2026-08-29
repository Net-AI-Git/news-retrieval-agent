# Live Gather GT

## Goal

Run production Gather (LLM + live `search_facts`) on all 11 local-GT questions, with no Answer step. Score gold-in-evidence and stop timing.

## Scope

`src/prompts/gather_agent.md`, `src/prompts/retrieve_agent.md`, `src/prompts/grade_agent.md`, gather → retrieve → tools → grade routing, live facts Chroma. Answer and corpus are out of scope.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_gt.run_live_gather_gt
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_MODEL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`) and `vector_stores/facts_chroma`. No console print; success is a new CSV trio.

## Inputs

`inputs/control.md` is the rejected old template. Do not copy it into production. The runner always loads `src/prompts/gather_agent.md`.

## Expected outcome

`outputs/metrics_*.csv`, `hops_*.csv`, `calls_*.csv`. `gather_success=1` when gold URL+snippet are in evidence and stop is `on_time`, or when an unanswerable row made exactly `required_facts_calls` then stopped. `prompt_leak_hit` must stay 0.

Pass for the prompt GOAL: 11/11 twice on the same prompt, short OpenAI-shaped file, no exam text and no lookalike examples.

## Status

Standalone-retry track stopped at 7/11. Active Gather chunk spec: `project/plans/gate4-gather-gold-chunks-prompt-goal.md` (score with `tests.live_gather_first_hop`, not this loop).
