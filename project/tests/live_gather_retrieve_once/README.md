# Live Gather then one Retrieve

## Goal

Score one Gather decompose plus a single Retrieve invoke over that full sub-question list, then that batch’s `search_facts` hits, against all 11 local-GT questions.

## Scope

`src/prompts/gather_agent.md` snapshot, experimental batched Retrieve prompt, `src/agents/gather_agent.py` shape, `src/agents/retrieve_agent.py` tools, one Gather invoke, one Retrieve invoke, tools only, live facts Chroma (`RETRIEVAL_TOP_K=1`). Isolated per-hop Retrieve, Grade, Answer, corpus, and later Gather turns are out of scope.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_retrieve_once.run_live_gather_retrieve_once
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_AGENT_MODEL`, `OPENAI_RETRIEVE_AGENT_MODEL`, `OPENAI_EMBEDDING_MODEL`) and `vector_stores/facts_chroma`. No console print; success is a new CSV trio.

## Inputs

`inputs/gather_prompt.md` is the 10/11 Gather snapshot (`candidate_abilities_first_outlet_example.md`). `inputs/control.md` is production isolated Retrieve. `inputs/candidate_batch_copy.md` is the batched Retrieve prompt. The runner loads only this directory’s prompt files.

## Expected outcome

`outputs/metrics_*.csv`, `hops_*.csv`, `calls_*.csv`. Same `first_hop_success` contract as `live_gather_first_hop`: gold `facts` URL+sentence in the first-batch hits, sourced calls on unanswerable rows, dated filters when the user named publication dates, `prompt_leak_hit=0`.

Pass: two consecutive newest metrics files, same prompts, `first_hop_success=1` on all 11 rows, no exam text.

## Status

Archived — 2026-08-29. Isolated first-hop gold coverage is **11/11 twice** (`live_gather_first_hop` `metrics_2026-08-29_11-16-45.csv`, `11-19-10.csv`). This batch-Retrieve experiment stayed **8/11** (`outputs/metrics_2026-08-28_22-30-09.csv`) and is not the score. Production Retrieve stays frozen and isolated.
