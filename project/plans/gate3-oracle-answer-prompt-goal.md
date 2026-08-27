# GOAL — Oracle Answer 11/11, no data leakage

**Status:** Done  
**Author:** N/A  
**Created:** 2026-08-27  
**Target Completion:** 2026-08-27  
**SDD(s) Impacted:** none  
**Rollback:** restore `project/src/prompts/answer_agent.md` from git, or from `project/tests/oracle_answer_gt/inputs/candidate_round2_temporal_clause_binding.md`.

---

## Closed — 2026-08-27

Gate 3 is closed. Round 2 reached **11/11** on two consecutive CSVs plus an independent re-run, with no evaluation items and no isomorphic few-shot in `project/src/prompts/answer_agent.md`.

Winning scoreboard:

- `tests/oracle_answer_gt/outputs/metrics_2026-08-27_21-56-37.csv` — 11/11
- `tests/oracle_answer_gt/outputs/metrics_2026-08-27_21-58-37.csv` — 11/11 (same prompt, no edit)
- `tests/oracle_answer_gt/outputs/metrics_2026-08-27_22-16-19.csv` — 11/11 (independent re-run)

Do not re-open this GOAL to chase a higher number. Do not put exam clones back into the prompt. Next work is Gate 4 (Gather), not this file.

The sections below are the historical spec (round 1 fail, round 2 assignment). They are not an open task.

---

## Historical spec (do not execute)

This block was the round-2 assignment. It is kept for the record. The GOAL is **Done**. Do not edit `answer_agent.md` from this file.

---

## Round 1 review (read this before you edit)

A previous agent already iterated on `project/src/prompts/answer_agent.md`.

### What was good

- Stayed in scope: production prompt only. Did not edit the runner, GT, Gather, or citation filter.
- Used the vendor shape: `# Identity` / `# Instructions` / `# Examples` with `<user_query>` / `<assistant_response>`. Short. English.
- No exam question text, no gold titles, no real news URLs. Toy domain `https://example.test/...`.
- Kept real product rules in general language: a supported No is an answer; multi-clause Yes needs every clause; compare `published_at` for before/after; copy snippet/url exactly; a conclusion may come from combining items, not from one snippet.

### Why round 1 is still a FAIL

The CSV is 11/11. The method is still cheating.

After a clean 8/11 (`metrics_2026-08-27_20-31-49.csv`, failures Q08 / Q10 / Q11 refused), the agent looked at those failures and put **two toy examples that are the same traps with the names swapped**:

| What is in the prompt now | What it is teaching |
|---|---|
| “Did the bulletin's subject change between the two notices?” → Yes | The remaining coverage-change item (Q08): two reports, different subjects, Yes is inferred, not written in one snippet |
| “Does the first notice leave the berth fee **unspecified**, **while** the second …” → No | The remaining conjunction item (Q10), including the exam’s distinctive word `unspecified` and the `while` template |

That is **isomorphic few-shot**. The GOAL already forbade paraphrases that are still clearly the same exam item. Harbor names do not make it clean. The unittest that searches for `Flipboard` / `Forerunner` / `Tremblant` does **not** catch this. Do not treat that unittest as a leakage pass.

Q11 improved more honestly: a general `published_at` direction rule, without a Gemini toy clone.

### Other process faults in round 1

- Stacked several new rules plus the two targeted examples in one prompt instead of one hypothesis per run.
- Did not save `inputs/candidate_<name>.md`, so prompt versions cannot be matched to CSVs.
- Scores between `20-43` and `20-55` jumped around (Q08/Q10/Q11 flipping refuse vs wrong Yes/No). One lucky 11/11 is not a pass. Two consecutive 11/11 files on the **same** prompt are required.

### Scoreboard (do not treat these as a pass)

| File | Score | Notes |
|---|---|---|
| `metrics_2026-08-27_20-07-33.csv` … `20-11-54.csv` | 11/11 | **Invalid** — exam items were in the prompt |
| `metrics_2026-08-27_20-29-24.csv` | 2/11 | Clean zero-shot; only Q04/Q09 |
| `metrics_2026-08-27_20-31-49.csv` | 8/11 | Last **honest** baseline. Q08, Q10, Q11 refused |
| `metrics_2026-08-27_20-43-52.csv` … `20-55-24.csv` | 8–10/11 | Unstable while the isomorphic examples were being fitted |
| `metrics_2026-08-27_20-57-32.csv` | 11/11 | Round-1 claim. **Rejected** (isomorphic few-shot) |
| `metrics_2026-08-27_21-30-46.csv` | 11/11 | Independent re-run of the same leaked-in-spirit prompt. Confirms the number, not the method |

