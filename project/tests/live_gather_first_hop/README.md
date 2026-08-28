# Live Gather first hop

## Goal

Score one Gather decompose plus isolated retrieve hops and that batch’s `search_facts` calls against all 11 local-GT questions. Every gold fact URL and sentence must already be in those hits, with `source` and publication-date filters when the user named them.

## Scope

`src/prompts/gather_agent.md`, `src/prompts/retrieve_agent.md`, `src/agents/gather_agent.py`, `src/agents/retrieve_agent.py`, one Gather invoke then retrieve hops then tools only, live facts Chroma (`RETRIEVAL_TOP_K=1`). Grade, Answer, corpus, and later Gather turns are out of scope.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_MODEL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`) and `vector_stores/facts_chroma`. No console print; success is a new CSV trio.

## Inputs

`inputs/control.md` is the starting production Gather prompt. Snapshot each live edit as `inputs/candidate_<name>.md`. The runner always loads `src/prompts/gather_agent.md` and `src/prompts/retrieve_agent.md`.

## Expected outcome

`outputs/metrics_*.csv`, `hops_*.csv`, `calls_*.csv`. `first_hop_success=1` when `prompt_leak_hit=0`, first-batch gold URL+snippet are complete (or an unanswerable row filled `source` for each named outlet), and dated calls meet `gt_dated_required_count` when the user named publication dates.

Pass: two consecutive newest metrics files, same Gather and retrieve prompts, `first_hop_success=1` on all 11 rows, vendor-shaped prompts, no exam text and no lookalikes.

## Status

Active — 2026-08-28. Gather emits standalone sub-questions; `retrieve_agent` fills `source` / dates and calls `search_facts`. First live score `metrics_2026-08-28_16-44-21.csv` is 8/11. Q05 gold complete (`The Age` only on that hop). Misses: Q01 gold miss at top-1 with `Sporting News` filled; Q04 packed both outlets into one sub-question so `source` stayed empty; Q07 over-split and missed the second TechCrunch fact. Spec: `project/plans/gate4-gather-first-hop-prompt-goal.md`.
