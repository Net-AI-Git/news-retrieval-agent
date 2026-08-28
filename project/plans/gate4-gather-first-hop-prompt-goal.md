# GOAL — Gather first-hop decompose, 11/11 gold facts, no leakage

**Status:** In Progress  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/gather_agent.md`

This file is the **only** spec. Do not read other plans for prompt wording. Do not copy old prompt templates.

---

## Friend review — you will be failed for these

1. **Leakage is cheating.** Do not put evaluation-set questions, answers, article titles, snippets, URLs, sub-questions, expected tool-call question strings, or “the same question with fake names” into `gather_agent.md`. If the study guide contains the exam, the score is invalid even at 11/11.
2. **No examples of our exam.** `# Examples` is optional and usually wrong. If you add any, invent them yourself in a made-up domain. If someone who saw the 11 exam questions would recognize the example after you hide the proper nouns, delete it.
3. **Short.** Production `gather_agent.md` must stay **under 40 lines** and **under 350 words**. Cut, do not append.
4. **Vendor shape only.** Model is `openai/gpt-4o-mini`. You **must** use this outline and nothing else:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (optional; prefer none)
   - Do **not** put `# Context` in the file. The user question is sent as the user message.
5. **Do not use the old template.** Do not keep or translate `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`.
6. **Question wording is free.** Do not try to match ground-truth sub-questions or `expected_tool_calls.arguments.question`. Matching those strings is not the goal and copying them is leakage.

After every edit, before you run: open `gather_agent.md` and confirm all six checks pass.

---

## What this product is

News-fact answering over a local index. Retrieval is already good when `search_facts` gets a **standalone** query (one information need) plus the named `source` / publication-date filters. Top-1 returns one chunk per call. A packed question cannot return two gold facts. Repeating a failed string later is out of scope here.

You own **only Gather**. One tool: `search_facts` (`question` required; optional `source`, `published_from`, `published_to`). Gather must not answer the user.

**Grade is out of this job.** Do not edit Grade. Do not route to Grade. Do not score stop / continue / retry. Answer is frozen.

---

## Your job

Get **11/11** on a **first Gather LLM turn + that turn’s tool batch only**. After that one parallel `search_facts` batch, every local-GT **fact** for the question must already be in the hits.

Wording of the tool `question` arguments does **not** have to match ground truth. What must be true:

- The user question is split into independently verifiable needs.
- Independent needs are **separate** `search_facts` calls in the **same** first turn (parallel).
- If the user named a news outlet, that call passes it as `source`, not only inside the question text, and not as a yes/no “was this featured in …” search.
- If the user named a **publication** window, that call passes `published_from` / `published_to` as ISO-8601. A date that is part of an event stays in the question text.

