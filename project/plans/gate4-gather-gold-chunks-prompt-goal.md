# GOAL — Gather retrieving all gold chunks 11/11 vs frozen Retrieve, without leakage

**Status:** Done — 2026-08-29. Production: [`src/prompts/gather_agent.md`](../src/prompts/gather_agent.md). Pass: [`metrics_2026-08-29_11-16-45.csv`](../tests/live_gather_first_hop/outputs/metrics_2026-08-29_11-16-45.csv) + [`11-19-10.csv`](../tests/live_gather_first_hop/outputs/metrics_2026-08-29_11-19-10.csv). Working log: [`pda-knowledge-retrieval-assignment/TASK-04-decisions.md`](pda-knowledge-retrieval-assignment/TASK-04-decisions.md) “Gather first-hop gold chunks”. No SDD.  
**Author:** N/A  
**Created:** 2026-08-28  
**Target Completion:** 2026-08-29  
**SDD(s) Impacted:** none  
**Rollback:** `git checkout -- project/src/prompts/gather_agent.md`

This is the **only** file you read. Do not read other plans. Do not copy old prompt templates. Do not run other live boards as your score.

You have no other context. Everything you need is here. Success = **11/11 twice** on the **GT facts chunks** in the first search batch, **without data leakage**, with **mandatory synthetic `# Examples`**. **There is no stop rule.** Leakage invalidates the **run**, not the task.

**The only prompt you are allowed to edit is `project/src/prompts/gather_agent.md`.**  
**Under no circumstances touch Retrieve's prompt** (`project/src/prompts/retrieve_agent.md`) — not editing, not a «small fix», not an experiment candidate, not copying to production, not changing `tool_choice`, not a batch instead of isolated hops. Gather changes **according to** Retrieve, not the other way around.

---

## Friend review — these are what you will fail on

1. **Leakage is cheating.** You must not put in the prompt (`gather_agent.md`) evaluation-set questions, answers, article titles, `facts` / `citations` chunks, URLs, gold sub-questions, tool `question` strings, or «the same question with fake names». If the study material contains the test, the score is invalid even at 11/11.
2. **`# Examples` is mandatory — synthetic only.** A prompt without an `# Examples` section is forbidden. At least two `<user_query>` / `<assistant_response>` pairs in a made-up domain. If after hiding proper nouns the example still looks like Q01–Q11 — delete the pair and write another. Do not delete the entire section.
3. **Length is allowed.** Soft ceiling: up to **120 lines** and **1200 words**. If you exceeded — shorten duplications, do not delete `# Examples`.
4. **Vendor structure only.** Gather runs on `openai/gpt-4.1` (`OPENAI_GATHER_MODEL`). Retrieve / Grade / Answer stay on `OPENAI_MODEL` (`openai/gpt-4o-mini`). Gather outline:
   - `# Identity`
   - `# Instructions`
   - `# Examples` (**mandatory**, at least two synthetic pairs)
   - **Forbidden** `# Context` in the file. Runtime JSON is sent as the user message.
