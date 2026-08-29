# GOAL — Gather hop inventory 11/11, without leakage

**Status:** Superseded — 2026-08-28. Hop-inventory wording vs `sub_questions` is no longer the score. Gold `facts` chunks in the first `search_facts` batch: **Done** 2026-08-29 ([`gate4-gather-gold-chunks-prompt-goal.md`](gate4-gather-gold-chunks-prompt-goal.md)).  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** TBD  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/gather_agent.md`

This is the **only** file you read. Do not read other plans. Do not copy old prompt templates. Do not run other live boards as your score.

You have no other context. Everything you need is here. Your work is prompt experiments **on one file**. Success = **11/11 twice** on the hop inventory against the local GT, **with no data leakage at all**, and with **mandatory synthetic `# Examples`**. **There is no stopping rule.** Do not stop after N runs, not after a repeating failure class, and not when one fix breaks another. Run until two clean 11/11s. Leakage disqualifies the **run** (delete the leaked text, write a different synthetic example, and continue), not the task. The 40/350 limit is cancelled.

---

## Friend review — these are what you will fail on

A previous attempt was disqualified. Do not repeat it.

1. **Leakage is cheating.** You must not put in the prompt (`gather_agent.md`) questions from the evaluation set, answers, article titles, passages, URLs, gold sub-questions, tool `question` strings, or «the same question with fake names». If the study material contains the test, the score is invalid even at 11/11.
2. **`# Examples` is mandatory — synthetic only.** A prompt without an `# Examples` section is forbidden. Examples from our test are forbidden. **You must invent and build** at least two `<user_query>` / `<assistant_response>` pairs in a fake domain (newspapers, places, events that do not appear in the GT). Do not copy GT. Do not clone Q01–Q11 with swapped names. If someone who saw the 11 test questions would recognize the example after you hide nouns, delete it and write a different example — do not delete the entire section.
3. **Length is allowed.** The 40-line / 350-word limit is **cancelled**. You may lengthen the prompt so there is room for instructions and the synthetic examples. Do not fill it with test text and do not repeat the same instruction ten times. Soft ceiling: up to **120 lines** and **1200 words** — if you exceed it, shorten duplicate examples, do not delete `# Examples`.
4. **Vendor structure only. You must stick to this.** The model is `openai/gpt-4.1` via `OPENAI_GATHER_MODEL`. Use the OpenAI developer-message outline and only that:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (**mandatory**, at least two synthetic pairs)
   - **Do not** put `# Context` in the file. Runtime JSON is sent as a user message.
5. **No old prompt template.** Do not leave and do not translate `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`. Do not use Claude-style XML tags such as `<role>` or `<decision_policy>` as the main outline.
6. **Wording is free.** Do not try to match word-for-word the GT `sub_questions` or `expected_tool_calls.arguments.question`. That is not the goal. Copying them is leakage.

After every edit, before a run: open `gather_agent.md` and verify that all six items pass.

---

## What this product is

The service answers news-facts questions over a **local** article index.

In the live loop there are several agents. You own **only Gather**, and only **one task** of Gather: the hop inventory.

```text
User question
    → Gather     (you)     List of independent sub-questions. No tools.
    → Retrieve   (frozen)    One search_facts call per sub-question. Fills source / dates.
    → Tools      (code)     Runs search_facts against Chroma. Top-1 passage per call.
    → Grade      (frozen)    enough / rewrite / missing_hop / empty_stop
    → Answer     (frozen)    Yes/No/entity or refuse
```

Retrieve sees **only one sub-question string** at a time. It does not see the parent question. It does not see sibling hops. If Gather packs two newspapers into one string, Retrieve cannot put `source` on either of them. If Gather omits the newspaper from a claim, Retrieve will not add it. If Gather emits a hop whose entire role is «did the newspaper featured the topic», Retrieve will search that useless string.

**If the hop list is wrong, the failure stays with Gather.** What comes after it does not fix a packed or over-split inventory.

---

## What Gather is (your only task)

**One goal: the hop inventory.**

Take the user question and split it into a list of independent sub-questions. Each sub-question is **one information need** that needs **one search**.

Gather does **not** search. Gather does **not** fill `source`. Gather does **not** fill dates as tool arguments. Gather does **not** answer the user. Gather does **not** call tools.

### Input (already sent as a user message — do not write this JSON in the prompt)

```json
{"question": "<user question>", "prior_queries": [], "grade_note": ""}
```