**Pass:** two consecutive newest first-hop `metrics_*.csv` files, same Gather prompt, `first_hop_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor shape, length limits, no exam lookalikes.

`first_hop_success=1` means:

- `unanswerable=0`: every gold fact URL **and** gold fact sentence is in the **first-batch** hits (`first_hop_gold_complete=1`)
- `unanswerable=1`: first batch has `search_facts` with `source` filled for each named outlet the user gave (see `gt_source_required_count` vs `agent_source_call_count`); no gold facts are required
- If the user named publication dates (`gt_dated_required_count` > 0), the first batch uses date filters on those calls (`agent_dated_call_count` ≥ that count)
- `prompt_leak_hit=0`

Do not score `stop_verdict`, `too_early`, `too_late`, or later Gather turns. Those belong to Grade.

---

## What you must teach (general habits, not exam rows)

- One independently verifiable fact or claim → one `search_facts` call. A listed set of abilities or events is several calls, not one packed `question`.
- A named news outlet is the `source` argument on the call for the claim that outlet is said to report. Do not attach that outlet to claims it is not said to report. Do not invent a separate search whose only job is whether an outlet featured the subject.
- Never pass a person, company, product, or topic as `source`.
- Publication dates the user used as article windows go in `published_from` / `published_to` as ISO-8601 (include an explicit UTC offset so a date-only midnight is not used). Event dates stay in the question text.
- Send every independent call in the **first** turn. There is no second Gather turn on this board.

---

## Leakage check (do this yourself)

After each edit, search `gather_agent.md` against `project/src/data/questions.json` and `project/src/data/ground_truth/*.json`. Any full question, fact sentence, article title, URL, sub-question, or expected tool `question` string from those files is a leak. Delete it.

The runner flags `prompt_leak_hit=1` on exam strings and zeros every `first_hop_success`. Lookalikes are still on you.

Debugging a CSV is allowed. Pasting that row into the prompt is not.

If you want examples, invent them. Made-up outlets, towns, fake `https://….example/…` URLs.

---

## In / out

**Edit:**

- `project/src/prompts/gather_agent.md`
- snapshots `project/tests/live_gather_first_hop/inputs/candidate_<name>.md`
- first-hop board under `project/tests/live_gather_first_hop/` (runner + `README.md` + `inputs/control.md`) if it does not exist yet

**Do not edit:**

- `grade_agent.md`, Answer, any other prompt
- GT JSON, `questions.json`, `answers.json`
- agents, tools, services, repositories, production orchestration, `conts.py`
- `tests/live_gather_gt`, `tests/live_grade_gt`, `cases.json`
- vector stores

Do not add agents. Do not bind `search_corpus`. Do not run e2e, oracle-Answer, or Grade boards.

One **named hypothesis** per live run.

---

## First-hop board (this is 11/11)

Always from the inner `project/` folder.

The existing `tests/live_gather_gt` loop includes Grade and later turns. **Do not use it as the score for this job.**

If `project/tests/live_gather_first_hop/` is missing, create it:

- One Gather LLM invoke on the user question (same `run_gather` / production prompt as production).
- Execute only the tool calls from that message.
- Score **that batch’s hits** against GT facts (URL + snippet match, same rule as `live_gather_gt`).
- Write `outputs/metrics_*.csv`, `hops_*.csv`, `calls_*.csv`.
- Leak-scan **only** `gather_agent.md`.
- No Grade node. No second Gather turn. No console `print`.
- `README.md` required (goal, scope, how to run, inputs, expected outcome, status).

Then run:

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
```

Needs `.env`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, and `vector_stores/facts_chroma`.

If `uuid_utils` fails to import on this machine, use the same `uuid_utils.compat.uuid7` shim already used on this workspace.

These runs send evaluation payloads to OpenRouter. That is expected.

On `metrics_*.csv` count `first_hop_success=1`. That is N/11.

Also look at `first_hop_gold_complete`, `url_recall` / `snippet_recall`, `facts_call_count`, `gt_source_required_count` vs `agent_source_call_count`, `gt_dated_required_count` vs `agent_dated_call_count`, `prompt_leak_hit`, `runtime_error`.

On `calls_*.csv` (all rows are turn 1):

- Packed `question` (several facts in one string)
- Named outlet only in the question text, `source` empty
- Named publication date missing from `published_from` / `published_to`
- A yes/no “featured in {outlet}” call instead of `source=`

How to read a miss (teach a **general** habit, not that row):

- Gold URL/snippet missing → first-hop queries were packed, missing `source`, missing dates, or used a non-outlet as `source`
- Unanswerable with `source` empty on named outlets → teach `source`, not more searches
- 429 / `runtime_error` → wait, re-run the **full** suite. Partial CSVs are not a score.

Do not copy hops/calls text into the prompt.

---

## Loop

1. Snapshot Gather to `project/tests/live_gather_first_hop/inputs/candidate_<name>.md` (and `inputs/control.md` for the starting production file).
2. Edit only `project/src/prompts/gather_agent.md`. Keep it short. One named change per run.
3. Recheck friend-review and the GT-string search.
4. Run the first-hop board. Read the newest `metrics_*.csv` and, on misses, `calls_*.csv`.
5. If 11/11, run again with **no** prompt edit. Two consecutive 11/11 files are the pass.
6. If not, one new named hypothesis. Repeat.

Start from the current `gather_agent.md` (short vendor stub). Do not restore `tests/live_gather_gt/inputs/control.md`.

Do not “fix” gold by editing GT. If first-hop gold is still missing after filters look right, the query is not standalone enough — split or rephrase the **fact**, still without exam wording.

If the decompose and filters are clearly right on most IDs and a few still miss only by model variance, **stop and report** that a stronger chat model is the next lever. Do not keep stuffing the prompt.

---

## When to stop (report, do not widen scope)

Stop prompt work if **any** is true. Do not edit Grade or the production graph.

1. **6 honest first-hop runs** (saved candidate + full `metrics_*.csv` + no leak) and still not two clean 11/11.
2. **Same failure class** on the same live IDs after two dedicated runs with no improvement: packed query, missing `source`, missing dates, or gold miss with filters already set.
3. **Fixing one class breaks another** (for example attaching one named outlet to every call, or splitting one entity into extra empty hops).
4. The only next idea is an exam lookalike.
5. Three honest runs in a 1-point band with the same IDs flipping.

Report: CSV paths, N/11 per candidate, remaining IDs and class, whether first-hop `source` / dates were empty, which rule fired, best clean `candidate_*.md`. Do not recommend Grade, a supervisor, or extra agents.

---

## First message for this chat

Read `project/plans/gate4-gather-first-hop-prompt-goal.md` from the first heading to the end. Follow the friend-review checks. You own only `gather_agent.md`. Build or use the first-hop-only board (one Gather turn, then tools, no Grade). Success is every GT fact chunk in that first batch, with `source` and publication dates on the tool calls when the user named them. Tool `question` strings need not match ground truth. No evaluation text and no lookalikes. 11/11 `first_hop_success` twice, or stop under section “When to stop”.
