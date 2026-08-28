# GOAL — Live Grade 11/11, no leakage

**Status:** Stopped — 9/11. Next spec: [`gate4-standalone-retry-prompt-goal.md`](gate4-standalone-retry-prompt-goal.md)  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/grade_agent.md`

This Grade-only prompt track is closed. Do not resume it. The production Grade file is the 9/11 snapshot [`project/tests/live_grade_gt/inputs/candidate_literal_need_binding.md`](../tests/live_grade_gt/inputs/candidate_literal_need_binding.md). Honest live CSV: `project/tests/live_gather_gt/outputs/metrics_2026-08-28_12-53-03.csv` (9/11, `prompt_leak_hit=0`). Remaining live misses were `too_early` / missing gold on Q01 and Q07. A later candidate (`snippet_states_need`) was 8/11 and broke stop timing (stop rule #3). Two CSVs with `OpenAIConnectionError` (`12-58-15`, `13-00-55`) do not count.

Do not keep editing Grade in isolation. The next job is standalone tool queries on the first hop **and** on every retry.

---

## Friend review — you will be failed for these

1. **Leakage is cheating.** Do not put evaluation-set questions, answers, article titles, snippets, URLs, sub-questions, or “the same question with fake names” into `grade_agent.md`. If the study guide contains the exam, the score is invalid even at 11/11.
2. **No examples of our exam.** `# Examples` is optional and usually wrong here. If you add any, you must invent them yourself in a made-up domain. Do not copy `inputs/cases.json`. If someone who saw the 11 exam questions would recognize the example after you hide the proper nouns, delete it.
3. **Short.** Production `grade_agent.md` must stay **under 40 lines** and **under 350 words**. Cut, do not append.
4. **Vendor shape only.** The chat model is `openai/gpt-4o-mini`. You **must** use OpenAI’s developer-message outline and nothing else:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (optional; prefer none)
   - Do **not** put `# Context` in the file. Runtime state is sent separately as the user message.
5. **Do not use the old template.** Do not keep or translate `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`. Do not paste those bullets under `# Instructions`. Write a short prompt for this model.
6. **Do not invent extra verdict labels.** Code only routes these four strings: `enough`, `rewrite`, `missing_hop`, `empty_stop`.

After every edit, before you run: open `grade_agent.md` and confirm all six checks pass.

---

## What this product is

This is a news-fact answering loop over a local index.

There are three agents. You own **only Grade**.

1. **Gather** (already written, frozen). It may call one tool: `search_facts`. Tool arguments: `question` (required), optional `source`, optional `published_from`, optional `published_to`. It must not answer the user.
2. **Tools** (code). The tool runs. Hits are appended to `evidence`. Each executed search is appended to `prior_queries`.
3. **Grade** (you). No tools. It looks at the question, the evidence so far, and the searches already run. It decides continue or stop.
4. **Answer** (already written, frozen). Runs only after Grade (or Gather) stops. You never touch it.

Loop:

```text
Gather  →  tools  →  Grade  →  continue  →  Gather
                         ↘  stop      →  Answer
```

If Gather emits no tool calls, the graph skips tools and Grade and goes to Answer. You do not handle that case in the prompt.

Hard caps in code (you do not change them): at most 6 Gather LLM turns and 8 tool calls. Hitting a cap forces stop even if Grade wanted to continue.

---

## What Grade receives (this is the state)

Graph state after each tools batch includes:

| Field | What it is |
|---|---|
| `question` | The original user question. Never changes. |
| `evidence` | All retrieved items so far (this run only). Grows after every tools batch. |
| `prior_queries` | All searches already executed. Grows after every tools batch. |
| `gather_count` | How many Gather LLM turns happened. |
| `tool_count` | How many tool calls happened. |
| `grade_verdict` | Last Grade label. Empty on the first Grade visit. |

Grade’s Python consumer sends **only** this JSON as the user message (not the rest of the chat history):

```json
{
  "question": "<original question>",
  "evidence": [
    {
      "article_title": "...",
      "snippet": "...",
      "url": "...",
      "published_at": "...",
      "match_percentage": 0
    }
  ],
  "prior_queries": [
    {
      "question": "...",
      "source": "...",
      "published_from": "...",
      "published_to": "..."
    }
  ]
}
```

Important facts about that JSON:

- `evidence` items **do not have a `source` field**. If the question named an outlet, you may infer the outlet only from `url` or `article_title`.
- `prior_queries` is the memory of searches already tried, including `source` and date filters when they were used. Use it so you do not ask for the same search string again.
- The frozen fixtures in `tests/live_grade_gt/inputs/cases.json` are **already after one or more searches**. That is on purpose: you must decide stop vs continue mid-loop, not only on the first hop.

Do not write this JSON into `grade_agent.md`. The consumer already sends it.

---

## What Grade must return

