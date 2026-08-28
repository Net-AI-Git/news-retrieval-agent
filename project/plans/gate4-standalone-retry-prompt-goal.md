# GOAL — Standalone queries and new wording on retry, 11/11, no leakage

**Status:** Stopped — 9/11 still best for Gather+Grade. Do not resume. Gather-only first-hop spec: [`gate4-gather-first-hop-prompt-goal.md`](gate4-gather-first-hop-prompt-goal.md)  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/gather_agent.md project/src/prompts/grade_agent.md`

This file is the **only** spec. Do not read other plans for prompt wording. Do not copy old prompt templates.

---

## Friend review — you will be failed for these

1. **Leakage is cheating.** Do not put evaluation-set questions, answers, article titles, snippets, URLs, sub-questions, or “the same question with fake names” into `gather_agent.md` or `grade_agent.md`. If the study guide contains the exam, the score is invalid even at 11/11.
2. **No examples of our exam.** `# Examples` is optional and usually wrong. If you add any, invent them yourself in a made-up domain. Do not copy `tests/live_grade_gt/inputs/cases.json`. If someone who saw the 11 exam questions would recognize the example after you hide the proper nouns, delete it.
3. **Short.** Each production prompt must stay **under 40 lines** and **under 350 words**. Cut, do not append.
4. **Vendor shape only.** Model is `openai/gpt-4o-mini`. You **must** use this outline and nothing else:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (optional; prefer none)
   - Do **not** put `# Context` in the file. Runtime data is sent as the user message.
5. **Do not use the old template.** Do not keep or translate `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`.
6. **Do not invent extra Grade verdicts.** Code only routes `enough`, `rewrite`, `missing_hop`, `empty_stop`.

After every edit, before you run: open both prompt files and confirm all six checks pass.

---

## What this product is

News-fact answering over a local index. Retrieval is already good when `search_facts` gets a **standalone** query (one information need) plus the named `source` / date filters. The same query string with Top-1 returns the same chunk. Repeating a failed question cannot find a missing gold hop.

Loop:

```text
Gather  →  tools  →  Grade  →  continue  →  Gather
                         ↘  stop      →  Answer
```

- **Gather** has one tool: `search_facts` (`question` required; optional `source`, `published_from`, `published_to`). It must not answer the user.
- **Grade** has no tools. It sees `{question, evidence, prior_queries}` and returns `verdict` + `note`. Continue is `rewrite` or `missing_hop`. Stop is `enough` or `empty_stop`. On continue, `note` is appended as a HumanMessage for the next Gather turn.
- **Answer** is frozen. You never touch it.

Caps (do not change): 6 Gather LLM turns, 8 tool calls. Hitting a cap forces stop.

`evidence` items have **no** `source` field. Infer outlet from `url` or `article_title`. `prior_queries` lists every executed search: `{question, source, published_from, published_to}`.

---

## Your job

Get **11/11** live Gather+Grade vs local ground truth, with **zero leakage** in both prompts.

You own **two** files:

- `project/src/prompts/gather_agent.md` — how the tool is called
- `project/src/prompts/grade_agent.md` — when to continue, and what the next search should be

Start from the files on disk. Grade’s current text is the 9/11 snapshot. Do not restore rejected templates.