5. **No old template.** Do not leave `[INSTRUCTIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or Claude-style XML tags as the main outline.
6. **Wording is free vs GT, subject to Retrieve.** Do not try to match word-for-word to `sub_questions` or to `expected_tool_calls.arguments.question`. That is **not** the goal. Copying them is leakage. A sub-question that Retrieve can copy and that retrieves the gold chunk — passes even if the words differ from the GT. A sub-question that Retrieve cannot fill `source` / date from, or whose Top-1 is not the chunk — fails.

After every edit, before a run: open `gather_agent.md` and verify that all six items pass. Verify that `retrieve_agent.md` has **not** changed (`git diff` on it must be empty).

---

## Retrieve contract (frozen — Gather is written for it)

Retrieve is **already closed**: 11/11 twice on prepared GT hops (`tests/live_retrieve_gt`, `metrics_2026-08-28_18-12-29.csv` + `18-18-29`). The code calls `run_retrieve` **once per string**, with `tool_choice="search_facts"`. Each call sees **only** that string as the user message. No parent question. No siblings. No list.

The frozen prompt does exactly this, in this order:

1. **`question`** = the entire user message **word for word**. No deletion, addition, reordering, rephrasing, or letter change.
2. **`source`** = only if **in that same string** an explicit newspaper name appears; copies only the newspaper name as-is. A newspaper also counts in attribution / reporting / coverage / article. Forbidden: a person, company, product, topic, or generic label. **If there is no newspaper in the string — `source` is empty.** Retrieve will not fill in a newspaper from the parent question or from a sibling.
3. **Publication dates** = only an explicit **article publication** window in that same string → `published_from` / `published_to` to an ISO day with offset (`T00:00:00+00:00` … `T23:59:59+00:00`). An **event** date stays in `question` and does not become a filter. Without a window in the string — no dates.
4. **One** `search_facts` call. Chroma returns **Top-1** (`RETRIEVAL_TOP_K=1`).

### What this requires of Gather

Every string you emit **is** Retrieve's user message. If the string does not contain what Retrieve knows how to extract — it is lost. Gather does not fill `source`. Gather does not call tools. Gather does not «fix» after Retrieve.

| If Gather writes… | Frozen Retrieve does… | The chunk |
|---|---|---|
| Two newspapers in one string | `source` empty | Usually a foreign article at Top-1 |
| Newspaper missing from the string (even if it is in the parent question) | `source` empty | The same failure |
| Newspaper on the wrong claim | `source` on the wrong search | A sibling's gold chunk is missing |
| Publication window missing from the string | No date filter | Q08 fails |
| Two claims / two articles in one string | One search, one Top-1 | One chunk is missing |
| A featured-in / name-only / third-comparison hop | A useless search | A wasted slot, gold missing |
| The same proper nouns in two strings from the same newspaper | Two Top-1s may be the same article | The second article is missing |
| An ability from article A with newspaper of article B | `source` of B, embedding of A | Chunk A is missing |

**A batch experiment (one Retrieve call on the entire list) failed: 8/11** vs 10/11 on isolated hops. Do not repeat it. Do not build a `live_gather_retrieve_once` board as the score. Production is an isolated hop; Gather must work with it.

---

## What this product is

The service answers news-facts questions over a **local** article index. Live loop:

```text
User question
    → Gather     (you)     List of independent sub-questions. No tools.
    → Retrieve   (frozen)    Loop: one string → one search_facts. Copies question, fills source / dates from the string only.
    → Tools      (code)     Runs search_facts against Chroma. Top-1 chunk per call. RETRIEVAL_TOP_K=1.
    → Grade      (frozen, outside the board)    enough / rewrite / missing_hop / empty_stop
    → Answer     (frozen, outside the board)
