# Live Retrieve GT

## Goal

Score isolated retrieve hops against all 11 local-GT questions. Hops are `expected_tool_calls` rows with `agent` equal to `retrieve` in `src/data/ground_truth/` (see that folder’s README). Each hop is invoked alone with that sub-question only. Success is a correct tool fill (verbatim question, outlet token, publication-date filters), not gold rank.

## Scope

`src/prompts/retrieve_agent.md` and `src/agents/retrieve_agent.py` (`run_retrieve` only). No Gather, Grade, Answer, Chroma execution, or ranking.

## How to run

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_retrieve_gt.run_live_retrieve_gt
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_RETRIEVE_AGENT_MODEL`). No vector store. No console print; success is a new CSV pair.

## Inputs

`inputs/control.md` is the starting production Retrieve prompt. Snapshot each live edit as `inputs/candidate_<name>.md`. The runner always loads `src/prompts/retrieve_agent.md`. Isolated hop strings come from live `src/data/ground_truth/Q*.json`: `sub_questions` via `sub_question_index` on rows where `agent` is `retrieve`. Unbound `search_corpus` rows are skipped.

## Expected outcome

`outputs/metrics_*.csv` (11 rows) and `outputs/hops_*.csv` (one row per GT retrieve hop). `retrieve_success=1` when every hop on that question copies the input into `question`, fills `source` only from a news outlet named in that string, fills publication-date filters only when the GT retrieve hop has them (ISO-8601 with UTC offset, same calendar day), emits exactly one `search_facts` call, does not answer, and `prompt_leak_hit=0`.

Pass: two consecutive newest metrics files, same Retrieve prompt, `retrieve_success=1` on all 11 rows, vendor-shaped prompt, no exam text and no lookalikes.

## Status

Active — 2026-08-28. Spec: `project/plans/gate4-retrieve-isolated-hop-prompt-goal.md`.