Structured object (the schema is already bound in code):

- `verdict`: one of `enough` | `rewrite` | `missing_hop` | `empty_stop`
- `note`: a short next-search hint when continuing; empty when stopping

What the labels mean:

| Verdict | Route | When |
|---|---|---|
| `enough` | stop | Every distinct information need in the question has a covering hit in `evidence`. |
| `empty_stop` | stop | The named needs were already searched (`prior_queries`) and the hits cannot support an answer. More search will not help. |
| `rewrite` | continue | A need was searched, but the hits do not cover it. Hint a **different** wording and/or pass a named outlet as `source` / named dates as `published_from` and `published_to`. Never repeat a string already in `prior_queries`. |
| `missing_hop` | continue | A named need, outlet, or date window was not searched yet. |

Covering hit: an evidence snippet that actually supports that need. A named outlet is covered only if an evidence `url` or `article_title` belongs to that outlet.

If some needs are covered and another named need is not, you must continue (`rewrite` or `missing_hop`). Do not stop.

If every named need is covered, you must stop even if another search might find a related extra article.

If the named needs were searched and nothing covers them, you must stop (`empty_stop`). Do not keep rephrasing forever.

`note` is shown to Gather as a short user message only on continue. Keep it a hint, not an answer to the user.

---

## Your job

Get **11/11** on the live Gather+Grade loop against local ground truth, with **zero data leakage** in the Grade prompt.

You do that by editing **only** `project/src/prompts/grade_agent.md`.

Gather’s prompt is frozen. Retrieval is already good when the tool is called with the right query. If gold is missing on the live board, either Grade stopped too early, Grade’s `note` repeated a failed query, or Gather ignored a good hint — you may only teach Grade (general habits, not exam rows).