---

## Follow-up task (what you do now)

**Starting file:** the current `project/src/prompts/answer_agent.md` (the round-1 prompt). Do not revert to the old `[INSTRUCTIONS]` / `ROLE:` template. Do not copy `inputs/control.md` (it still contains exam content).

### Step A — required first edit (do this before any new experiment)

1. Copy the current prompt to `project/tests/oracle_answer_gt/inputs/candidate_round1_rejected.md` so the rejected version is on disk.
2. In production `answer_agent.md`, **delete both current examples** (the dock/ferry “subject change” pair and the berth-fee “unspecified while” pair).
3. You may keep the `# Instructions` bullets that are actually general (evidence fields, supported No, combine items, `published_at` direction, conjunction, refuse if empty, verbatim citations, no outside knowledge).
4. `# Examples` may disappear. If the unittest fails because `example.test` is gone, fix **only** that one assert in `tests/grounded_answering/test_grounded_answering.py`. Do not weaken the Flipboard/Forerunner/Tremblant checks.
5. Run the oracle command in section 7. Record the new CSV. A drop from 11/11 is expected and honest. That is the new baseline for round 2.

### Step B — iterate until a clean 11/11

Same loop as section 9, with these extra rules:

- Change **one** general instruction per run. Do not add an example that clones a failing row.
- If you add examples again, they must be **format** examples (verbatim citation copy, empty evidence → refuse, one-snippet entity). They must **not** be the exam’s decision traps with fake names.
- After every edit, search the prompt for the forbidden patterns in section 3.
- Save `inputs/candidate_<short_name>.md` **before** each run.
- Stop only when **two consecutive** oracle CSVs are 11/11 on the **same** prompt text, and the leakage checks in section 3 still pass.

Do not put the deleted examples back. Do not rebuild them with a stadium, a bakery, or any other costume.

---

## 1. What this system is (plain language)

This project answers 11 news questions (IDs `Q01` … `Q11`).

There are two agents in production:

1. **Gather** — searches a facts index with tools. **Out of scope for you.**
2. **Answer** — receives the user question plus a list of evidence items, and must return a short answer or a refusal. **This is your only surface.**

The test you will run is an **oracle**. It does **not** call Gather. It does **not** search. For each question it injects that question’s gold facts as evidence (or an empty list), calls Answer, then scores the result against local ground truth.

So you are testing: **if the gold evidence is already on the table, does the Answer prompt produce the right short answer and the right citation titles?**

This is not full end-to-end. Do not run Gather / e2e tests for this GOAL.

---

## 2. The GOAL (pass / fail)

**Pass (all of these):**

1. The two newest oracle CSVs, from two runs of the **same** prompt, both have `oracle_success=1` on all 11 rows.
2. `answer_agent.md` matches the OpenAI section shape in section 4.
3. The prompt has **no** exam items, **no** gold strings, and **no** isomorphic few-shot of the exam (section 3).

What `oracle_success=1` means:

- For **answerable** rows (`unanswerable=0`): the model’s short answer matches ground truth, **and** every ground-truth citation **title** appears in the model’s citations.
- For **unanswerable** rows (`unanswerable=1`): status is refused, answer is empty, citations are empty. Today those IDs are **Q04** and **Q09**.

**Fail:** any row with `oracle_success=0`, **or** any evaluation question / answer / gold snippet / gold title in the prompt, **or** a toy example that is the same decision as a remaining exam item with the names swapped, **or** a single 11/11 CSV after you just fitted that example.

A score of 11/11 reached by putting the exam (or a clone of the exam) in the prompt is **invalid**. Delete that prompt. Do not keep it.

---

## 3. Data leakage — forbidden, not optional

The 11 questions plus their gold answers, gold facts, and gold citations are an **exam**. The prompt is a **study guide**. The study guide must not contain the exam, and must not contain a disguised copy of the exam.