```

This board stops after the **first tools batch**. No Grade. No second Gather turn. No Answer.

**Gold chunk = a record in the GT file's `facts`** (`url` + `fact` sentence). The score requires that both appear in the first batch's evidence.

---

## What Gather is (your only task)

Take the user question and split it into a list of sub-questions each of which is **one Retrieve message**: one search that can return **one gold chunk**, with newspaper and publication window **inside** the string when the user named them.

Gather does **not** search. Gather does **not** fill `source`. Gather does **not** answer. Gather does **not** call tools. Gather does **not** change Retrieve.

### Input (already sent as the user message — do not write this JSON in the prompt)

```json
{"question": "<user question>", "prior_queries": [], "grade_note": ""}
```

The score is a first turn: `prior_queries` empty, `grade_note` empty.

### Output (already bound in code)

```text
sub_questions: list[str]
```

No tools. No other fields.

### How to split so Retrieve will bring the chunks (habits, not test rows)

Teach these in the prompt. Do not mention question identifiers in the prompt. Every rule here is **so that frozen Retrieve can copy and fill**.

- A side in a comparison, an ability in a list, an event, a side in `and` / `or`, a side in `before` / `after`, an event with a separate publication date — each one **its own string**, because Top-1 returns one chunk per call.
- Do **not** add a third hop for the comparison itself («did A happen before B?») after the two sides — Retrieve will waste a call and will not retrieve gold.
- If the user put a **newspaper on a claim**, the newspaper must be **inside** the claim's string, so Retrieve will fill `source`. Without `source`, Chroma mixes articles from all newspapers.
- A newspaper only on the claim that named it. Not on siblings. Retrieve will not transfer a newspaper from a sibling.
- If the same newspaper is on two claims — the newspaper in **both** strings. Two articles from the same newspaper require two strings with different proper nouns, otherwise the two Top-1s may be the same article.
- A **publication** window the user named stays in the sub-question text. Retrieve will fill ISO. An event date stays in the text as well (Retrieve will not turn it into a filter — and that is desired).
- Forbidden to pack two newspapers in one string — Retrieve will leave `source` empty.
- Forbidden a hop whose entire role is «did the newspaper featured the topic».
- Abilities: if three+ abilities in a list, two strings (first alone, the rest together) **only if** both strings carry the **same** first newspaper. An event that is not an ability (anniversary, opening) goes to the second newspaper **only**. Do not swap newspapers. Do not also duplicate the event onto the first newspaper.
- Two newspapers on the same topic without separate claims (unanswerable): two strings, one newspaper each, so Retrieve will fill `source` twice. No featured-in / CEO-filter as a separate hop.
- **Retry in production:** if there is a `grade_note`, only new strings. This board does not test retry, but the prompt must remain production-fit.

The score does **not** require inventory identical to `sub_questions`. It requires that the calls Retrieve built from your strings bring all `facts` records.

---

## What is not yours

| Domain | Who owns it | Why this is not Gather |
|---|---|---|
| `search_facts` arguments (`question` word for word, `source`, ISO dates) | Retrieve (frozen) | You put newspaper/window **in the string**. Retrieve copies and fills. |
| Source catalog / `run_resolve_source` | The retrieval service | After Retrieve fills `source`. |
| `RETRIEVAL_TOP_K` / Chroma ranking | Retrieval | Frozen at 1. Do not raise k. |
| Grade / Answer / `search_corpus` | Frozen | Outside the board. `agent: unbound` rows in the GT are not counted. |
| Hop inventory vs `sub_questions` | `live_gather_hops` board (not the score) | Gold wording is not the goal. |
| Retrieve batch / changing `retrieve_agent.md` | Forbidden | 8/11 experiment. Production is isolated. |

Failure remains yours if the split prevents Retrieve from filling or the embedding from hitting: packing newspapers, featured-in instead of a claim, newspaper on the wrong claim, omitting a publication window, two claims from the same newspaper with the same proper nouns, abilities with another article's newspaper.

A Top-1 miss **after** a string stands alone, the newspaper is in the string, and `source` is filled in `calls_*.csv` — that is ranking. You may rephrase the **type** of need so the embedding hits the chunk. Forbidden to paste the `fact` sentence. Forbidden to edit index / GT / k / Retrieve.

---

## Your task (the only pass)

**11/11** on the gold chunks of the 11 local GT questions in the first `search_facts` batch, with **zero leakage**, when frozen Retrieve runs **hop-by-hop**.

Edit **only** `project/src/prompts/gather_agent.md`.

**Pass:** the two newest consecutive `metrics_*.csv` files from `project/tests/live_gather_first_hop/outputs/`, the same Gather prompt, `first_hop_success=1` on all 11 rows, `prompt_leak_hit=0`, vendor structure, synthetic `# Examples`, no test lookalikes, and `retrieve_agent.md` unchanged.

`first_hop_success=1` means:

- `prompt_leak_hit=0`
- `runtime_error` empty
- An **answerable** question (`unanswerable=0`): every URL in `facts` is found in evidence **and every** `fact` sentence matches a snippet in evidence (`first_hop_gold_complete=1`). These are **the chunks**.
- An **unanswerable** question (Q04, Q09; `facts` empty): no gold chunks. They pass when there are enough calls with filled `source` for the named newspapers (`agent_source_call_count` ≥ `gt_source_required_count`).
- If the user named publication windows (`gt_dated_required_count` > 0, Q08): the batch fills date filters (`agent_dated_call_count` ≥ the count).
- On answerable questions with newspapers in the GT: also `agent_source_call_count` ≥ `gt_source_required_count` (without `source` the correct chunk usually does not arrive at Top-1).