On a retry the same structure arrives with a non-empty `grade_note` and a filled `prior_queries`. The score on the 11 questions is first turn: empty `prior_queries` and empty `grade_note`.

### Output (already bound in code)

```text
sub_questions: list[str]
```

No tools. No other fields.

---

## How Gather must split (general habits, not test rows)

Teach these habits in the prompt. Do not mention question IDs inside the prompt.

- Split by claims that can be verified **separately**:
  - a side of a comparison
  - an ability in a list
  - an event
  - a side of `and` / `or`
  - a side of `before` / `after`
  - each of these is **its own string**
- **Do not** add a third hop for the comparison itself («did A happen before B?», «did the coverage change?») after you have already emitted both sides.
- **Do not** add a hop whose entire role is the entity name, when that name is already what the ability/event hops are asking about.
- Abilities that appear as a pair in the same clause («debug code and compose music») may stay **one string**. Do not split every verb into its own hop and then also add a name-hop and featured-in hops.
- If the user put a **newspaper on a specific claim**, copy the newspaper name **only** into that claim's string. Not onto claims he did not say the newspaper reports. Class example: Q05 — `The Age` only on the The Age clause, not on the TechCrunch clauses.
- If the user put the **same** newspaper on two claims (two sides of `and`, two events), copy the newspaper onto **both** strings.
- If the user put a **publication window**, keep it in the text of the sub-question it constrains. Event dates stay in the text as well. Gather does not format ISO tool arguments. Retrieve will read the dates from your string.
- **Do not pack two needs or two newspapers into one string.** Class example: Q04 — New York Times and Wall Street Journal must be two strings, otherwise Retrieve cannot fill `source` for either.
- **A hop whose entire role is «did the newspaper featured the topic» is forbidden.** Copy the newspaper into the real claim/ability/event string. Class example: Q07 — extra featured-in hops and over-splitting (name-hop, featured-in hops, a hop per ability) are a Gather failure.
- **Retry:** if there is a `grade_note`, emit **only** new sub-questions that follow it and differ from every `prior_queries`. The 11-question score does not check this, but production does. Leave the rule in the prompt.
- **Never answers the user. Never calls a tool.** Return only `sub_questions`.

The score does **not** require your wording to match the GT. It requires the **inventory**: the correct number of needs, newspapers only on their claims, publication windows on the claims they constrain, no packing, no featured-in hops, no extra comparison hops.

---

## What is not yours

Do not do these. Do not write them in Gather's prompt. Do not edit their files.

| Domain | Who owns it | Why this is not Gather |
|---|---|---|
| `search_facts` arguments (`question`, `source`, `published_from`, `published_to`) | Retrieve | You emit strings. Retrieve copies and fills filters. |
| Source catalog / `run_resolve_source` | Retrieval service | Official newspaper-name matching happens after Retrieve fills `source`. |
| Chroma ranking / Top-1 | Retrieval | If the hop is independent and the newspaper is in the string, a gold miss at rank 1 is not your board. |
| Grade (`enough` / `rewrite` / `missing_hop` / `empty_stop`) | Grade | Stop vs continue is after the tools. |
| Answer | Answer | You never write Yes/No/entity. |
| Orchestration, tools, `conts.py`, indexes | Frozen | Out of scope. |

The failure stays with you if the split is wrong:

- Q04 packed (two newspapers in one string)
- Q07 over-split / featured-in
- Outlet on the wrong claim in the Q05 style (The Age only on the The Age clause)

Q01 where gold is missing at Top-1 **after** Sporting News is already in both strings is retrieval/k, not this board.

---

## Your task (the only pass)

Reach **11/11** on Gather's hop inventory against the 11 local GT questions, with **zero leakage**.

Do this by editing **only** `project/src/prompts/gather_agent.md`.

**Pass:** the two newest consecutive `metrics_*.csv` files from `project/tests/live_gather_hops/outputs/`, the same Gather prompt, `hop_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor structure, an `# Examples` section with at least two synthetic pairs, no test clones. No 40/350 limit.

`hop_success=1` means all of these hold:

- `prompt_leak_hit=0`
- empty `runtime_error`
- every item in the GT `sub_questions` is covered by a **separate** agent sub-question (no missing need)
- no string that covers two gold hops (`packed_needs=0`)
- no string that contains two gold newspapers (`packed_outlets=0`)
- no extra agent hops (`extra_hops=0`) — over-splitting, featured-in, and extra comparison hops count here
- no featured-in-only hop (`featured_in_hops=0`)
- a clause-limited newspaper was not copied onto a claim it does not belong to (`misattached_outlet=0`)
- publication windows that are in the GT appear in the matching sub-question text (`dates_missing=0`)