**Do not put any of the following into `answer_agent.md` (or into any other prompt file):**

- The text of questions `Q01`–`Q11`
- The short gold answers (entity names, Yes, No, or the refusal sentence)
- Gold `fact` / snippet strings from `project/src/data/ground_truth/`
- Gold article titles or URLs from those files
- Paraphrases that are still clearly the same exam item (“the Flipboard ActivityPub question”, the ski-resort pair, and so on)
- Copied rows from `answers.json`, `transcripts.json`, or ground-truth JSON
- **Isomorphic few-shot:** a fake-domain example whose question shape and correct Yes/No are the same as a specific exam item. Harbor / ferry / bakery names do not make this legal.

**Explicitly forbidden example shapes** (do not rebuild these):

- “Did the subject / coverage / topic change between two notices / reports?”
- A two-clause question that uses the word **`unspecified`** plus **`while`**
- Any other clone where you took a failing CSV row, swapped the entities, and kept the trap

**You may open** ground-truth JSON **after a run** to understand why a CSV row failed. That is debugging. The moment you paste that content into the prompt, or turn that row into a toy clone, you have leaked. Close the file and write a **general** instruction instead (for example: “use `published_at` for before/after”, not the actual dates from a question).

**If you want examples in the prompt:** invent them yourself. Fake URLs only (`https://example.test/...`). Prefer format examples:

- Empty evidence → refuse, empty citations
- One snippet that names an entity → answer that entity, copy the snippet exactly
- Do **not** add examples whose only job is to teach the Yes/No of a failing exam row

A cheap check after every prompt edit:

1. Search for `Flipboard`, `Forerunner`, `Tremblant`, and any gold title or snippet from `Q01.json`–`Q11.json`.
2. Search for `unspecified` and for “subject change” / “coverage change between”. If those are in an example, you leaked again.
3. Ask: “if I hide the toy names, is this still obviously one of the 11?” If yes, delete it.

---

## 4. You must use the vendor prompt shape (OpenAI / GPT-4o-mini)