The runner does **not** compare `sub_questions` wording to the GT. It compares evidence to `facts` in `project/src/data/ground_truth/Q01.json` … `Q11.json`.

---

## Which files to run (this board only)

Always from the inner `project/` directory.

**This is the 11/11 score. Use it every time.** It runs Gather then Retrieve **isolated** per string — the same contract as production.

```text
cd project
uv sync
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_gather_first_hop.run_live_gather_first_hop
```

You need a `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_GATHER_MODEL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, and `vector_stores/facts_chroma`.

There is a delay between questions. A few minutes to a quarter hour. No printing to the console. Success = a new CSV trio.

The runs send the 11 evaluation questions to OpenRouter. That is expected. Putting them in the prompt — not.

### Do not run these as your score

- `tests.live_gather_retrieve_once` — Retrieve batch. **8/11. Dead.** Not the score.
- `tests.live_gather_hops.run_live_gather_hops` — wording inventory vs `sub_questions`. **Not** the chunks.
- `tests.live_gather_gt.run_live_gather_gt` — full loop + Grade + stop
- `tests.live_retrieve_gt` — Retrieve on prepared GT hops (already 11/11, frozen; do not change it)
- `tests.gt_facts_union_topk` — oracle on GT sub-questions with k=5. Diagnosis only
- e2e, oracle-Answer, Grade boards

---

## Output files — where they go and how to read them

Every run writes a new trio under `project/tests/live_gather_first_hop/outputs/`. Nothing is overwritten. Open the **newest** stamp.

| File | What it is | How to use |
|---|---|---|
| `metrics_YYYY-MM-DD_HH-MM-SS.csv` | The results board. **This is N/11.** | Count rows with `first_hop_success=1`. |
| `hops_*.csv` | One row per **gold chunk** (`facts`) | `url_in_evidence` / `snippet_in_evidence`. No rows for Q04/Q09. |
| `calls_*.csv` | One row per `search_facts` | You see `question`, `source`, dates, packing, featured-in. If `source` is empty — Gather omitted a newspaper from the string or packed two. |

### `metrics_*.csv` columns that matter

- `first_hop_success` — 1 or 0. Target 11.
- `first_hop_gold_complete` — every gold URL+sentence in evidence (1 automatically on unanswerable).
- `url_recall` / `snippet_recall` — how many of the chunks arrived.
- `gold_url_count` — how many unique URLs in `facts`.
- `facts_call_count` vs `required_facts_calls` — excess calls (over-splitting) or shortage.
- `gt_source_required_count` vs `agent_source_call_count` — `source` empty because the string did not give Retrieve what to copy.
- `gt_dated_required_count` vs `agent_dated_call_count` — publication window missing from the string (Q08).
- `missing_urls` / `missing_titles` — which chunk is missing.
- `agent_queries` — the strings Retrieve **copied**, joined with ` | `.
- `prompt_leak_hit` — 1 zeros **all** success. Scans `gather_agent.md` **and also** `retrieve_agent.md`. Do not edit Retrieve; if it «leaked» that is an old bug, not your fix.
- `runtime_error` — 429 / network / parse. Wait, rerun **all** 11.

### How to read a miss (first check whether Retrieve received a string it can fill)

1. `calls_*.csv`: is there a call for every need? Is `source` filled when the user named a newspaper **in that same string**? Did Q08 fill dates because the window was in the text?
2. `hops_*.csv`: `url_in_evidence=0` or `snippet_in_evidence=0` — this chunk did not arrive.
3. If `source` is filled and the string stands alone and still `snippet_in_evidence=0` — Top-1 returned another article. Rephrase unique proper nouns for the need (without pasting the gold sentence).
4. If there is a featured-in hop / comparison-hop / name-hop in `agent_queries` — delete that hop **type** from the prompt.
5. If an ability from one article ran with `source` of another newspaper — fix newspaper assignment in the string, not Retrieve.

`missing_titles` / `gold_title` / a `fact` sentence in the GT are allowed **to read** in order to understand which article is missing. **Forbidden** to paste them in the prompt.

429 → wait, run all 11 again. Do not edit a prompt because of a network fault.

---

## What counts as a gold chunk (do not paste the sentences in the prompt)

The `facts` field in every `Q0N.json`. Not `corpus`. Not `citations` (they are the same sentences for Answer). Not `search_corpus`.

| ID | `facts` chunks | Unanswerable | What the search must bring (so Retrieve succeeds) |
|---|---|---|---|
| Q01 | 2 | no | Two different Sporting News articles; newspaper in **both** strings; different proper nouns per game |
| Q02 | 2 | no | TechCrunch in one string, The Verge in the second; no third comparison-hop |
| Q03 | 3 | no | Three needs, no newspapers — Retrieve will leave `source` empty, and that is correct |
| Q04 | 0 | yes | Two strings, one newspaper each, so that `source` is filled twice |
| Q05 | 3 | no | Two needs without The Age, last need with The Age only inside the string |
| Q06 | 2 | no | The Age in one string, The Guardian in the second — the newspaper must appear **in the string** |
| Q07 | 3 | no | Two **different** TechCrunch articles (first ability vs debug/music) with TechCrunch in **both** strings + an Engadget article (anniversary) with Engadget in the string. Do **not** put debug/music on Engadget |
| Q08 | 2 | no | Independent Travel in both strings; publication window in the text for each date; Zermatt+Vail together, Tremblant alone |
| Q09 | 0 | yes | Two calls with `source` (the two named newspapers, each in its own string) |
| Q10 | 2 | no | Investment amount at one newspaper in a string; founding at the second newspaper in a string. There is **no** requirement for the word `figure` on this board |
| Q11 | 2 | no | Two sides, the same newspaper in **both** strings, two articles, different proper nouns |

Do not mention the table in the prompt. Do not paste URLs / titles / `fact` sentences.

---

## Leakage check (do it yourself)

After every edit, search in `gather_agent.md` against:

- `project/src/data/questions.json`
- `project/src/data/ground_truth/Q01.json` … `Q11.json`

A full question, `fact` sentence, title, URL, gold sub-question, or `arguments.question` from these files — you leaked. Delete.

The runner sets `prompt_leak_hit=1` on strings ≥24 characters from both prompts. Test lookalikes are **not** caught automatically. That is still on you. Do not «clean» a leak in Retrieve — do not touch it.

---

## Prompt structure per the vendor (mandatory to stick to)

```markdown
# Identity
...

