# GOAL — Retrieve isolated hop, 11/11 against GT, without leakage

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/retrieve_agent.md`

This file is **the only spec** of this chat. Do not read other plans for prompt wording. Do not copy old prompt templates. Do not use `tests/live_gather_first_hop` or `tests/live_gather_gt` as the scoreboard.

---

## Friend review — you fail if you do these

1. **Leakage is cheating.** Must not put inside `retrieve_agent.md` questions from the evaluation set, answers, article titles, fact snippets, URLs, sub-questions, `question` strings of a tool from the GT, or “the same question with fake names”. If the study material contains the test, the score is invalid even at 11/11.
2. **No examples from our test.** `# Examples` is optional and usually a mistake. If you add examples — invent them yourself, in a fictional domain. If someone who saw the 11 test questions would recognize the example after hiding proper names — delete it.
3. **Short.** Production `retrieve_agent.md` must stay **under 40 lines** and **under 350 words**. Shorten, do not add without deleting.
4. **Vendor structure only.** The model is `openai/gpt-4o-mini`. **Must** use this outline and only it:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (optional; better without)
   - **Must not** put `# Context` in the file. The isolated sub-question is sent as a user message.
5. **No old template.** Do not leave and do not translate `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`. Do not use Claude XML tags as the main outline (`<role>`, `<decision_policy>`).
6. **Do not teach ranking or a newspaper's canonical name.** Catalog names and top-k are not this agent. Teaching “always emit Sporting News exactly” or pasting gold facts is leakage and also out of scope.

After every edit, before a run: open `retrieve_agent.md` and verify that these six checks pass.

---

## What this product is (you have no prior context)

This repo answers questions from news facts in a local index. The answering loop is split into agents:

- **Gather** — breaks the full user question into independent sub-questions. **Not yours.**
- **Retrieve** — **this is yours.** Sees **one sub-question**. Fills **one call** to `search_facts`.
- **Tools / Chroma / ranking** — run after Retrieve. **Not yours.**
- **Grade / Answer** — afterward. **Not yours.**

Arguments of `search_facts`:

- `question` (required) — the search string
- `source` (optional) — newspaper name, only when this sub-question names a newspaper
- `published_from` / `published_to` (optional) — **publication** date window in ISO-8601

Retrieve's runtime code already exists. You change only the prompt file.

```text
project/src/agents/retrieve_agent.py
```

What this file already does (do not edit it):

- loads `project/src/prompts/retrieve_agent.md` as the system message
- sends `HumanMessage(task_data["sub_question"])` — **only** that string
- binds the `search_facts` tool with `tool_choice="search_facts"` (exactly one call)
- uses `OPENAI_MODEL` (`openai/gpt-4o-mini`), `temperature=0`, `seed=151`

Because the user message is only the isolated sub-question, a newspaper that appears in a sibling hop **cannot** appear in this hop — unless **you** put it in the prompt. Therefore leakage in the prompt also breaks isolation.

---

## Your task

Reach **11/11** on the Retrieve-only board, twice in a row, with **zero data leakage**.

There are 11 local GT questions (`Q01` … `Q11`) under `project/src/data/ground_truth/`, according to the schema in `project/src/data/ground_truth/README.md`. The board **does not** send the parent question. For each question it takes only `expected_tool_calls` rows where `agent` is `"retrieve"`. The input to Retrieve is the isolated sub-question from `sub_questions` by `sub_question_index` (if missing — `arguments.question`). Rows `agent: "unbound"` (`search_corpus` in Q04/Q09) do not enter this board.