The runner compares **structure** to `sub_questions` in `project/src/data/ground_truth/Q01.json` … `Q11.json` (Gather's field per `project/src/data/ground_truth/README.md`). Newspaper and publication window are taken from `expected_tool_calls` with `agent: retrieve` at the same `sub_question_index`. It does **not** require gold wording word-for-word. `search_corpus` with `agent: unbound` is not part of this board.

---

## Which files to run (this board only)

Always from the inner `project/` directory.

**This is the 11/11 score. Use it every time.**

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_hops.run_live_gather_hops
```

You need a `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_MODEL`.

You do **not** need Chroma. It does **not** call Retrieve, Grade, Answer, or tools. One Gather call per question. A few minutes. No console printing.

These runs send the 11 evaluation questions to OpenRouter as Gather input. That is expected. Putting those questions in the prompt — not.

### Do not run these as your score

- `tests.live_gather_gt.run_live_gather_gt` — full loop + Grade + Chroma
- `tests.live_gather_first_hop.run_live_gather_first_hop` — Gather **plus** Retrieve plus `search_facts`
- oracle-Answer, e2e, Grade-only boards

If gold is missing on the other boards after your hop inventory is already 11/11, that is not this task.

---

## Output files — where they go and how to read them

Every run writes a new timestamped trio under `project/tests/live_gather_hops/outputs/`. Nothing is overwritten. Open the **newest** timestamp.

| File | What it is | How to use it |
|---|---|---|
| `metrics_YYYY-MM-DD_HH-MM-SS.csv` | The results board. **This is N/11.** | Count rows with `hop_success=1`. That is the score. |
| `hops_YYYY-MM-DD_HH-MM-SS.csv` | One row per **gold** hop | See which gold need was not covered (empty `matched_agent_index`, `covered=0`). |
| `calls_YYYY-MM-DD_HH-MM-SS.csv` | One row per **agent** sub-question | See packing, extras, featured-in, wrong newspaper. |

### `metrics_*.csv` columns that matter

- `hop_success` — 1 or 0. Sum them. Target 11.
- `gold_hop_count` versus `agent_hop_count` — extra or missing hops.
- `missing_gold` — a gold need with no matching string.
- `packed_needs` — one string covers two gold needs.
- `packed_outlets` — one string contains two gold newspapers.
- `extra_hops` — extra strings (over-splitting / comparison / name-only).
- `featured_in_hops` — a hop whose entire role is «featured in {outlet}».
- `misattached_outlet` — a newspaper was copied onto the wrong claim.
- `dates_missing` — a dated hop whose string omitted the publication window.
- `prompt_leak_hit` — 1 zeros **every** `hop_success`. Fix the prompt, do not argue with the scorer.
- `failure_class` — one label for debug (see below).
- `agent_sub_questions` — the list Gather returned, joined with ` | `.
- `runtime_error` — 429 / network / parse. Wait, rerun **all** 11. A partial CSV is not a score.

### `failure_class` values

| Label | What it means | What to teach (general habit) |
|---|---|---|
| `leak` | Test text in the prompt | Delete it. Do not turn the test into an example. |
| `runtime_error` | LLM/network/parse failure | Wait. Run all 11 again. Do not score this file. |
| `packed_outlets` | Two gold newspapers in one string | One newspaper per string. Two named newspapers → two strings. |
| `packed_needs` | Two gold needs in one string | One verifiable claim per string. |
| `featured_in` | A hop that only asks whether a newspaper featured the topic | Copy the newspaper onto the real claim. Do not emit featured-in. |
| `misattached_outlet` | A newspaper on a claim the user did not attach it to | Copy the newspaper only onto the clause that named it. |
| `missing_gold` | A gold need with no covering string | Split this **type** of claim. Do not paste the gold sentence. |
| `extra_hops` | Extra strings | Do not add a name-hop, a comparison-hop, or duplicates. |
| `dates_missing` | A publication window was omitted | Leave the named window in the string it constrains. |
| _(empty)_ | The row passed | — |

### `calls_*.csv` — to debug the strings themselves

Columns: `question_id`, `hop_index`, `sub_question`, `gold_match_index`, `is_extra`, `is_featured_in`, `packed_outlets_in_string`.

Look for:

- Packed: `packed_outlets_in_string=1` (Q04 class: NYT and WSJ on the same row)
- Featured-in: `is_featured_in=1`
- Over-split: how many `is_extra=1` on the same `question_id` (Q07 class)
- Wrong newspaper: in metrics `misattached_outlet=1`, then read the strings and see which claim got the extra newspaper

### `hops_*.csv` — to debug gold coverage

Columns: `question_id`, `hop_index`, `gold_source`, `gold_question`, `matched_agent_index`, `matched_agent_text`, `source_in_text`, `date_in_text`, `covered`.

`gold_question` is the test's hop wording. **You may read it to understand the miss. You must not paste it into the prompt.**

How to read a miss:

- `covered=0` → the need is missing or packed into another string
- `source_in_text=0` while `gold_source` is filled → you omitted the newspaper from this claim
- `date_in_text=0` while the gold hop is dated → you omitted the publication window

Learn a **general habit** from the failure class. Do not learn that row.

429 / `runtime_error` → wait, run all 11 again. Do not edit the prompt because of a network fault.

---

## Leakage check (do it yourself)

After every edit, search `gather_agent.md` against:

- `project/src/data/questions.json`
- `project/src/data/ground_truth/Q01.json` … `Q11.json`

If a full question, a fact sentence, an article title, a URL, a gold sub-question, or a tool `question` string from these files appears in the prompt — you leaked. Delete it.

The runner also sets `prompt_leak_hit=1` when that happens and zeros every `hop_success`. This check does **not** catch clone-examples. That is still on you.

You may **read** GT to understand hop inventory. You may **debug** a failed CSV. Pasting the row into the prompt is leakage.

---

## Prompt structure per the vendor (you must stick to it)

The consuming model is OpenAI GPT (`openai/gpt-4.1` in `OPENAI_GATHER_MODEL`) via ChatOpenAI. Retrieve / Grade / Answer stay on `OPENAI_MODEL`. Production prompts must match the vendor structure. See `project/src/prompts/AGENTS.md`.

Required section order:

```markdown
# Identity
...

# Instructions
...

# Examples
```

`# Examples` is **mandatory**. A prompt without this section, or with the section empty, is not eligible for a pass.

Inside `# Examples` use **only**:

```text
<user_query>
...
</user_query>
<assistant_response>
...
</assistant_response>
```

Rules:

- English only in the prompt file
- no executable code, no env lookups, no secrets
- no evaluation-set questions, answers, gold citations, or isomorphic few-shot of those items
- context is not written in the prompt. The consumer already sends `{question, prior_queries, grade_note}`
- **Zero-shot is forbidden.** Synthetic examples are required.
- You may lengthen. The old 40/350 limit is cancelled.

Start from the current `project/src/prompts/gather_agent.md` and add `# Examples` onto it. Do not restore `project/tests/live_gather_gt/inputs/control.md` (an old template that was disqualified). Do not restore `project/tests/live_gather_first_hop/inputs/control.md` (old Gather-with-tools wording).

---

## Synthetic examples — mandatory, you build them yourself

Do not ask anyone for test clones. Do not copy GT. Do not leave `# Instructions` without `# Examples`.

1. Invent a fake domain (mills, clubs, towns, fake newspapers that do not appear in the test). Do not recycle Oak mill / Harbor Gazette / Hill Ledger if they already failed as a Q07 clone — invent **other** names.
2. At least **two** user/assistant pairs. Prefer three–four, if you need to teach different habits (splitting sides, a sub-question that stands alone, newspaper inside the claim and not as a featured-in hop, singular `figure` instead of yes/no on an omission).
3. You may search the public internet for **format** ideas (what a sub-question list looks like). You must not paste our 11 questions or clones.
4. Example input in JSON format as at runtime: `{"question":"...","prior_queries":[],"grade_note":""}`. Output: `{"sub_questions":[...]}`.
5. Examples for **habit**: one claim per string that can be asked alone; newspaper only on the claim that named it; not a hop whose entire role is that the newspaper mentioned the entity.
6. Hide nouns and read again: if it still looks like Q04/Q05/Q07/Q10 — delete **that pair** and write a different pair. Do not delete all of `# Examples`.
7. The old length limit is cancelled. If there is not enough room for examples — lengthen, do not shorten them out.

---

## In / out

**Edit:**

- `project/src/prompts/gather_agent.md` — the only production file you change
- snapshots `project/tests/live_gather_hops/inputs/candidate_<name>.md` — history of every hypothesis

**Allowed to read (do not edit):**

- this plan
- `project/tests/live_gather_hops/README.md` and the runner (to understand how it scores)
- `project/src/agents/gather_agent.py` — how the prompt is loaded and which JSON is sent
- `project/src/schemas/agent.py` — `GatherResult.sub_questions`
- `project/src/data/questions.json`, `project/src/data/ground_truth/README.md`, and `project/src/data/ground_truth/*.json` — to understand inventory, never copy into the prompt
- the newest CSV files under `project/tests/live_gather_hops/outputs/`

**Do not edit:**

- `retrieve_agent.md`, `grade_agent.md`, `answer_agent.md`, any other prompt
- GT JSON, `questions.json`, `answers.json`
- agents, tools, services, repositories, orchestration, `conts.py`
- `tests/live_gather_gt`, `tests/live_gather_first_hop`, `tests/live_grade_gt`
- indexes
- the hop-inventory runner's scoring rules (do not «fix» gold by relaxing the board)

Do not add agents. Do not wire tools to Gather. Do not change Retrieve so it can unpack a packed string. **One named hypothesis** per live run.

---

## Loop

1. Snapshot the current production Gather prompt to `project/tests/live_gather_hops/inputs/candidate_<short_hypothesis_name>.md`. Also leave `inputs/control.md` as the starting file (already there).
2. Edit **only** `project/src/prompts/gather_agent.md`. One named change per run. Synthetic `# Examples` must remain in every candidate.
3. Recheck the friend-review list and search the prompt against GT strings.
4. Run the command in «Which files to run».
5. Open the newest `metrics_*.csv`. Count `hop_success=1`. On misses read `failure_class`, then `calls_*.csv` / `hops_*.csv`.
6. If 11/11 — run **again without editing the prompt**. Two consecutive 11/11 files are the pass.
7. If not — one new named hypothesis. Repeat.

Do not «fix» gold by editing GT. If a need is missing, split or rephrase that **type** of claim in general, still without test wording.

Do not recommend a stronger model again as the first lever without approval. The current round is `openai/gpt-4.1` (one grade above mini), the same starting prompt `candidate_gpt41_exactly_two_sides` / `candidate_gpt41_full_restart`.

---

## Current state — 2026-08-28 (must read before editing)

The previous chat does **not** start from zero. The production prompt is the stable candidate. The task is **only** to close the two remaining IDs, without destroying the nine that work.

### Locked baseline (revert to it after every regression)

- File: `project/src/prompts/gather_agent.md`
- Snapshot: `project/tests/live_gather_hops/inputs/candidate_gpt41_exactly_two_sides.md`
- Gather model: `OPENAI_GATHER_MODEL=openai/gpt-4.1` (Retrieve/Grade/Answer stay `OPENAI_MODEL=openai/gpt-4o-mini`)
- Score: **9/11 twice** on the same prompt — `metrics_2026-08-28_17-56-06.csv`, `metrics_2026-08-28_18-00-57.csv`
- Passing: Q01, Q02, Q03, Q04, Q05, Q06, Q08, Q09, Q11
- Failing: **Q07** (`featured_in`), **Q10** (`missing_gold`)

Gather **only** splits into isolated questions (`sub_questions: list[str]`). It does not fill `source`. The newspaper name must stay **inside the sentence**, because Retrieve sees only that string. A good sub-question = you can send it alone to Retrieve and the search is still clear. That is what later feeds the chunk: wrong hop → wrong `search_facts` → wrong passage. **Do not score** with `live_gather_gt` or `live_gather_first_hop`.

### What Q07 actually needs (habit, not gold wording)

One question with an entity, two newspapers, a list of abilities, and an ending event. Correct inventory = **3** strings:

1. First newspaper + the first ability in the list
2. The same first newspaper + the next two abilities joined by `and` (do not split per verb)
3. The second newspaper + the ending event only

Forbidden: a name-hop, a hop whose entire role is «featured in {outlet}», cloning all abilities onto both newspapers, packing all abilities into one string.

On the baseline the model emits name + featured-in for each newspaper + birthday without the second newspaper. It isolates questions, but the wrong slices.

### What Q10 actually needs (habit, not gold wording)

Two strings, one side per newspaper. The first side already passes on the baseline (the investment sum). The second side must ask what the second newspaper wrote about **the founding**, including a **number**. The scorer requires the English word **`figure` in the singular** (not `figures`). On the baseline the second side stays yes/no with `financial figures` — hence `missing_gold`.

Do not paste the gold sentence. You may read `Q07.json` / `Q10.json` to understand inventory.

### What was already tried — do not repeat it

| Experiment | Result | Why not to repeat |
|---|---|---|
| `openai/gpt-4o-mini` on Gather | Peak 7/11 | Too weak for splitting |
| `openai/gpt-4.1` (full) on the same 9/11 prompt | **8/11** (`metrics_2026-08-28_18-39-30.csv`) | Broke Q01 (copied Week 13 onto the wrong side, `packed_needs`); Q07 packed into two newspapers; Q10 did not move |
| «never featured» / «figure not figures» rules as extra bullets | 7–8/11 | A Q07/Q10 fix broke **Q04** (CEO hops per newspaper). Try different wording, do not stop |
| `# Examples` in a fake domain (Oak mill / Harbor Gazette / Hill Ledger / Vale Post / Tide Courier) for splitting abilities | 8/11 | 4.1-mini copies the split onto «known-for / CEO» in Q04 as well |
| The same examples for `figures`→`figure` | Q10 still copies `financial figures` from the user | Does not override the parent-question wording |
| A figure-only example without ability splitting | 8/11 | Q04 came back, Q09 lost nouns of the article topic, Q07/Q10 were not closed |

Snapshots under `project/tests/live_gather_hops/inputs/`: `candidate_gpt41_exactly_two_sides.md` (the winner), `candidate_gpt41_invented_examples*.md`, `candidate_gpt41_figure_example_only.md`. Read only so you do not repeat. Do not copy test clones from them if they are too close to Q07/Q10.

### What you may try now (one named hypothesis per run)

The prompt's goal: every sub-question stands alone, one information need, newspaper only if it belongs to that claim. **There is no stopping rule.** Run until 11/11 twice without leakage. **Every candidate must have synthetic `# Examples`** (at least two pairs). A candidate without examples is not eligible.

Directions (if one fails — a different hypothesis, not a wrap-up report):

- First add synthetic examples to the 9/11 baseline, in a new domain (not Oak mill if that already failed as a clone)
- Rephrase the **existing** bullets (same content, different words) **with** the examples
- If after hiding nouns an example looks like Q04/Q07/Q10 — replace the pair, do not delete all of `# Examples`
- If a fix breaks Q04/Q09: restore the baseline instructions, **keep** corrected synthetic examples, run again

After every failing edit: restore instructions from `candidate_gpt41_exactly_two_sides.md` if needed, but do **not** go back to a prompt without `# Examples`. Do not edit Retrieve, Grade, Answer, or the graph. Do not recommend a supervisor, a plan-before-search, extra agents, or teaching Retrieve to unpack packed strings.

---

## There is no stopping rule

Do not stop prompt work until there are **two** consecutive `metrics_*.csv` files with `hop_success=1` on all 11 rows, `prompt_leak_hit=0`, and full synthetic `# Examples`. There is no run ceiling. A test clone in the prompt = delete the leaked pair, write a different synthetic example, and continue.

Do not edit Retrieve, Grade, Answer, or the graph. An interim report is allowed only when there is 11/11 twice, or when the user asks for status. In a status: CSV paths, N/11 per candidate, remaining IDs and `failure_class`, the best `candidate_*.md` — then continue.

---

## First message for the next chat (paste this)

Read `project/plans/gate4-gather-hop-inventory-prompt-goal.md` from the first heading to the end, including «Current state — 2026-08-28». Go through the friend-review checks.

You are continuing work, not starting from zero. The production prompt (`project/src/prompts/gather_agent.md`, snapshot `candidate_gpt41_exactly_two_sides.md` / `candidate_gpt41_full_restart.md`) runs on `openai/gpt-4.1`. Nine questions were correct on mini. Q07 and Q10 remain.

Gather only splits into isolated sub-questions that can be asked alone. No tools, no `source` field. The newspaper stays inside the sentence so Retrieve can extract it. Wrong hop = wrong search = wrong chunk. Score **only** with `uv run python -m tests.live_gather_hops.run_live_gather_hops` from `project/`.

**There is no stopping rule.** Run until 11/11 `hop_success` twice. The Gather model is `openai/gpt-4.1`. No data leakage and no test clones — leakage disqualifies the run, replace the example and continue. Do not paste test text into the prompt.