# Instructions
...

# Examples
```

`# Examples` is **mandatory**. Inside the section only:

```text
<user_query>
...
</user_query>
<assistant_response>
...
</assistant_response>
```

Example input: `{"question":"...","prior_queries":[],"grade_note":""}`. Output: `{"sub_questions":[...]}`.

The examples must show strings Retrieve can swallow: newspaper **inside** the claim when there is a newspaper; not two newspapers in a string; publication window in the text when there is a window; different proper nouns for two articles from the same newspaper.

English only in the file. No code, env, secrets. Context is not written in the prompt.

Start from the **current** `project/src/prompts/gather_agent.md` (10/11). Do not restore `tests/live_gather_gt/inputs/control.md` or `tests/live_gather_first_hop/inputs/control.md` (old templates). Do not restore Marsh Courier / Oak mill / Vale Post.

Do not restore the «write `figure` in the singular» rule only because the hops board required it — this board does not require the word. If a «without amount» side already retrieves the founding chunk, that passes.

---

## Synthetic examples — mandatory, you will build them yourself

1. Fake domain. Pebble Dispatch / Lichen Record / brine pump are already in use; if they failed as a Q07 lookalike — replace the domain. Do not recycle Oak mill / Harbor Gazette / Marsh Courier / Vale Post.
2. At least two pairs. Prefer teaching the **Retrieve contract**: two sides with a newspaper inside each string; not featured-in; two articles from the same newspaper with different proper nouns; publication window in the text; abilities stay with the first newspaper and a non-ability event with the second — without a Q07 skeleton after hiding names.
3. Hide proper nouns: if it is still Q01/Q04/Q07/Q08/Q10 — replace the pair.
4. Examples for a **retrieval habit that Retrieve can copy**, not for duplicating gold inventory.