**Meeting the goal:** the two newest `metrics_*.csv` files in a row, the same Retrieve prompt, `retrieve_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor structure, length limits, no test text and no lookalikes.

`retrieve_success=1` on a question means that **all** of the question's isolated hops passed:

- exactly one tool call, name `search_facts`
- `question` is a literal copy of the input string (after whitespace normalization). Keeps the user's verbs and names. Do not rewrite, do not summarize, do not “improve”
- if the hop in the GT has `source`: the agent's `source` is not empty, copied **from this string** (short token; spelling errors allowed), and matches the newspaper — not a person / company / product / topic from the same string
- if the hop in the GT has no `source`: the agent omits `source` (empty)
- if the hop in the GT has `published_from` / `published_to`: the agent fills both, ISO-8601 with explicit UTC offset, the same calendar day as in the GT. The desired form: start `T00:00:00+00:00`, end `T23:59:59+00:00`. Midnight without offset fails
- if the hop in the GT has no publication window: the agent omits both date fields. Event dates stay inside `question`
- the model does not answer the user (no non-empty assistant text)
- the prompt leak scan is 0

**Not measured (do not chase this):**

- URL / gold sentence / place 1 in Chroma
- canonical name in the catalog (the newspaper's full name vs a short token from the string). Canonicalization is `run_resolve_source` in code: exact → unique substring → embedding; if unresolved — no source filter in Chroma
- Top-k / ranking. Q01 with a full `source` from a newspaper in the string and the gold not rank 1 is a retrieval problem, not a Retrieve prompt failure on this board
- Gather packing (two newspapers in one string). This board already feeds split hops from the GT. Do not edit Gather to “help” Retrieve

---

## What to teach in the prompt (general habits, not test rows)

Teaches habits. Does not teach the 11 questions.

- One isolated sub-question goes in, one `search_facts` comes out. Never answers.
- Copies the input string to `question`. Does not add the parent question. Does not add sibling hops. Does not nest entities inside `question`.
- A **newspaper** that appears in **this** string → `source` = a short token from this string. Spelling errors allowed. If this string has no newspaper → omit `source`.
- Must not put a person, company, product, topic, or a generic marker like “news outlet” in `source`. A company or stock-exchange name in the text is not a newspaper.
- A **publication window** that appears in this string (when the article was published) → `published_from` / `published_to` that cover the calendar day in ISO-8601 with UTC offset. Dates that are part of the event stay only in `question`.
- Does not invent a newspaper that is not in this string. Does not copy a newspaper from an example in the prompt onto a hop that did not name a newspaper.

---

## Prompt structure per the vendor (must stick to this)

File: `project/src/prompts/retrieve_agent.md`  
Language: English only.  
No Python, YAML, JSON, Jinja, env lookups, or secrets in the prompt file.

The exact outline:

```markdown
# Identity
...

# Instructions
...

# Examples
<user_query>
...
</user_query>
<assistant_response>
...
</assistant_response>
```

`# Examples` optional. Better without. If included — exactly these two tags. Context is not written into the file; the run sends the sub-question as a user message.

Start from the current production file. Do not restore `tests/live_gather_gt/inputs/control.md` or any Gather prompt.

---

## If you want examples — search and build them yourself

This document does not give example bodies. Do not copy hops from the GT. Do not duplicate the 11 questions with swapped names.

The allowed way:

1. Read `project/src/prompts/AGENTS.md` only for the vendor's example tags.
2. Invent a fictional domain (fictional town, fictional newspaper, fake `https://….example/…` URLs).
3. Use examples only for **format**: literal copy of the user string to `question`; omitting `source` when there is no newspaper; a short newspaper token when the fictional string names a newspaper; date filters only for a fictional publication window.
4. Delete the example if after hiding proper names it still looks like our test (the same trap: two newspapers and one must not leak into the other hop, a company name mistaken for a newspaper, publication day vs event date).

Prefer zero-shot. A long examples block usually fails the length limit and also the leak risk.

---

## In / out

**Allowed to edit:**

- `project/src/prompts/retrieve_agent.md` (the only production file you change)
- snapshots `project/tests/live_retrieve_gt/inputs/candidate_<name>.md`
- the Status line in `project/tests/live_retrieve_gt/README.md` after a run, if you want

**Forbidden to edit:**

- `gather_agent.md`, `grade_agent.md`, `answer_agent.md`, any other prompt
- `retrieve_agent.py`, Gather / Grade / Answer agents, tools, services, repositories, orchestration, `conts.py`, schemas
- GT JSON, `questions.json`, `answers.json`, `facts.json`
- `tests/live_gather_first_hop`, `tests/live_gather_gt`, `tests/live_grade_gt`, `tests/live_search_facts_gt_calls`
- vector stores, top-k, source catalog, `run_resolve_source`

