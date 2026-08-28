# Live Gather hop inventory

## Goal

Score production Gather’s hop inventory against `sub_questions` in all 11 local-GT files. Each gold sub-question must be a distinct standalone string, with named outlets and publication windows kept on the claims they belong to, and with no packed or featured-in-only hops.

## Scope

`src/prompts/gather_agent.md` and `src/agents/gather_agent.py` only. One Gather LLM invoke per question. Retrieve, tools, Chroma, Grade, and Answer are out of scope.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_hops.run_live_gather_hops
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_MODEL`). Does not need Chroma. No console print; success is a new CSV trio.

## Inputs

`inputs/control.md` is the starting production Gather prompt. Snapshot each live edit as `inputs/candidate_<name>.md`. The runner always loads `src/prompts/gather_agent.md`.

## Expected outcome

`outputs/metrics_*.csv`, `hops_*.csv`, `calls_*.csv`. Gold inventory is `src/data/ground_truth/Q01.json`–`Q11.json` field `sub_questions` (see `src/data/ground_truth/README.md`). Outlet and publication-window checks join the retrieve `expected_tool_calls` (`agent: retrieve`) at the same `sub_question_index`. `hop_success=1` when `prompt_leak_hit=0`, every gold sub-question is covered by a distinct agent string, no packed outlets/needs, no extra/featured-in hops, no misattached outlet, and named publication windows stay in the matching string.

Pass for the prompt GOAL: two consecutive newest metrics files, same prompt, `hop_success=1` on all 11 rows, short OpenAI-shaped file, no exam text and no lookalike examples.

## Status

Active — 2026-08-28. Spec: `project/plans/gate4-gather-hop-inventory-prompt-goal.md`.