---

## In / out

**Edits:**

- `project/src/prompts/gather_agent.md` **only** as a prompt
- Snapshots `project/tests/live_gather_first_hop/inputs/candidate_<name>.md`

**Allowed to read (not to edit):**

- This plan
- `project/tests/live_gather_first_hop/README.md` and the runner
- `project/src/agents/gather_agent.py`, `retrieve_agent.py` (how it is loaded, what is sent) — without changing
- `project/src/prompts/retrieve_agent.md` — **read only, locked**
- `project/src/data/questions.json`, `ground_truth/README.md`, `Q01.json`–`Q11.json` — to understand which chunk is missing, not to copy into the prompt
- New CSVs under `project/tests/live_gather_first_hop/outputs/`

**Forbidden to edit:**

- **`retrieve_agent.md` — under no excuse**
- `grade_agent.md`, `answer_agent.md`
- GT JSON, `questions.json`, `answers.json`
- agents, tools, services, repositories, orchestration, `conts.py`, `RETRIEVAL_TOP_K`
- `tests/live_gather_hops`, `tests/live_gather_gt`, `tests/live_retrieve_gt`, `tests/live_grade_gt`, `tests/live_gather_retrieve_once`
- Indexes
- The runner's scoring rules (do not «fix» gold by loosening the board)

Do not add agents. Do not bind tools to Gather. Do not change Retrieve to unpack a packed string or to accept a list at once. **One named hypothesis** per live run.

---

## Loop

1. **No zero baseline.** The production prompt is a 10/11 candidate. Continue from it. Do not run again «without an edit» as a mandatory step unless you lost the state.
2. Snapshot Gather to `project/tests/live_gather_first_hop/inputs/candidate_<short_hypothesis_name>.md`.
3. Edit **only** `gather_agent.md`. One named change, aimed at the Retrieve contract. Synthetic `# Examples` remains.
4. Check friend-review, search against GT strings, and verify that `retrieve_agent.md` did not change.
5. Run the score command (`live_gather_first_hop` only).
6. Open the newest `metrics_*.csv`. Count `first_hop_success=1`. On misses: `calls_*.csv` first (`source` / dates), then `hops_*.csv`.
7. If 11/11 — run **again without a prompt edit**. Two consecutive files are the pass.
8. If not — one new named hypothesis that fixes how the string looks **to Retrieve**. Repeat.

Do not «fix» gold by editing GT. Do not recommend raising k, a supervisor, additional agents, or changing Retrieve without a new explicit approval from the user.

Do not recommend again a stronger Gather model as a first lever. The round is `openai/gpt-4.1`. Retrieve stays `gpt-4o-mini` and frozen.

---

## Result — 2026-08-29 (closed)

11/11 `first_hop_success` twice, same Gather, frozen Retrieve, `prompt_leak_hit=0`, synthetic `# Examples`. Candidate: `candidate_featured_in_abilities_first_outlet.md`. Do not continue the chunks board as the score; Grade/stop and e2e are the next stage.

---

## Current state — 2026-08-28 (archive before the close)

### What is already closed (do not touch)

- **Isolated Retrieve:** 11/11 twice on prepared GT hops. `retrieve_agent.md` frozen. Copies `question` word for word and fills `source` / dates **only from the string**.
- **Answer on perfect evidence (oracle):** 11/11. Out of scope.
- **Retrieve batch (one LLM call on the entire list):** tried and failed. `live_gather_retrieve_once` / `metrics_2026-08-28_22-30-09.csv` = **8/11**. Regressions: Q01 Top-1; Q06 without `source` on The Guardian; Q07 the same miss. **Do not repeat.**