Do not add agents. Do not bind `search_corpus`. Do not run e2e, oracle-Answer, Grade boards, or the Gather first-hop board as the scoreboard.

**One named** experiment hypothesis per live run.

---

## The board (this is the 11/11)

Always from the inner `project/` folder. In PowerShell:

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_retrieve_gt.run_live_retrieve_gt
```

Need `project/.env`:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL` (`openai/gpt-4o-mini`)

**Does not** need the Chroma store or `OPENAI_EMBEDDING_MODEL`. The board only asks the chat model to fill the tool call. It does not run `search_facts`.

These runs send an evaluation payload to OpenRouter. That is expected. The hop count is the number of `agent: "retrieve"` rows in the current GT (12-second pause between hops). No `print` to the console; success is a new CSV pair.

Do not use:

```text
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
uv run python -m tests.live_gather_gt.run_live_gather_gt
```

These boards mix Gather + retrieval hits. They will punish you for Gather packing and for rank-1 misses that are not the Retrieve contract.

More detail: `project/tests/live_retrieve_gt/README.md`.

---

## Output files — where they go and how to inspect them

Written to:

```text
project/tests/live_retrieve_gt/outputs/
```

Two files per run, the same timestamp:

- `metrics_YYYY-MM-DD_HH-MM-SS.csv` — **one row per question** (11 rows). This is the 11/11 score
- `hops_YYYY-MM-DD_HH-MM-SS.csv` — **one row per Retrieve hop in the GT** (`agent: "retrieve"`). This is the debug file

UTF-8 with BOM (`utf-8-sig`) so Excel will open them. The newest stamp = this run. A partial CSV after a crash is not a score; rerun the whole suite.

### `metrics_*.csv` — how to count 11/11

Open the newest metrics file. Count rows where `retrieve_success` is `1`. That number out of 11 is the score.

| Column | What it means |
| --- | --- |
| `question_id` | `Q01` … `Q11` |
| `hop_count` | how many `agent: "retrieve"` rows the GT has for the question |
| `hops_passed` | how many of them passed. Must equal `hop_count` |
| `retrieve_success` | `1` only if all hops passed **and** `prompt_leak_hit=0` |
| `prompt_leak_hit` | `1` if `retrieve_agent.md` contains a test needle. Then **all** questions fail |
| `rewritten_question_count` | hops that did not copy the input string to `question` |
| `source_fail_count` | hops with missing / extra / wrong `source` |
| `dates_fail_count` | hops with missing / extra / wrong date filter |
| `call_fail_count` | hops that did not emit exactly one `search_facts` |
| `answered_count` | hops that also wrote text to the user |
| `fail_reasons` | unique fail codes on the question |
| `runtime_error` | exception text if the model call crashed |

### `hops_*.csv` — how to debug a miss

Filter to `hop_success=0`. Read `fail_reason`, then compare `sub_question` (what Retrieve saw) against `agent_question` / `agent_source` / `agent_published_*`.

| `fail_reason` | What went wrong | What to teach (general) |
| --- | --- | --- |
| `prompt_leak` | test text found in the prompt | delete. The run is not valid until leakage is 0 |
| `rewritten_question` | `question` is not a copy of the input | teach literal copy; keep verbs and names |
| `source` | missing newspaper, extra `source` when there is no newspaper, token not from this string, or token that is not the named newspaper | teach: newspaper in **this** string → short token from **this** string; otherwise omit; never a person/company/topic |
| `dates` | missing publication window, extra dates on an event-only hop, no UTC offset, or wrong calendar day | teach ISO-8601 with offset; event dates stay in `question` |
| `call_count` / `wrong_tool` | not exactly one `search_facts` | teach one call, do not answer. The run already forces the tool; do not fight this |
| `answered` | non-empty assistant text | teach never answer |
| `runtime_error` | API / import crash | if 429 — wait and rerun the **whole** suite. A partial file is not a score |

Debugging CSV is allowed. Pasting the row into the prompt is forbidden.

