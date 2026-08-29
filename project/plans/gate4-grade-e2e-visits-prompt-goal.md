# GOAL — Grade on real e2e visits, stop on time, no leakage

**Status:** Draft  
**Author:** N/A  
**Created:** 2026-08-29  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/grade_agent.md`

This is **the only spec** of this chat. Do not read other plans for prompt wording. Do not copy old prompt templates. Do not use `tests/live_grade_coverage`, `tests/live_grade_gt`, `tests/live_gather_gt`, or `tests/live_e2e_gt` as the score.

You have no other context. Everything you need is here. Success = **every frozen Grade visit twice**, with **zero data leakage**, with **mandatory synthetic `# Examples`**. **There is no stop rule.** Leakage invalidates the **run**, not the task.

**The only production prompt you may edit is `project/src/prompts/grade_agent.md`.**  
Gather, Retrieve, and Answer stay frozen. Do not touch their prompts.

---

## Friend review — these are what you will fail on

1. **Leakage is cheating.** You must not put in `grade_agent.md` evaluation-set questions, answers, article titles, `facts` / `citations` sentences, URLs, gold sub-questions, tool `question` strings, or «the same question with fake names». If the study material contains the test, the score is invalid even at a perfect board.
2. **`# Examples` is mandatory — synthetic only.** A prompt without `# Examples` is forbidden. At least **three** `<user_query>` / `<assistant_response>` pairs in a made-up domain (or new questions over unused corpus articles that are **not** Q01–Q11 lookalikes). If after hiding proper nouns the example still looks like Q01–Q11 — delete that pair and write another. Do not delete the entire section.
3. **Length is allowed.** The old 40-line / 350-word Grade limit is **cancelled**. Soft ceiling: up to **120 lines** and **1200 words**. If you exceed it, shorten duplications, do not delete `# Examples`.
4. **Vendor structure only.** Grade runs on `openai/gpt-4.1-mini` (`OPENAI_GRADE_AGENT_MODEL`). Outline:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (**mandatory**, at least three synthetic pairs)
   - **Forbidden** `# Context` in the file. Runtime JSON is sent as the user message.
5. **No old template.** Do not leave `[INSTRUCTIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or Claude-style XML as the main outline. Do not restore the cancelled `rewrite` verdict.
6. **The only legal verdicts are `enough`, `missing_hop`, `empty_stop`.** `note` is empty on `enough` and `empty_stop`. On `missing_hop` it is not empty and does not equal any `prior_queries.question`.

After every edit, before a run: open `grade_agent.md` and verify that all six items pass.

---

## What already closed (do not reopen)

Full-system e2e already answers the 11 questions. Gather first-hop gold chunks is closed. Retrieve is closed. Answer on evidence is closed.

Grade is the remaining hole: it **continues after it should stop**.

Honest live e2e (`tests/live_e2e_gt`) with `task_success=100` still shows `grade_success` below 100 because `stop_verdict=too_late`:

| ID | What Grade did in the real loop | What it should have done |
|---|---|---|
| Q06 | `missing_hop` after both gold facts were already in evidence; extra comparison search | `enough` on that first visit |
| Q09 | `missing_hop` after both named outlets were already searched; off-topic hits; more CEO-in-both searches | `empty_stop` on that first visit |
| Q04 | `missing_hop` after both named outlets were already searched; off-topic hits | `empty_stop` (e2e stayed `on_time` only because Gather then emitted an empty list) |
| Q10 | `empty_stop` even though both gold fact sentences were already in evidence | `enough` (route is already stop; still label `enough`) |

Do not chase this by editing Gather, the tool cap, or Q01–Q11 gold. Teach Grade the stop.

---

## What this product is (you have no prior context)

News-fact answering over a local article index. Production loop:

```text
User question
    → Gather     (frozen)   List of independent sub-questions. No tools.
    → Retrieve    (frozen)   One search_facts per string. Copies question, fills source / dates from that string.
    → Tools      (code)     Top-1 chunk per call. Appends to evidence and prior_queries.
    → Grade      (you)      enough / missing_hop / empty_stop
        missing_hop → Gather again, evidence kept
        enough / empty_stop → Answer (frozen) with all accumulated evidence