Production chat model (see `project/.env.example`): **`openai/gpt-4o-mini`** via OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`).

You **must** structure the system prompt the way OpenAI documents a developer/system message for this family. Do **not** use the old project template (`[INSTRUCTIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`). Do **not** use Claude-style XML instruction tags such as `<role>` or `<decision_policy>` as the main outline.

OpenAI’s documented section order:

1. **`# Identity`** — who the assistant is and its high-level goal.
2. **`# Instructions`** — what to do, what never to do, numbered or bulleted.
3. **`# Examples`** — optional. Only if you built non-exam, non-isomorphic examples yourself. OpenAI’s own illustration uses `<user_query>` … `</user_query>` and `<assistant_response>` … `</assistant_response>` **inside** this section.
4. **Context** — **not** written into the prompt file. The runner already sends context as the **user** JSON: `{"evidence": [...], "question": "..."}` with evidence first, then the question. Do not paste live evidence into `answer_agent.md`.

Use **Markdown headers** (`# Identity`, `# Instructions`, `# Examples`) so GPT can see the hierarchy. Keep the prompt **short**. Long prompts weaken instruction-following on this model. Prefer zero-shot; add examples only if a clean run shows a **format** problem (for example citations not copied verbatim).

The model output is already constrained by a Pydantic schema (`AnswerResult`: `status`, `answer`, `citations[]` with `article_title`, `url`, `snippet`). You do not need to ask for a markdown JSON code block. Citations must be **character-for-character** copies of an evidence item’s `snippet` and `url`. After the model returns, code drops any citation that is not an exact match and **forces a refusal** if nothing remains. If you see `predicted_status=refused` and `citations_empty=1` on an answerable row, the usual cause is: the model answered but paraphrased the snippet, so the filter wiped it.

Evidence fields the model actually receives:

- `article_title`
- `snippet` (the gold fact sentence)
- `url`
- `published_at` (ISO timestamp — treat as a real fact, including for before/after)
- `match_percentage`

---

## 5. Your responsibility (in) vs stay out (out)

**In — you may edit:**

- `project/src/prompts/answer_agent.md` — this is the only production file you change.
- Optional history copies: `project/tests/oracle_answer_gt/inputs/candidate_<short_name>.md` (save a snapshot of a prompt version). The runner does **not** load these; it always loads the production file above.
- Only if you remove all `example.test` URLs: the single `assertIn("example.test", …)` in `tests/grounded_answering/test_grounded_answering.py`.

**Out — do not edit, do not “fix”, do not expand into:**

- Ground truth: `project/src/data/ground_truth/Q01.json`–`Q11.json`, `project/src/data/questions.json`, `project/src/data/facts.json`
- Gather prompt or gather agent
- Retrieval, Chroma, tools, services, schemas, orchestration logic, `filter_answer_citations`
- The oracle runner `run_oracle_answer_gt.py` (do not change scoring to make 11/11 easier)
- Root `answers.json` / `transcripts.json` (those are a later full-pipeline step, not this GOAL)
- End-to-end / Gather evaluation tests
- Other plans, rules under `.Codex/rules`, or unrelated tests
- This GOAL file, except you may ignore it as a place to dump notes

If a failure looks like “Gather did not retrieve the hop”, that is **not your bug** on this test. This test already injects gold facts. Stay on the prompt.

---

## 6. Files you need to know

| Path | What it is | You |
|---|---|---|
| `project/src/prompts/answer_agent.md` | Production Answer system prompt | **Edit this** |
| `project/src/agents/answer_agent.py` | Loads that file, calls the model with structured output | Read only |
| `project/src/orchestration/grounded_answering_workflow.py` | `filter_answer_citations` — exact snippet+url or refuse | Read only |
| `project/src/schemas/agent.py` | `AnswerResult` / `AnswerCitation` | Read only |
| `project/tests/oracle_answer_gt/run_oracle_answer_gt.py` | The only runner for this GOAL | Run it, do not edit it |
| `project/tests/oracle_answer_gt/README.md` | Short test notes | Read |
| `project/tests/oracle_answer_gt/outputs/metrics_*.csv` | Scoreboard | Read after each run |
| `project/tests/oracle_answer_gt/inputs/control.md` | Old prompt snapshot | Do not copy exam content from it into production |
| `project/tests/oracle_answer_gt/inputs/candidate_*.md` | Prompt version snapshots | **Write these** before each run |
| `project/.env` | API key and `OPENAI_MODEL` | Must exist; do not commit it; do not print secrets |

---

## 7. How to run the task (copy-paste)

Open a terminal. Working directory must be the inner `project` folder (the one that contains `src/` and `tests/`).

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.oracle_answer_gt.run_oracle_answer_gt
```

Requirements:

- `project/.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- Network (OpenRouter)
- Wait: the runner sleeps a few seconds between the 11 questions. A full pass is on the order of 1–2 minutes. No `print` output is normal. Success is a **new CSV**, not console text.

Optional leakage smoke check (does not call the model):

```text
cd project
uv run python -m unittest tests.grounded_answering.test_grounded_answering.GroundedAnsweringTests.test_prompts_exist_and_require_verbatim_snippet
```

That unittest currently expects `# Identity`, `published_at`, a verbatim-copy instruction, and that `Flipboard` / `Forerunner` / `Tremblant` are absent. It also currently expects `example.test`. Passing this unittest is **necessary and not sufficient**. It missed the round-1 isomorphic examples.

Do **not** run live Gather/e2e tests for this GOAL. They are a different gate.

---

## 8. Where output goes and how to read it

**Directory:** `project/tests/oracle_answer_gt/outputs/`

**File:** `metrics_YYYY-MM-DD_HH-MM-SS.csv` (new file every run; UTF-8 with BOM). Always open the **newest** timestamp.

**One row per question.** Columns:

| Column | Meaning |
|---|---|
| `question_id` | `Q01` … `Q11` |
| `unanswerable` | `1` = must refuse (Q04, Q09); `0` = must answer |
| `expected_answer` | Ground-truth short answer (exam secret — do not copy into the prompt) |
| `predicted_status` | `answered` or `refused` |
| `predicted_answer` | What Answer returned |
| `answer_match` | `1` if the short answer (or refusal) matches GT |
| `citation_title_recall` | Fraction of GT citation titles that appeared |
| `citations_empty` | `1` if the model/filter left no citations |
| `injected_evidence_count` | How many gold facts were injected (`0` on Q04/Q09) |
| `oracle_success` | **The score.** You want `1` on every row |
| `expected_citation_titles` | GT titles, ` \| ` separated |
| `predicted_citation_titles` | Model titles after the exact-match filter |
| `missing_citation_titles` | GT titles the model missed |

How to check a run:

1. Count rows with `oracle_success=1`. Target: **11**, twice in a row.
2. For each `oracle_success=0`:
   - If `predicted_status=refused` and `injected_evidence_count>0`: Answer refused or the citation filter wiped paraphrased snippets. Tighten **verbatim copy** and “supported No is an answer”, in general language.
   - If `answer_match=0` but status is answered: wrong Yes/No/entity. Teach a general decision rule (conjunction, before/after via `published_at`). **Do not** add that question as an example.
   - If `answer_match=1` but `citation_title_recall<1`: the short answer was right but a GT title is missing. Ask to cite every supporting hop, still without naming the exam titles.

---

## 9. Experiment loop (this is the whole job)

Repeat until a **clean** 11/11 **or** you are blocked without leaking:

1. Snapshot the current prompt to `inputs/candidate_<name>.md`.
2. Edit only `project/src/prompts/answer_agent.md`, staying in `# Identity` / `# Instructions` / optional `# Examples`.
3. Keep it short. English only. One general hypothesis.
4. Confirm section 3 (including isomorphic shapes) is clean.
5. Run the command in section 7.
6. Open the newest `metrics_*.csv`.
7. If 11/11, run **once more with no prompt change**. Both CSVs must be 11/11.

Stop when both consecutive CSVs are 11/11 and the prompt still has no exam content and no isomorphic clones.

If you are blocked: report the newest CSV path, the remaining failing IDs, and that you refused to leak. Do not invent a costume example to close the last rows.

---

## 10. Product behavior the prompt must support (general, not exam spoilers)

Write instructions that cover these **types**, without naming the 11 items and without cloning them as examples:

- Use **only** this-run evidence. No world knowledge.
- Short answer only: entity name, `Yes`, or `No`. No extra prose in `answer`.
- Empty evidence → refuse, empty citations.
- A well-supported **No** is an answer, not a refusal.
- Multi-clause questions: Yes only if every clause holds; No if evidence shows the whole claim is false. A false first clause makes the whole conjunction No even if a later clause is true.
- Temporal before/after: compare `published_at` timestamps even when the snippet has no date, in the direction the question asked.
- Two items may support a comparison (same vs different subject, before vs after) even if neither snippet states the comparison in words.
- Citations: copy `article_title`, `url`, and `snippet` **exactly**. Never paraphrase the snippet.

Do not add a special-case rule that is only true for one of the 11 questions.

---

## 11. Done when

- Two consecutive newest `metrics_*.csv` files are 11/11 `oracle_success=1` on the same prompt.
- `answer_agent.md` still matches the OpenAI section shape above.
- `answer_agent.md` contains no evaluation questions, gold answers, gold snippets, gold titles, or isomorphic clones (no “subject change between two notices”, no “unspecified while”).
- You saved candidate snapshots for the rejected round-1 prompt and for each round-2 attempt.
- You did not change files outside the prompt (except those snapshots and, only if needed, the single `example.test` unittest assert).

**Rollback:** revert `answer_agent.md` with git, or restore a clean candidate snapshot, if a prompt change is worse or leaks.

---

## 12. Copy this into the other chat (first message)

Read `project/plans/gate3-oracle-answer-prompt-goal.md` from the first heading to the end. That file is your only spec. Round 1 is rejected: 11/11 on the CSV with isomorphic few-shot of the remaining exam items. Execute the follow-up: delete those two examples first, then reach 11/11 twice in a row with no exam clones, by iterating on `project/src/prompts/answer_agent.md` only.

---

## Revision — 2026-08-27 — Round 1 rejected, round 2 assigned

Round-1 numeric 11/11 (`20-57-32`, independently re-run as `21-30-46`) used toy examples that clone Q08 (subject/coverage change) and Q10 (`unspecified` + `while`). Unittest leak strings were clean; the GOAL still fails. Follow-up requires deleting those examples, snapshotting prompt versions, and two consecutive clean 11/11 CSVs. Honest baseline remains `20-31-49` (8/11) until round 2 produces a clean scoreboard.