### Leak check (also do it yourself)

After every edit, search in `retrieve_agent.md` against `project/src/data/questions.json` and `project/src/data/ground_truth/*.json` (the live files, not an old copy). Any full test question, fact sentence, title, URL, sub-question, or expected `question` string from those files is leakage. Delete.

The runner marks `prompt_leak_hit=1` on these needles (length ≥ 24, skips short answers like Yes/No) and zeros every `retrieve_success`. Lookalikes remain on you.

Allowed to open GT files to understand a miss. Forbidden to copy their wording into the prompt.

---

## The loop

1. Snapshot the current production prompt to `project/tests/live_retrieve_gt/inputs/candidate_<name>.md` (and leave `inputs/control.md` as the starting file).
2. Edit only `project/src/prompts/retrieve_agent.md`. Keep it short. One named change per run.
3. Recheck Friend review and GT string search.
4. Run the Retrieve board. Read the newest `metrics_*.csv`. On misses — read `hops_*.csv`.
5. If 11/11 — run again **without** editing the prompt. Two 11/11 files in a row is meeting the goal.
6. If not — one new named experiment hypothesis. Repeat.

Do not “fix” gold by editing GT. Do not raise `k`. Do not nest newspaper names in the prompt.

If filling is clearly correct on most identifiers and a few still fail only because of model variance (same prompt, hops flip) — **stop and report**. Do not keep stuffing the prompt.

---

## When to stop (report, do not expand scope)

Stop prompt work if **one** of these is true. Do not edit Gather, Grade, Answer, tools, or k.

1. **6 honest runs** of the Retrieve board (saved candidate + full `metrics_*.csv` + no leakage) and still no two clean 11/11.
2. **The same fail type** on the same hop identifiers after two dedicated runs with no improvement: rewritten question, missing `source`, extra `source`, missing dates, extra dates.
3. **Fixing one type breaks another type** (for example filling `source` on every hop, or omitting it on hops that name a newspaper).
4. The only next idea is a test lookalike.
5. Three honest runs within one point of the score with the same identifiers flipping.

In the report: CSV paths, N/11 per candidate, remaining question IDs and `fail_reason`, whether `source` / dates were empty or extra, the best clean `candidate_*.md`. Do not recommend Grade, Gather edits, a supervisor, extra agents, or changing `RETRIEVAL_TOP_K`.

---

## Architecture decisions (closed — honor them)

- Retrieve is a separate agent from Gather. The input is one isolated `HumanMessage(sub_question)`. No parent question, no siblings.
- Retrieve hops in the GT are `expected_tool_calls` rows with `agent: "retrieve"`. `unbound` rows are not part of the task.
- `tool_choice="search_facts"` is production code. The prompt does not try to call other tools or skip the call.
- Catalog canonicalization stays in `run_resolve_source`, not in the prompt.
- Ranking stays in retrieval. This board does not run Chroma.
- The production prompt lives in `prompts/retrieve_agent.md`; the filename matches `retrieve_agent.py`.

---

## The final deliverable

A short `retrieve_agent.md` in vendor structure, that hits **11/11 `retrieve_success` twice** on `tests/live_retrieve_gt` with `prompt_leak_hit=0`, and with snapshots under `tests/live_retrieve_gt/inputs/`. No other production files changed.

---

## Open questions

- none

---

## Opening message for this chat

Read `project/plans/gate4-retrieve-isolated-hop-prompt-goal.md` from the first heading to the end. Go over the Friend review checks. You own only `project/src/prompts/retrieve_agent.md`. Measured only with `tests/live_retrieve_gt` (hops from `expected_tool_calls` with `agent: "retrieve"` in `src/data/ground_truth`, tool filling against GT, no Gather, no Chroma, no `unbound` rows). Success is 11/11 `retrieve_success` twice, without evaluation text and without lookalikes. The tool's `question` must be a literal copy of the isolated sub-question input. `source` only when this string names a newspaper. Publication windows get ISO-8601 filters with UTC offset; event dates stay in `question`. Canonical names and rank-1 are not your job. If you want examples — invent them yourself. Stop according to the section “When to stop”.