```

Caps in code (do not change them): 6 Gather LLM turns, 5 tool calls. Hitting a cap forces `empty_stop` even if Grade wanted to continue. Do not rely on the cap. Grade must stop on time **before** the cap.

`GroundedAnsweringState.evidence` and `prior_queries` are append-only (`operator.add`). Grade sees the **full accumulated lists**, not only the last batch.

---

## What Grade is (your only task)

No tools. Never answers the user.

### Input (already sent as the user message — do not write this JSON in the prompt)

```json
{
  "question": "<original user question>",
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

Facts about that JSON:

- `evidence` items have **no** `source` field. Outlet is inferred only from `url` or `article_title`.
- `prior_queries` is every `search_facts` already executed, including `source` and date filters when they were used.
- Evidence is append-only. A non-covering chunk stays. Do not teach Grade to drop chunks.

### Output (already bound in code)

```text
verdict: enough | missing_hop | empty_stop
note: str
```

---

## The three states (habits, not exam rows)

### `enough`

Every distinct **retrievable fact-need** in the question is already covered by a snippet in accumulated evidence. Stop immediately. `note` is empty.

Covering hit: the snippet **explicitly supplies** that need, and if the user bound an outlet to that claim, `url` or `article_title` belongs to that outlet. Topic / keyword overlap is not coverage. A refutation of a yes/no premise **is** coverage.

Important:

- A comparison / «do A and B match» / «featured in both» is **not** a third search need after both sides already have covering snippets. Answer combines evidence. Stop.
- Noise chunks do not block `enough`.
- If the gold fact sentences for the question are already in evidence, stop even if the yes/no wording is not copied verbatim in one snippet.

### `missing_hop`

At least one **required search** has not been run yet, **or** a gold fact-need is still uncovered **and** that need was never searched with its bound outlet / publication-date filter.

`note` is a short next-search hint for the missing need only. It must differ from every `prior_queries.question`. Existing evidence is kept.

### `empty_stop`

Every required named outlet / publication-date filter has already been used in `prior_queries`, the accumulated evidence still cannot support an answer, and a substantially different search will not help. Typical: unanswerable questions whose named outlets were searched and returned off-topic chunks.

Stop. Send all evidence to Answer. `note` is empty.

Do **not** continue for:

- a CEO / name-in-both hop after both named outlets were already searched
- a comparison hop after both sides were already searched
- repeating a prior `question` string
- hoping a second Top-1 from the same query will move

---

## Build the GT (this is part of the job)

The old 12-case file `src/data/ground_truth/grade_coverage.json` is **not** the score. It used invented-ish exam lookalikes and stalled at 9/12.

You freeze a new board from **real Grade I/O** that already happened in the full loop.

### Source

Primary: [`project/output_for_mission/transcripts.json`](../output_for_mission/transcripts.json) — the latest honest 11-question package (matches `tests/live_e2e_gt/outputs/metrics_2026-08-29_16-27-52.csv`).

You may add unique extra visits from other e2e transcripts whose metrics row has `retrieval_success=100` and empty `runtime_error`. Dedup by `(question_id, visit_index, evidence url tuple, prior_queries.question tuple)`. Do not add runtime-error runs.

Do **not** copy Grade's recorded `verdict` as gold. Label what **should** have come out.

### How to reconstruct one visit

Walk each transcript in order. After every `stage: "tools"` there is a Grade visit.

- `question` = the transcript's user question
- `evidence` = **concatenation** of every `tools.evidence` list **up to and including** this tools batch (append-only, same as production)
- `prior_queries` = every `tools.tool_calls[].args` so far, each as `{question, source, published_from, published_to}` with missing fields as `""` (same as `prior_query_records` in orchestration)
- `visit_index` = 1-based Grade visit on that question

The last-batch-only evidence in the transcript tools turn is **not** Grade's input when `visit_index > 1`. Concatenate.

### How to label `expected_verdict`

Read `project/src/data/ground_truth/Q01.json` … `Q11.json` for that `question_id`. Do not edit those files.

Let `gold_facts` = the `facts` array. Unanswerable = `facts` is empty (Q04, Q09).

A gold fact is **covered** when its `url` is in accumulated evidence **and** its `fact` sentence is a substring of some evidence `snippet` (whitespace-normalized).

A required retrieve hop is **searched** when `prior_queries` contains a call whose `source` matches that hop's named outlet (same catalog token the user named). If the hop also has publication dates, those fields must be non-empty on some matching call.

Then, first matching rule:

1. `gold_facts` non-empty **and every gold fact is covered** → `enough`
2. Unanswerable **and** every required named outlet (and named publication window, if any) already appears in `prior_queries` → `empty_stop`
3. A gold fact is uncovered **and** its bound outlet / date filter was never used → `missing_hop`
4. Unanswerable **and** a required named outlet was never searched → `missing_hop`
5. Otherwise, after every required named outlet / date was searched → `empty_stop`

Later visits that should never have happened (Q06 visit 2, Q09 visits 2–4) stay in the board. Label them with the **correct** stop (`enough` or `empty_stop`), not with the model's `missing_hop`. That is how Grade learns to stop even after extra noise was appended.

`expected_note_empty` is true iff the verdict is `enough` or `empty_stop`.

### Case object shape

Write one JSON array to:

```text
project/tests/live_grade_e2e_visits/inputs/cases.json
```

Each object:

```json
{
  "id": "Q06_visit1",
  "question_id": "Q06",
  "visit_index": 1,
  "class": "enough",
  "expected_verdict": "enough",
  "question": "<verbatim from the transcript>",
  "evidence": [],
  "prior_queries": []
}
```

`id` unique. `class` equals `expected_verdict`. Do not retarget a label to fit a weak prompt.

Do **not** put this JSON into `grade_agent.md`.

### Expected first-visit labels on the current transcript (check, do not paste the questions)

| `id` | `expected_verdict` | Why |
|---|---|---|
| `Q01_visit1` … `Q03_visit1`, `Q05_visit1`, `Q07_visit1`, `Q08_visit1`, `Q11_visit1` | `enough` | Gold facts already in the first tools batch |
| `Q04_visit1` | `empty_stop` | Unanswerable; both named outlets already searched |
| `Q06_visit1` | `enough` | Both gold facts already in evidence; no comparison hop |
| `Q06_visit2` | `enough` | Gold still covered after the extra chunk |
| `Q09_visit1` | `empty_stop` | Unanswerable; both named outlets already searched; hits off-topic |
| `Q09_visit2` … `Q09_visit4` | `empty_stop` | Same; extra CEO-in-both searches must not continue |
| `Q10_visit1` | `enough` | Both gold fact sentences already in evidence |

If your reconstruction disagrees with this table, your concat of evidence / prior_queries is wrong. Fix the reconstruction. Do not change Q01–Q11 gold.

---

## The board (this is the score)

New experiment directory (required by `project/tests/AGENTS.md`):

```text
project/tests/live_grade_e2e_visits/
  README.md
  inputs/cases.json
  inputs/control.md          ← snapshot of production grade_agent.md at start
  inputs/candidate_<name>.md
  outputs/metrics_*.csv
  run_live_grade_e2e_visits.py
```

The runner is Grade-only: one `run_grade` invoke per case. No Gather, no Retrieve, no Chroma, no Answer.

Clone the scoring from `tests/live_grade_coverage/run_live_grade_coverage.py`:

- leak-scan `grade_agent.md` against `questions.json`, `Q01.json`–`Q11.json`, **and** the new `cases.json` (needles ≥ 24 chars; skip Yes/No/Insufficient information)
- `case_success=1` when `predicted_verdict == expected_verdict`, `prompt_leak_hit=0`, `runtime_error` empty, stop verdicts have empty `note`, `missing_hop` has nonempty `note` that is not a prior query string
- pause between cases (same 8s as the coverage runner)
- no `print`; newest `outputs/metrics_*.csv` is the score
- UTF-8 with BOM

From inner `project/`:

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_e2e_visits.run_live_grade_e2e_visits
```

Needs `.env`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GRADE_AGENT_MODEL`. Does **not** need Chroma or embeddings.

### Do not run these as your score

- `tests.live_grade_coverage` — old 12 cases, stalled 9/12
- `tests.live_grade_gt` — invented stop/continue, four-verdict history
- `tests.live_gather_gt` / `tests.live_gather_first_hop` / `tests.live_retrieve_gt`
- `tests.live_e2e_gt` — full loop. Not this board. Optional **after** a double pass, never the score

---

## Your task (the only pass)

**Every frozen visit `case_success=1` twice**, same Grade prompt, `prompt_leak_hit=0`, vendor structure, mandatory synthetic `# Examples`, no exam lookalikes.

Edit **only** `project/src/prompts/grade_agent.md` after the board exists.

**Pass:** the two newest consecutive `metrics_*.csv` files under `project/tests/live_grade_e2e_visits/outputs/`, same prompt, `case_success=1` on every row.

---

## What to teach in the prompt (general habits, not exam rows)

Teach these. Do not mention question identifiers in the prompt.

- Split the user question into fact-needs. Each outlet-bound claim is separate. A date is a filter only when the user restricts **article publication**.
- Only snippets cover needs. `question` and `prior_queries` are never evidence.
- After both sides of a comparison / both named outlets already have covering snippets (or were searched, on unanswerable), **stop**. Do not invent a third hop for the comparison, the CEO, or «featured in both».
- If every gold-style fact-need is covered, `enough` even when the final Yes/No is a combination of two snippets.
- If named outlets were searched and hits are off-topic / wrong site / unrelated celebrity, and no required filter remains unused, `empty_stop`.
- `missing_hop` only when a required outlet, publication window, or uncovered fact-need was never searched with that filter.
- Evidence is append-only. `note` empty on stop; on continue, a new standalone hint, never a prior query string.
- No outside knowledge.

---

## Prompt structure (mandatory)

File: `project/src/prompts/grade_agent.md`  
English only. No Python, YAML, JSON, Jinja, env, or secrets.

```markdown
# Identity
...

# Instructions
...

# Examples
<user_query>
{"question":"...","evidence":[...],"prior_queries":[...]}
</user_query>
<assistant_response>
{"verdict":"enough","note":""}
</assistant_response>
```

Start from the **current** production file (three-verdict, append-only, snippet-only coverage). Do not restore `rewrite`. Do not restore `tests/live_grade_gt/inputs/control.md` or the 40/350 stub.

Example input JSON may be pretty-printed. Output is `verdict` + `note` only.

---

## Synthetic examples — mandatory, you will build them yourself

This document does not give example bodies. Do not copy `cases.json`. Do not clone Q01–Q11 with swapped names.

Allowed way:

1. Invent a fictional domain (new newspapers, towns, fake `https://….example/…` URLs). Do not recycle Pebble Dispatch / Lichen Record / Marsh Courier / Oak mill / Vale Post if those already look like other agents' examples **and** like the exam after hiding names — still fine for Grade if they are not exam lookalikes.
2. At least three pairs. Prefer teaching **stop**:
   - two covering snippets on a comparison question → `enough`, empty `note`
   - two named outlets already searched, off-topic chunks, entity not in the index → `empty_stop`, empty `note`
   - second named outlet never searched → `missing_hop` with a new `note`
   - optional fourth: covering pair plus an unrelated extra chunk → still `enough`
3. Hide proper nouns: if it is still Q04/Q06/Q09/Q10 — replace the pair.
4. You may invent **new** questions over unused corpus articles that are not gold for Q01–Q11. Forbidden: the 11 exam questions, their gold `fact` sentences, their titles, their URLs, or isomorphic few-shot of those items.

---

## Leakage check (do it yourself)

After every edit, search `grade_agent.md` against:

- `project/src/data/questions.json`
- `project/src/data/ground_truth/Q01.json` … `Q11.json`
- `project/tests/live_grade_e2e_visits/inputs/cases.json`

A full question, `fact` sentence, title, URL, gold sub-question, or expected tool `question` from those files — you leaked. Delete.

The runner sets `prompt_leak_hit=1` on needles ≥ 24 characters and zeros every `case_success`. Lookalikes are **not** caught automatically. That is still on you.

Debugging a CSV is allowed. Pasting that row into the prompt is forbidden.

---

## In / out

**Edits:**

- `project/src/prompts/grade_agent.md` (the only production prompt)
- `project/tests/live_grade_e2e_visits/` (new board: runner, README, `inputs/cases.json`, snapshots)
- the Status line in that README after a run, if you want

**Allowed to read (not to edit):**

- This plan
- `project/src/agents/grade_agent.py` (what is sent, what is bound)
- `project/src/orchestration/grounded_answering_workflow.py` (`grade_node`, `prior_query_records`, append-only state) — without changing
- `project/output_for_mission/transcripts.json` and e2e `metrics_*.csv` — to reconstruct visits
- `project/src/data/questions.json`, `ground_truth/Q01.json`–`Q11.json` — to label expected verdicts, not to copy into the prompt
- `project/src/prompts/gather_agent.md`, `retrieve_agent.md`, `answer_agent.md` — **read only, locked**

**Forbidden to edit:**

- `gather_agent.md`, `retrieve_agent.md`, `answer_agent.md`
- `grade_agent.py`, agents, tools, services, repositories, orchestration, `conts.py`, schemas
- Q01–Q11 JSON, `questions.json`, `answers.json`, `facts.json`
- `grade_coverage.json`, `grade_invented_midloop_stop_continue.json`
- vector stores, `RETRIEVAL_TOP_K`, the e2e runner

Do not add agents. Do not restore `rewrite`. **One named hypothesis** per live run.

The README inside the new test directory must include Goal, Scope, How to run, Inputs, Expected outcome, Status — and must **not** be an `AGENTS.md`.

---

## Loop

1. Build `tests/live_grade_e2e_visits/` and freeze `inputs/cases.json` from real visits. Snapshot production Grade to `inputs/control.md`.
2. Snapshot each edit to `inputs/candidate_<short_hypothesis_name>.md`.
3. Edit **only** `grade_agent.md`. One named change. Synthetic `# Examples` remains.
4. Recheck friend-review and GT-string search.
5. Run `tests.live_grade_e2e_visits.run_live_grade_e2e_visits`.
6. Open the newest `metrics_*.csv`. Count `case_success=1`. On misses: predicted vs expected, then `note`.
7. If all rows pass — run **again without a prompt edit**. Two consecutive files are the pass.
8. If not — one new named hypothesis aimed at stop-on-coverage / stop-when-unanswerable-outlets-were-searched. Repeat.

Do not «fix» gold by editing Q01–Q11 or by retargeting `cases.json` to a weak prompt.

Do not recommend a supervisor, extra agents, raising the tool cap, or editing Gather so it ignores a bad `grade_note`.

---

## How to read a miss (teach a general habit)

| Fail | What to teach |
|---|---|
| Q06-class: `missing_hop` when gold facts already in evidence | comparison is not a third search; `enough` |
| Q09/Q04-class: `missing_hop` after both named outlets searched | `empty_stop`; off-topic hits will not become the missing entity |
| Q10-class: `empty_stop` when both gold sentences are present | two snippets together cover a yes/no; `enough` |
| `enough` while a required outlet was never in `prior_queries` | `missing_hop`; do not stop early |
| `note` repeats a prior query | new wording only |
| `prompt_leak_hit=1` | delete the needle; the run is invalid |
| 429 / `runtime_error` | wait, rerun the **whole** suite. A partial CSV is not a score |

---

## There is no stop rule

Do not stop until two consecutive `metrics_*.csv` files with `case_success=1` on every frozen visit, `prompt_leak_hit=0`, and synthetic `# Examples`. No run ceiling. A test lookalike = delete that example pair, write another, continue.

An interim report is allowed when there is a double pass, or when the user asks for status. In status: CSV paths, N/N per candidate, remaining `id`s and expected vs predicted, the best `candidate_*.md` — then continue.

Do not edit Gather, Retrieve, Answer, k, or the graph.

---

## Architecture decisions (closed — honor them)

- Three verdicts only. `rewrite` is cancelled.
- Grade has no tools. Input is `{question, evidence, prior_queries}`.
- Evidence is append-only. Answer receives the full list.
- Continue is only `missing_hop`. Stop is `enough` or `empty_stop`.
- Caps stay 6 / 5. This board does not hit them; the prompt must stop without them.
- Production prompt filename matches `grade_agent.py`.

---

## The final deliverable

A `grade_agent.md` in vendor structure, with mandatory synthetic examples, that hits **every frozen real-visit case twice** on `tests/live_grade_e2e_visits` with `prompt_leak_hit=0`, plus snapshots under that directory. No other production files changed.

---

## Open questions

- none

---

## Opening message for the other chat

Read `project/plans/gate4-grade-e2e-visits-prompt-goal.md` from the first heading to the end. Follow the friend-review checks. You own only `project/src/prompts/grade_agent.md` plus a new Grade-only board under `project/tests/live_grade_e2e_visits/`. Freeze GT from real Grade I/O in `output_for_mission/transcripts.json`: wrap accumulated `{question, evidence, prior_queries}` and label the verdict that **should** come out (`enough` when gold facts are already in evidence, `empty_stop` when unanswerable named outlets were already searched, never a comparison/CEO third hop). Do not copy Grade's recorded verdicts. Do not put evaluation text or lookalikes in the prompt. `# Examples` is mandatory and synthetic. Length may exceed the old 40/350 Grade limit. Score only with `tests.live_grade_e2e_visits`. Success is every frozen visit `case_success=1` twice. There is no stop rule.