**Pass:** two consecutive newest `project/tests/live_gather_gt/outputs/metrics_*.csv`, same pair of prompts, `gather_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor shape, length limits, no exam lookalikes.

`gather_success=1` means:

- `unanswerable=0`: every gold URL and gold sentence is in evidence, and `stop_verdict=on_time`
- `unanswerable=1`: `facts_call_count` equals `required_facts_calls`, and `on_time`

Same-turn parallel calls are `on_time`. A later Gather turn that still searches after gold is complete is `too_late`. Stopping while a retrievable gold hop is missing is `too_early`.

---

## What you must teach (general habits, not exam rows)

### 1) First-hop tool calls (Gather)

For each independently verifiable need in the user question, one standalone `search_facts` call:

- The `question` argument is that need alone: named entities, event, and time scope that belong to the **fact**, not a packed copy of the whole user question.
- If the user named an outlet, pass it as `source`, not only inside the question text.
- If the user named a **publication** window, pass `published_from` / `published_to` as ISO-8601. A date that is part of the event stays in the question text; do not turn it into a filter unless the user restricted when the article was published.
- Independent needs go in the same Gather turn (parallel).

### 2) Every retry must be a **new** standalone query (Gather + Grade)

The index will not move if you send the same `question` string again.

When Grade continues:

- `note` must not equal any `prior_queries.question`.
- `note` is a short hint for the **uncovered need only**: a new standalone question, plus `source` / dates when the user already named them and they were missing or unused.
- Gather’s next `search_facts` must follow that hint **and** still be a well-formed tool call. Do not paste the previous `question` argument again.

If a need was searched and the hit does not cover it, rewrite the standalone question (different wording and/or the missing filter). Do not “try the same sentence once more”.

If every need is covered, stop (`enough`). If named needs were searched and hits are unrelated, stop (`empty_stop`). Do not hunt forever.

---

## Leakage check (do this yourself)

After each edit, search **both** prompt files against `project/src/data/questions.json` and `project/src/data/ground_truth/*.json`. Any full question, fact sentence, article title, URL, or sub-question from those files is a leak. Delete it.

The live runner flags `prompt_leak_hit=1` on exam strings in Gather **or** Grade and zeros every `gather_success`. Lookalikes are still on you.

Debugging a CSV is allowed. Pasting that row into a prompt is not.

If you want examples, invent them. Made-up outlets, towns, fake `https://….example/…` URLs.

---

## In / out

**Edit:**

- `project/src/prompts/gather_agent.md`
- `project/src/prompts/grade_agent.md`
- snapshots `project/tests/live_gather_gt/inputs/candidate_<name>.md` (Gather)
- snapshots `project/tests/live_grade_gt/inputs/candidate_<name>.md` (Grade)

**Do not edit:**

- Answer prompt, any other prompt
- GT JSON, `questions.json`, `answers.json`
- agents, tools, services, repositories, orchestration, `conts.py`
- runners, `cases.json`
- vector stores

Do not add agents. Do not change the graph. Do not bind `search_corpus`. Do not run e2e, oracle-Answer, or retrieval tests.

One **named hypothesis** per run. You may change Gather, Grade, or both in that run if they are the same hypothesis (for example “retry must be a new standalone query”). Do not mix two unrelated ideas in one live CSV.

---

## Files you run

Always from the inner `project/` folder.

Needs `.env`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`. Live also needs `OPENAI_EMBEDDING_MODEL` and `vector_stores/facts_chroma`.

These runners send evaluation payloads to OpenRouter. That is expected. No console print. Read the newest CSV.

If `uuid_utils` fails to import on this machine, prefix the `uv run python -m …` with the same `uuid_utils.compat.uuid7` shim already used on this workspace.

### 1) Cheap Grade board (stop/continue + note must not repeat)

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_gt.run_live_grade_gt
```

Writes `project/tests/live_grade_gt/outputs/metrics_*.csv`.

You want every row `case_success=1` and `prompt_leak_hit=0`. Continue cases must not put a prior query string in `note`.

This is not 11/11. Use it after a Grade edit, before burning the live 11-question run. Do not edit `cases.json` to match a weak prompt.

### 2) Live exam board (this is 11/11)

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_gt.run_live_gather_gt
```

Several minutes. Writes `project/tests/live_gather_gt/outputs/`:

| File | Use |
|---|---|
| `metrics_*.csv` | Scoreboard. Count `gather_success=1`. That is N/11. |
| `hops_*.csv` | Which gold URL/snippet is in evidence. Debug only. |
| `calls_*.csv` | Every `search_facts` call: `gather_turn`, `question`, `source`, dates. Debug only. |

On `metrics_*.csv` also look at `stop_verdict`, `url_recall` / `snippet_recall` / `gold_complete`, `facts_call_count` vs `required_facts_calls`, `gt_source_required_count` vs `agent_source_call_count`, `gt_dated_required_count` vs `agent_dated_call_count`, `extra_turn_after_gold`, `prompt_leak_hit`, `runtime_error`.

On `calls_*.csv` look for:

- First-turn queries that are packed or missing `source` / dates the user named
- A later `gather_turn` whose `question` is the same string as an earlier call (this is the retry bug)
- A retry that still omits a named `source` / date filter

How to read a miss (teach a **general** habit, not that row):

- Gold missing + `too_early` → Grade stopped, or the first-hop queries were not standalone / missing filters
- Gold missing after a later turn + **same** `question` in `calls_*.csv` → retry did not rephrase; fix wording, not “search again”
- Gold complete + `too_late` → Grade did not stop after coverage
- Unanswerable + `too_late` → extra searches after the required empty hops
- 429 / `runtime_error` → wait, re-run the **full** suite. Partial CSVs are not a score.

Do not copy hops/calls text into a prompt.

---

## Loop

1. Snapshot Gather and/or Grade to the matching `inputs/candidate_<name>.md`.
2. Edit only the prompt(s) for this hypothesis. Keep them short.
3. Recheck friend-review and the GT-string search on **both** files if either changed.
4. If Grade changed: run the cheap Grade board. Require 6/6 `case_success` and leak 0.
5. Run the live 11-question board. Read newest `metrics_*.csv` and, on misses, `calls_*.csv`.
6. If live is 11/11, run live again with **no** prompt edit. Two consecutive 11/11 files are the pass.
7. If not, one new named hypothesis. Repeat.

Do not “fix” gold by editing GT.

---

## When to stop (report, do not widen scope)

Stop prompt work if **any** is true. Do not edit the graph.

1. **6 honest live runs** (saved candidate + full live `metrics_*.csv` + no leak) and still not two clean 11/11.
2. **Same failure class** on the same live IDs after two dedicated runs with no improvement.
3. **Fixing one class breaks another.**
4. The only next idea is an exam lookalike.
5. Three honest live runs in a 1-point band with the same IDs flipping.

Report: CSV paths, N/11 per candidate, remaining IDs and class, whether `calls_*.csv` shows repeated `question` strings on later turns, which rule fired, best clean `candidate_*.md` pair. Do not recommend a supervisor, a planner-before-search, or extra agents.

---

## Stopped report — 2026-08-28

Stop rule **#5** (also **#3** on run 1). Production rolled back to the 9/11 pair. Do not resume this spec.

| Candidate | Live CSV | N/11 | Misses |
|---|---|---:|---|
| Grade `literal_need_binding` + Gather `standalone_needs` (best) | `metrics_2026-08-28_12-53-03.csv` | 9 | Q01, Q07 `too_early` |
| `standalone_source_retry` (cartesian source) | `metrics_2026-08-28_13-56-28.csv` | 7 | Q04 `too_late`; Q05 `budget_forced` (Age on every fact, repeated queries); Q07 `too_early`; Q08 `too_early` (date-only window) |
| `publisher_scoped_retry` | `metrics_2026-08-28_14-00-29.csv` | 7 | Q02 `budget_forced` (identical retry string, no `source`); Q06 `too_late`; Q07 `too_early`; Q08 `too_early` |
| `outlet_day_retry` | `metrics_2026-08-28_14-04-33.csv` | 7 | Q02 `too_early` (no `source`, no retry); Q07 `too_early` (packed + featured-in yes/no); Q08 `too_late` after gold; Q09 `too_late` |

Repeated `question` on later `gather_turn`: Q02 in `14-00-29`; Q05 in `13-56-28`; Q08 turns 5–6 in `14-04-33`. Grade edits that forced unused-filter continue failed the cheap board 3/6 (`13-50-29`, `13-52-16`, `13-53-55`). Restored Grade cheap 6/6: `metrics_2026-08-28_13-55-22.csv`.

Best clean pair: `tests/live_gather_gt/inputs/candidate_standalone_needs.md` + `tests/live_grade_gt/inputs/candidate_literal_need_binding.md`.

---

## First message for this chat (historical; do not start a new chat from this file)


Read `project/plans/gate4-standalone-retry-prompt-goal.md` from the first heading to the end. Follow the friend-review checks. You own `gather_agent.md` and `grade_agent.md`. First-hop tool calls must be standalone needs with the named filters. Every retry must be a new standalone query, not the same string. No evaluation text and no lookalikes. Cheap Grade board after Grade edits, then live Gather board for 11/11 `gather_success` twice, or stop under section “When to stop”.