**Pass (the only pass):** two consecutive newest files from `project/tests/live_gather_gt/outputs/metrics_*.csv`, same Grade prompt, `gather_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor shape, ≤40 lines / ≤350 words, no exam lookalikes.

`gather_success=1` means:

- `unanswerable=0`: every gold URL and gold sentence is in evidence, and `stop_verdict=on_time`
- `unanswerable=1`: `facts_call_count` equals `required_facts_calls`, and `on_time`

Same-turn parallel tool calls are `on_time`. A later Gather turn that still searches after gold is complete is `too_late`. Stopping while a retrievable gold hop is missing is `too_early`.

There is also a cheap Grade-only board. It does **not** count as 11/11. Use it first so you do not burn the live 11-question run on a Grade that never stops or never continues.

---

## Leakage check (do this yourself)

After each edit, search `grade_agent.md` against `project/src/data/questions.json` and `project/src/data/ground_truth/*.json`. If any full question, fact sentence, article title, URL, or sub-question from those files appears in the prompt, you leaked. Delete it.

Both runners set `prompt_leak_hit=1` when that happens and zero every success flag. That check does not catch lookalike examples. You still have to.

Debugging a failed CSV is allowed. Pasting that row into the prompt is not.

If you want examples in the prompt, invent them yourself. Made-up papers, made-up towns, fake `https://….example/…` URLs. Do not copy the isolation cases. Do not clone the exam.

---

## In / out

**Edit:**

- `project/src/prompts/grade_agent.md`
- snapshots `project/tests/live_grade_gt/inputs/candidate_<name>.md`

**Do not edit:**

- Gather prompt, Answer prompt, any other prompt
- GT JSON, `questions.json`, `answers.json`
- agents, tools, services, repositories, orchestration, `conts.py`
- both runners, `cases.json`, live Gather inputs
- vector stores

Do not add agents. Do not change the graph. Do not bind `search_corpus`. Do not run e2e, oracle-Answer, or retrieval tests.

---

## Files you run

Always from the inner `project/` folder.

Needs `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`. The live 11-question run also needs `OPENAI_EMBEDDING_MODEL` and `vector_stores/facts_chroma`.

No console print. Read the newest CSV.

### 1) Cheap Grade board (mid-loop stop/continue)

Frozen invented states, already after several searches. Calls Grade only. No Gather, no Chroma.

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_gt.run_live_grade_gt
```

Writes `project/tests/live_grade_gt/outputs/metrics_YYYY-MM-DD_HH-MM-SS.csv`.

Columns:

| Column | Meaning |
|---|---|
| `case_id` | Fixture name |
| `expected_route` | `stop` or `continue` |
| `predicted_verdict` | Model label |
| `predicted_route` | `stop` if verdict is `enough` or `empty_stop`; `continue` if `rewrite` or `missing_hop` |
| `route_match` | 1 if route matches |
| `note_repeats_prior` | 1 if `note` equals a prior search question |
| `prompt_leak_hit` | 1 if the Grade prompt contains exam strings |
| `case_success` | 1 if route matches, no leak, and a continue case did not repeat a prior query in `note` |
| `note` | Model hint (debug only; do not paste into the prompt) |
| `runtime_error` | Empty on success |

You want `case_success=1` on every row and `prompt_leak_hit=0`.

What the fixtures test (invented domain, not the exam):

- Both named outlets already covered → **stop**
- Named outlets already searched, hits are unrelated → **stop**
- Second named outlet never searched → **continue**
- Named outlet searched but the hit URL is the wrong site → **continue**
- Needs already covered, an extra later search added noise → **stop** (do not keep going)
- A dated second event still missing after a repeated search string → **continue**, and `note` must not repeat that string

Do not edit `cases.json` to match a weak prompt. Change the prompt.

### 2) Real exam board (this is 11/11)

Live Gather + tools + Grade against the 11 local-GT questions. No Answer step.

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_gt.run_live_gather_gt
```

Several minutes. Writes three files in `project/tests/live_gather_gt/outputs/`:

| File | Use |
|---|---|
| `metrics_*.csv` | Scoreboard. `gather_success` is the score. Count the `1`s. That is N/11. |
| `hops_*.csv` | Per gold hop: URL/snippet in evidence or not. Debug only. |
| `calls_*.csv` | Each `search_facts` call (query, `source`, dates). Debug only. |

On `metrics_*.csv` also look at:

- `stop_verdict`: `on_time` / `too_early` / `too_late` / `budget_forced` / `runtime_error`
- `url_recall` / `snippet_recall` / `gold_complete`
- `facts_call_count` vs `required_facts_calls` (unanswerable rows must be equal)
- `gt_source_required_count` vs `agent_source_call_count`
- `gt_dated_required_count` vs `agent_dated_call_count`
- `extra_turn_after_gold`
- `prompt_leak_hit` (must stay 0)
- `runtime_error` (must stay empty)

How to read a miss (teach a **general** habit, not that row):

- Gold missing + `too_early` → Grade stopped while a need was still uncovered, or it continued with a useless repeated `note`.
- Gold complete + `too_late` → Grade did not stop after the needs were covered.
- Unanswerable + `too_late` → Grade kept searching after the named needs were already tried.
- Unanswerable + `too_early` → Grade stopped before the required searches ran (less common; Gather may have under-called).
- `budget_forced` → the loop hit 6/8 caps. Grade should have stopped or given a different hint earlier.
- 429 / `runtime_error` → wait, re-run the **full** suite. Do not ship a partial CSV as a score.

Do not copy hops/calls text into the prompt.

---

## Loop

1. Snapshot the current `grade_agent.md` to `project/tests/live_grade_gt/inputs/candidate_<name>.md`.
2. Edit only `project/src/prompts/grade_agent.md`. Keep it short. One named change per run.
3. Recheck the friend-review list and the GT-string search.
4. Run the cheap Grade board. Read the newest `tests/live_grade_gt/outputs/metrics_*.csv`.
5. If every `case_success` is 1 and leak is 0, run the live 11-question board. Read the newest `tests/live_gather_gt/outputs/metrics_*.csv`.
6. If live is 11/11, run live again with **no** prompt edit. Two consecutive 11/11 files are the pass.
7. If live is not 11/11, inspect hops/calls, change one general Grade rule, snapshot, repeat.

Start from the current `grade_agent.md`. It is already a short vendor stub. `inputs/control.md` is that starting snapshot.

Do not switch Gather. Do not “fix” gold by editing GT.

---

## When to stop (report, do not widen scope)

Stop prompt work if **any** is true. Do not edit the graph. Report and finish.

1. **6 honest live runs** (saved candidate + full live `metrics_*.csv` + no leak) and still not two clean 11/11.
2. **Same failure class** on the same live IDs after two dedicated runs with no improvement: missing gold, `too_late`, `too_early`, or `budget_forced`.
3. **Fixing one class breaks another** (for example continue-for-coverage makes unanswerable rows `too_late`).
4. The only next idea is an exam lookalike.
5. Three honest live runs in a 1-point band with the same IDs flipping.

Report: CSV paths, N/11 per candidate, remaining IDs and class, which rule fired, best clean `candidate_*.md`. Do not recommend a supervisor, a planner-before-search, or extra agents.

---

## First message for this chat (historical; do not start a new chat from this file)

The active spec is [`gate4-standalone-retry-prompt-goal.md`](gate4-standalone-retry-prompt-goal.md). The original Grade-only first message is kept below for the record.

Read `project/plans/gate4-live-grade-prompt-goal.md` from the first heading to the end. Follow the friend-review checks. You own only `grade_agent.md`. Keep it short and OpenAI-shaped. No evaluation text and no lookalikes. Use the cheap Grade board for mid-loop stop/continue, then the live Gather board for 11/11 `gather_success` twice, or stop under section “When to stop”.
