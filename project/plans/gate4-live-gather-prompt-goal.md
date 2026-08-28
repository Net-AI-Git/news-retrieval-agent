# GOAL — Live Gather 11/11, no leakage

**Status:** Prompt track stopped at 7/11 (rules #2 and #5). Grade is now in the graph. Re-run live Gather against production prompts; do not resume prompt-only looping unless Grade also stalls.  
**Author:** N/A  
**Created:** 2026-08-27  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/gather_agent.md`

This file is the only spec. Do not read other plans for prompt wording. Do not copy the old Gather template.

---

## Friend review — you will be failed for these

A previous attempt was rejected. Do not repeat it.

1. **Leakage is cheating.** Do not put our evaluation questions, their answers, their article titles, their snippets, their URLs, or “the same question with fake names” into `gather_agent.md`. If the study guide contains the exam, the score is invalid even at 11/11.
2. **No examples of our questions.** `# Examples` is optional and usually wrong here. If you add any, invent them yourself in a made-up domain. If someone who saw the 11 questions would recognize the example after you hide the proper nouns, delete it.
3. **Short.** The production Gather prompt must stay **under 40 lines** and **under 350 words**. Cut, do not append.
4. **Vendor shape only.** Model is `openai/gpt-4o-mini`. Use OpenAI’s developer-message outline and nothing else:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (optional; prefer none)
   - Do **not** put `# Context` in the file. The graph already sends the user question and tool results as messages.
5. **Delete our old prompt rules.** Do not keep or translate `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`. Do not paste those bullets under `# Instructions`. Write a new short prompt for this model.

After every edit, before you run: open `gather_agent.md` and confirm all five checks pass.

---

## Job

Two agents exist. You own **only** Gather (`project/src/prompts/gather_agent.md`).

Gather has one tool, `search_facts` (`question`, optional `source`, optional `published_from` / `published_to`). It must search, then stop. It must not answer the user.

Answer is already done. Do not edit it. Do not run e2e / oracle-Answer / GT-query retrieval tests.

The runner runs live Gather (no Answer) against the local index. The index is already good on the GT queries. If gold is missing, the agent query is wrong — not Chroma.

**Pass:** two consecutive newest `metrics_*.csv` files, same prompt, `gather_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor shape, ≤40 lines / ≤350 words, no exam lookalikes.

`gather_success=1` means:

- `unanswerable=0`: every gold URL and gold sentence is in evidence, and `stop_verdict=on_time`
- `unanswerable=1`: `facts_call_count` equals `required_facts_calls`, and `on_time`

Parallel tool calls in one turn are `on_time`. A later turn that still searches after gold is complete is `too_late`.

---

## Leakage check (do this yourself)

After each edit, search `gather_agent.md` against `project/src/data/questions.json` and `project/src/data/ground_truth/*.json`. If any full question, fact sentence, article title, URL, or sub-question from those files appears in the prompt, you leaked. Delete it.

The runner also sets `prompt_leak_hit=1` when that happens and zeros every `gather_success`. That check does not catch lookalike examples. You still have to.

Debugging a failed CSV is allowed. Pasting that row into the prompt is not.

---

## In / out

**Edit:** `project/src/prompts/gather_agent.md` and snapshots `project/tests/live_gather_gt/inputs/candidate_<name>.md`.

**Allowed one-line test fix:** if `tests/grounded_answering/test_grounded_answering.py` still expects `[INSTRUCTIONS]` on Gather, change only the Gather asserts in `test_prompts_exist_and_require_verbatim_snippet` to `# Identity` / `search_facts` and to forbid the old headings. Do not touch the live Q01/Q07/Q09 tests.

**Do not edit:** GT JSON, Answer, retrieval, tools, orchestration, `conts.py`, the runner, `answers.json`, other prompts.

---

## Run (from inner `project/`)

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_gt.run_live_gather_gt
```

Needs `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`) and `vector_stores/facts_chroma`. Several minutes. No console print. Look at the newest files in `project/tests/live_gather_gt/outputs/`:

- `metrics_*.csv` — scoreboard (`gather_success` is the score)
- `hops_*.csv` / `calls_*.csv` — debug only; do not copy them into the prompt

If `url_recall` is low, inspect `calls_*.csv` (`source` / dates / query). Teach a **general** habit, not that row.

If gold is complete but `too_late`, teach stopping, not that row.

429 → `runtime_error`. Wait and re-run the full suite.

---

## Loop

1. Snapshot to `inputs/candidate_<name>.md`.
2. Edit only `gather_agent.md`. Keep it short. One change per run.
3. Recheck the friend list and the GT-string search.
4. Run the command. Read the newest `metrics_*.csv`.
5. If 11/11, run again with no edit.

Start from the current file. It is already a short vendor stub. Do not restore `inputs/control.md` (that is the rejected old template).

---

## When to stop (architecture, not more prompt)

Stop prompt work if **any** is true. Do not build the new graph. Report and finish.

1. **6 honest runs** (saved candidate + full CSV + no leak) and still not two clean 11/11.
2. **Same failure class** on the same IDs after two dedicated runs with no improvement: missing gold (`url_recall`/`snippet_recall`), missing filters (`source`/dates vs `gt_*` columns), `too_late`, or `too_early`.
3. **Fixing one class breaks another.**
4. The only next idea is an exam lookalike.
5. Three honest runs in a 1-point band with the same IDs flipping.

Report: CSV paths, N/11 per candidate, remaining IDs and class, which rule fired, best clean `candidate_*.md`. Recommend a **Grade node after tools** (`enough` / `rewrite` / `missing_hop` / `empty_stop`) routed in code. Do not recommend a supervisor, a planner-before-search, or extra agents.

---

## First message for the other chat

Read `project/plans/gate4-live-gather-prompt-goal.md` from the first heading to the end. Follow the friend-review checks. Write a short OpenAI-shaped Gather prompt. No evaluation questions and no lookalikes. 11/11 `gather_success` twice, or stop under section “When to stop”.