### Why we left the hops board

`live_gather_hops` scores **inventory structure** vs `sub_questions`. That is a proxy. It does **not** check whether Chroma returned the chunk, nor whether Retrieve filled `source` from the string.

Do not optimize for the word `figure` unless the chunk itself is missing.

### Chunks-board peak (your base now)

The production prompt is `candidate_abilities_first_outlet_example.md`. Several candidates reached **10/11** on `live_gather_first_hop` with `openai/gpt-4.1`. All fall on **Q07** only.

| Stamp | Candidate | N/11 | Q07 |
|---|---|---|---|
| `21-43-32` | baseline hop-inventory (Marsh/Oak/Vale) | 8/11 | packing + clone per newspaper |
| `21-52-27` | `split_listed_claims` | 10/11 | generate→TC; debug/music→Engadget; anniversary→Engadget |
| `21-58-01` | `abilities_keep_first_outlet` | 10/11 | packing all abilities + clone |
| `22-04-21` | `split_abilities_second_outlet_event` | 10/11 | over-split 8 calls, duplicate per newspaper |
| `22-10-33` | `no_cross_product_pair_abilities` | 10/11 | debug/music pair correct, **newspapers reversed** |
| `22-22-14` | `abilities_first_outlet_example` (production until the close) | 10/11 | generate→TC; debug/music→Engadget; anniversary→Engadget |
| `22-30-09` | same Gather + Retrieve batch | 8/11 | do not repeat |

Passing at 10/11: Q01–Q06, Q08–Q11.  
Q07 remains: the TechCrunch chunk «One year later…» (debug code / compose music) is missing, because Gather put the pair on **Engadget**. Retrieve copies `source=Engadget` and cannot fix it. Correct assignment that Retrieve will succeed with: first ability + TechCrunch; debug+music + TechCrunch (proper nouns different from the first); anniversary + Engadget only.

Q01 at 10/11 works with strings «What did the Sporting News report about…» and with yes-no; sometimes Top-1 drops it without a split change (see batch 8/11). Do not break the Sporting News assignment in both strings.

### What to try now (one named hypothesis)

The goal: every string is a Retrieve message whose Top-1 is the gold chunk of this need.

- **Q07:** two ability strings with **the first newspaper only**; a non-ability-event string with **the second newspaper only**. Do not swap. Do not duplicate. Not featured-in.
- Split two articles from the same newspaper with **different** proper nouns
- Put a newspaper inside the claim, not as a featured-in hop — so Retrieve will fill `source`
- Do not pack two newspapers
- Do not add a comparison-hop after two sides
- Q08: two publication windows in the text, two places on the same date stay together
- Q04/Q09: two strings, one newspaper each
- Q06: The Guardian / The Age must appear **in the string**, not only in the parent question

**There is no stop rule.** Run until 11/11 twice without leakage. Every candidate must have synthetic `# Examples`.

After a regression: restore instructions that worked on **this board** (10/11), fix only the newspaper assignment of abilities vs event, run again. Do not touch Retrieve.

---

## There is no stop rule

Do not stop until two consecutive `metrics_*.csv` files with `first_hop_success=1` on all 11 rows, `prompt_leak_hit=0`, synthetic `# Examples`, and Retrieve unchanged. No run ceiling. A test lookalike = delete the pair, write another example, continue.

Do not edit Retrieve, Grade, Answer, k, or the graph. An interim report is allowed when there is 11/11 twice, or when the user asks for status. In status: CSV paths, N/11 per candidate, IDs that remain with `url_recall`/`snippet_recall` and `source` empty or not, the best `candidate_*.md` — and then continue.

---

## Message for the next chat (this board is closed)

Do not continue `live_gather_first_hop` as the score. Gather gold chunks in the first batch is closed (11/11 twice). Retrieve stays frozen. The next stage is Grade/stop and e2e, not editing `gather_agent.md` for this board.
