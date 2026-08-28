# TASK 06 — Answers, Transcripts, and Evaluation

**Status:** In Progress  
**Author:** N/A  
**Created:** 2026-08-23  
**Target Completion:** TBD  
**Branch:** `feature/pda-6-answers-transcripts-evaluation`

## Goal

Run the completed system across all eleven questions, create the required machine-readable answers and decision transcripts, and evaluate grounding, refusals, and multi-step behavior before delivery.

## Product Requirements

- `answers.json` contains exactly one entry for each of the eleven question IDs and matches the required schema.
- Answers are short entity names, `Yes`, `No`, or an explicit refusal.
- Citations contain article titles and supporting snippets actually used by the agent.
- Transcripts capture the actual agent decisions and tool calls for all eleven runs, not only final answers.
- Evaluation distinguishes answer correctness, evidence support, citation traceability, tool-only compliance, and appropriate refusal.

## Research Before Implementation

- Define a repeatable evaluation matrix for direct, yes/no, temporal, multi-hop, and unanswerable questions.
- Decide what transcript detail is needed to prove genuine agent behavior without exposing credentials or unnecessary sensitive data.
- Determine how to audit that each citation supports the exact final claim and came from a tool result in the same run.
- Investigate deterministic settings, retry policy, and run-to-run variance within the available budget.
- Define how failures or incomplete runs are recorded without silently replacing them with hand-written answers.

## Implementation Autonomy

The developer chooses the runner, transcript format, evaluation tooling, model settings, and review workflow. The required artifacts and observable evidence are fixed; the internal evaluation architecture is not.

## Scope

**In:**

- Root `answers.json`.
- Developer-selected transcript and evaluation artifacts.
- A repeatable run across all eleven questions and a documented evidence audit.

**Out:**

- Manually inventing answers that were not produced by the system.
- Hiding failed tool calls or unsupported conclusions from transcripts.
- Redesigning the solution solely to optimize unseen ground truth.

## Success Criteria

- The output contains all and only the eleven expected IDs with no duplicates.
- Every non-refusal answer has at least one supporting citation, and every citation can be traced to its run transcript.
- Refusals occur when retrieved evidence is insufficient and are not padded with unsupported citations.
- Transcripts visibly demonstrate multi-step tool use where the question requires it.
- The full run completes within the documented cost and operational limits, or limitations are recorded honestly.

## Definition of Done

- [x] `answers.json` passes strict schema and ID-completeness validation.
- [x] All eleven answers were produced through the public solution path.
- [x] Transcripts exist for all eleven questions and show actual tool calls and decisions.
- [x] Each non-refusal citation is checked against the retrieved supporting text.
- [x] Tool-only answer-time access is verified for the recorded runs.
- [x] Multi-hop cases show evidence accumulation from the required number of sources when justified.
- [x] Unanswerable or unsupported cases refuse rather than guess.
- [x] Cost, retries, failures, and known quality limitations are recorded.
- [ ] The branch is independently reviewable and ready to merge. Answer quality vs ground truth is deferred.

## Final Deliverable

A schema-valid `answers.json`, complete agent transcripts for all eleven questions, and a repeatable evidence-based evaluation showing how each answer or refusal was produced.

## SDD(s) Impacted

- none

## Rollback Strategy

N/A — generated assignment artifacts can be regenerated from the merged system.

## Open Questions

- none

---

## Revision — 2026-08-27 — Path to 100% local-GT e2e

**Status:** In Progress — Gates 0–3 closed, including Gate 2 ranking (Top-1, no rerank). Gates 4–5 open.  
**Author:** N/A  
**Created:** 2026-08-27  
**Target Completion:** TBD  
**Baseline:** `project/tests/end_to_end_gt_evaluation/outputs/stage_eval_2026-08-26_19-54-27.csv` (5/11 e2e, 45%). Q03 `stop.verdict=too_late` in that file is a same-batch false positive; treat as `on_time`.

This continuation does **not** change the TASK 06 artifact work above. That work produced `answers.json`, transcripts, and the evaluation harness. Quality vs local ground truth was explicitly deferred. This section is the plan to close that gap.

The original TASK 06 out-of-scope line “Redesigning the solution solely to optimize unseen ground truth” still holds for the hidden evaluator set. This continuation targets the **local** GT under `project/src/data/ground_truth/` only.

---

### Goal

Reach **11/11 e2e pass** on the local GT runner (`tests/end_to_end_gt_evaluation`) without hand-writing answers, without changing GT to match a wrong model, and without using e2e as the first diagnostic.

100% means: for every question, the public `solution.answer` path produces the GT answer (including refusal on Q04/Q09) and, on answerable questions, every GT citation title. Isolated stage tests must be green **before** that e2e number is treated as real.

---

### Why the order is gates, not “biggest e2e pain first”

The 26 Aug run’s impact ranking (Answer 4/6 fails, RAG 2/6, over-search 4/11) is the right **payoff** ranking. It is the wrong **engineering** ranking if used as the first code change.

The pipeline is a ladder. A failure at a lower rung poisons every score above it:

1. If a tool cannot be invoked, Gather “query quality” is unmeasurable.
2. If the retriever misses gold on the **GT query itself**, Gather “bad decompose” is unmeasurable, and Answer on that question is unmeasurable in e2e.
3. If gold never enters evidence, Answer “false refusal” may be correct behavior.
4. If gold is already in evidence, Answer can be blamed in e2e — and can also be tested without Gather at all.

So: **measure downward, fix the first red gate, promote upward.** Do not start with “rewrite the Answer prompt” on a question whose gold URL was never retrieved. Do not start with “fix decomposition” on a hop whose GT query also misses.

You do **not** have to finish retrieval on every question before touching Answer. Four of the six e2e fails (Q02, Q06, Q10, Q11) already have complete gold in Gather evidence. Those Answer bugs are already isolatable. The two RAG misses (Q05, Q08) are not.

---

### Rejected orderings (do not do these)

- **Start with global decomposition work.** Token-overlap on Q07/Q10 looks weak while gold was still found. Decompose is only the diagnosis when oracle RAG hits and the agent query misses.
- **Use live e2e as the Answer test.** Q05/Q08 are contaminated by missing hops. Q10’s CSV `failure_stage=rag` is a scoring artifact (oracle GT query missed The Age; Gather URL recall was 1.0).
- **Finish stop-too-late first.** Q02/Q04/Q07/Q09 over-search. That did not cause the 6 e2e fails. It is cost, then a Gather prompt fix, after oracles are green.
- **Wait for 9/9 oracle RAG before any Answer work.** Wastes the 4 already-diagnosed Answer fails.
- **Edit GT so refusals count as success.** That is a fake 100%. GT changes only when the corpus/facts cannot support the labeled answer, or a GT field is factually wrong vs `facts.json` / `corpus.json`.

---

### Measurement ladder (run these as gates)

Each gate has a pass rule. A later gate is **not a fair exam** until the earlier one is green for that hop/question.

#### Gate 0 — Freeze the target (GT audit) — **Done** (2026-08-27)

**What:** For each `Q01.json`–`Q11.json`, check that `answer`, `facts`/`corpus`, `citations`, `sub_questions`, and `expected_tool_calls` match the source files and the question text (especially temporal “before”/“after” and Yes/No conjunctions).

**How:** Read GT vs `src/data/facts.json` and `src/data/corpus.json`. For temporal items, compare `published_at` across the two gold articles. Do not use the model’s answer as evidence that GT is wrong.

**Pass:** A written keep / fix / unclear verdict per question. Unclear items stay open; they do not block Gates 1–3.

**Likely keep (verify, do not assume):** Q11 `No` is supported — expected-Gemini fact is 2023-11-30, lite-Gemini-Pro fact is 2023-12-09, so “after the lite release” is false. Q04/Q09 empty gold + refusal. Q01/Q03/Q07 already e2e-correct.

**Must verify:** Q02 “before” using Flipboard vs Verge `published_at`. Q08 “did coverage change” given two different Independent Travel articles on two dates. Q06/Q10 comparison claims vs the actual gold snippets (not vs the agent’s refusal).

**GT edit rule:** One documented reason per changed field. Prefer fixing a wrong snippet/date/sub-question over changing the short answer. Never edit GT because the agent refused.

#### Gate 1 — Isolated tool invocation (no agent, no Gather) — **Done** (facts-only, 2026-08-27)

**What:** Call `RetrievalTools.search_facts` and `RetrievalTools.search_corpus` in process, with no LLM.

**Why first:** `search_corpus` is implemented and unit-tested, but `as_langchain_tools()` currently binds **only** `search_facts`. GT Q04/Q09 mark `search_corpus` as conditional after empty facts. The agent cannot call a tool that is not bound. Direct calls answer “can the tool run”; the bind list answers “can Gather call it”.

**How:** New named test package under `project/tests/` (own `README.md`). For each GT `expected_tool_calls` entry, invoke that tool with the recorded `arguments` (including Q08 `published_from`/`published_to`). Also call each tool with a known-empty query, invalid dates, and a known-hit query from Q01.

**Pass:**

- Both tools are in the LangChain bind list Gather actually receives.
- Direct calls return `ok` / `empty` / `invalid` as designed, never raw store internals.
- Q08 GT date-window calls are executed as recorded, not stripped.

Existing `tests/retrieval_tool_surface` covers mocked contracts. This gate is **live against the real Chroma stores** using GT argument payloads.

#### Gate 2 — Oracle RAG (GT queries, no Gather) — **Done** (2026-08-27)

**What:** Retrieval quality when the query is the GT query, not the agent’s paraphrase.

**Why before blaming Gather:** `tests/gt_facts_union_topk` already shows the holes: answerable Success@5 **7/9**, misses **Q05 (The Age)** and **Q08 (Tremblant)**. Those hops are index/query/date-filter problems. They are not decompose problems until a GT query retrieves them.

**How:** Keep `gt_facts_union_topk` and `gt_corpus_union_topk`. Add (or extend) a runner that uses **exact** `expected_tool_calls` arguments, including date filters. Compare: GT-query recall vs agent-query recall vs date-filtered GT-query recall.

**Pass:** 9/9 answerable gold-URL Success on facts using GT required `search_facts` args (or a documented irrecoverable miss that forces a Gate 0 GT change). Q04/Q09 have empty gold; they are not required to return `empty` from Top-1 (nearest noise is expected).

**Result (recall, Top-5):** `tests/live_search_facts_gt_calls` `outputs/metrics_2026-08-27_19-41-17.csv` (repeat of `19-37-44`): 11/11 `all_chunks_found=1`. Answerable 9/9 URL+snippet, including Q05 The Age and Q08 Tremblant. Source filter + relaxing the Facts floor after a resolved `source` closed Q05/Q08.

**Result (ranking, Top-1, current):** `outputs/metrics_2026-08-27_22-25-11.csv`. Same 9/9 gold; every matching hop has gold at rank 1; 0 false-positive URLs on answerable questions. No reranker. Q04/Q09 still return one non-gold chunk per hop — cosine cannot drop those without dropping Q08 gold (25.3%). Path and rejected alternatives: `TASK-03-decisions.md` (Ranking path). README: Traceable Retrieval Indexes → Ranking.

**Do not:** Score Gather `too_early` as a Gather bug on a hop that is still red here.

#### Gate 3 — Oracle Answer (gold evidence injected, no Gather) — **Done** (2026-08-27)

**What:** Run `run_answer` with evidence built from that question’s GT `facts` (empty list for Q04/Q09). No tools, no Gather.

**Why this exists:** This is how you test Answer **without** waiting for RAG. It is the missing test. Live e2e cannot do this job for Q05/Q08; it already can for Q02/Q06/Q10/Q11.

**Pass:** 9/9 answerable match GT short answers with GT citation titles; 2/2 unanswerable refuse with empty citations. The production prompt must not contain evaluation questions, their answers, or isomorphic few-shot of those items.

**Result:** Closed. Honest baseline was `metrics_2026-08-27_20-31-49.csv` (8/11). CSVs through `20-11-54` and round-1 `20-57-32` / `21-30-46` are invalid (eval items or isomorphic few-shot). Round 2 deleted those clones, kept OpenAI `# Identity` / `# Instructions` / format-only `# Examples`, and passed 11/11 on `21-56-37`, `21-58-37`, and independent re-run `22-16-19`. Prompt decisions: `TASK-04-decisions.md`. Spec: `project/plans/gate3-oracle-answer-prompt-goal.md`.

#### Gate 4 — Gather vs oracle (only hops that passed Gate 2)

**What:** Decomposition, tool choice, date filters, stop timing, waste.

**Diagnosis table:**

| Oracle RAG (Gate 2) | Agent query | Blame |
|---|---|---|
| hit | hit | Gather retrieval OK; look at stop / Answer |
| hit | miss | Decompose / query wording / missing date filter |
| miss | miss | Still Gate 2; do not “fix Gather” |
| miss | hit | Agent query luck; keep the oracle green anyway |

**Stop rules (after the hop is retrievable):**

- `too_early` — stopped while a Gate-2-green hop is still missing from evidence.
- `too_late` — another **tools turn** after gold URLs were already complete, or extra facts calls on unanswerable after the required empty searches.
- `on_time` — otherwise (do not treat same-turn parallel calls as `too_late`).

**Pass:** On Gate-2-green hops, agent queries retrieve gold. Unanswerable: required facts calls, then stop (corpus only if still bound-and-empty). No second tools turn after gold complete on answerable questions.

#### Gate 5 — Full e2e (joint exam, last)

**What:** Existing `tests/end_to_end_gt_evaluation` on all 11, public `solution.answer` path.

**Pass:** 11/11 `e2e_success=1`, `failure_stage=none`. Then regenerate root `answers.json` and transcripts through the same public path.

If Gate 3 is green and Gate 5 is red on that question, the bug is Gather/wiring, not Answer. If Gate 2 is green and Gate 5 still misses gold, the bug is Gather query/stop. If Gate 5 fails with gold in evidence, the bug is Answer or citation filter — Gate 3 should have caught it.

---

### Fix phases (what to change, in this order)

Work follows the ladder. Payoff from the 26 Aug run is used **inside** a gate (which Answer bug first), not to skip gates.

#### Phase A — Honest scoreboard (no production prompt changes)

1. [x] Gate 0 GT audit notes (keep in this TASK or a short log under the eval test `README`, not a new SDD unless one is requested). See “Gate 0 audit — 2026-08-27”.
2. [x] Gate 1 live tool-call test package (`tests/live_search_facts_gt_calls`). `search_corpus` stays unbound (facts-only product).
3. [x] Gate 3 oracle-Answer test package (`tests/oracle_answer_gt`). Earlier 11/11 CSV is invalid (eval items in the prompt).
4. Fix the e2e stop scorer so same-batch parallel is not `too_late` (Q03). Do not treat Q10 `failure_stage=rag` as a retrieval bug when Gather URL recall is 1.0.

**Exit:** You can say, per question, which gate is red. You are not yet chasing 11/11.

#### Phase B — Oracle RAG to 9/9 (Gate 2) — **Done** (2026-08-27)

Do this **before** any Gather-decompose rewrite aimed at Q05/Q08.

Priority hops:

1. [x] **Q08 Tremblant** — gold fact exists in GT; live agent and isolated GT-query both missed it; required date windows were not used (0/2). Closed by GT date windows + `source` = Independent Travel + relaxed min-similarity after the source filter. Live hop `url_hit=1` / `snippet_hit=1` at 25.3%.
2. [x] **Q05 The Age** — same miss on oracle and agent. Closed by `source` = The Age + relaxed min-similarity. Live hop `url_hit=1` / `snippet_hit=1` at 30.7%.

Q10 oracle Age hop also hits on the GT query (`19-41-17` / `19-37-44`).

3. [x] **Ranking after 9/9 recall** — Top-5 unions were too large for Answer. Tried NVIDIA OpenRouter rerank (`llama-nemotron-rerank-vl-1b-v2:free`) and one-fact-per-URL collapse; both rejected. Per-hop gold is already rank 1. Shipped `RETRIEVAL_TOP_K=1`, no rerank (`metrics_2026-08-27_22-25-11.csv`). Q04/Q09 noise is Gate 4/Answer, not a retrieval cutoff.

**Exit:** Live GT `search_facts` args: 9/9 answerable gold URL+snippet at rank 1, no extra answerable URLs. Q05/Q08 e2e Answer may now be believed **if** Gather actually retrieves those hops. Ranking decisions: `TASK-03-decisions.md`.

#### Phase C — Oracle Answer to 11/11 (Gate 3) — **Done** (2026-08-27)

Highest e2e payoff. Safe to run in parallel because evidence is injected.

Change `src/prompts/answer_agent.md` (and only if needed, Answer schema/examples). Hypotheses to test **one at a time** via a prompt experiment directory under `project/tests/` (control vs candidate; promote only the winner):

1. **Use `published_at` for temporal Yes/No.** Snippets often lack dates; Q02/Q08/Q11 need article dates. Today the prompt both lists `published_at` on evidence and says “answer only when the claim is stated in a snippet” — that contradiction produces refusals.
2. **Cross-article Yes/No** (Q06, Q10): require both hops, then Yes/No on the conjunction, not refuse because snippets are not word-for-word the question.
3. **Confidence 4–5 refuse band:** keep it for empty/contradictory evidence; do not use it to refuse a fully supported No.
4. **Q11 polarity:** expected Gemini (30 Nov) is **before** lite Pro (9 Dec), so “after the lite report” is No. Oracle evidence already contains both snippets.

Do not loosen citation copying. Orchestration already drops paraphrased snippets. Entity questions Q01/Q03/Q07 are the regression set.

**Exit:** Met. 11/11 on two consecutive CSVs plus an independent re-run; prompt has no eval items and no isomorphic few-shot. See Gate 3 Result. Next is Phase D / Gate 4.

#### Phase D — Gather query, dates, stop (Gate 4)

Only on hops that passed Gate 2.

1. **Date filters on temporal questions** (Q08 required; Q02/Q11 may need dates in Answer even if Gather did not filter).
2. **Stop after empty required facts** (Gather example 02 already says this; Q04 ran 6 facts calls and hit the turn cap; Q09 added a third). Bind corpus so the conditional GT path is possible, then stop if corpus is also empty.
3. **No extra tools turn after gold is complete** (Q02 date-rewrites, Q07 extra hops). Parallel first-turn batches stay allowed.
4. **Decompose only where Gate 2 hits and the agent query misses.** Do not “improve overlap” on Q07’s packed query if gold is found.

Prompt-only Gather stalled at 7/11 (`too_early` / missing gold on Q05/Q07 across dedicated runs). A Grade node after tools now routes `enough` / `rewrite` / `missing_hop` / `empty_stop`. Decision: `TASK-04-decisions.md`.

**Exit:** Stop `too_late` only when a later tools turn is real. Q05/Q08 `too_early` disappears once those hops retrieve gold.

#### Phase E — Joint e2e and artifacts (Gate 5)

Re-run `tests/end_to_end_gt_evaluation`. Target 11/11. If any remain:

- Gold missing → back to Gate 2/4, not Answer.
- Gold present, wrong/refused → back to Gate 3.
- Model right, GT wrong → Gate 0 edit, then re-run.

Regenerate root `answers.json` and transcripts via `solution.py`. Record remaining limitations honestly if 11/11 is blocked by an irrecoverable index miss after Gate 0.

---

### Per-question playbook (from the 26 Aug run)

| ID | E2E now | First red gate | Work | Do not start with |
|---|---|---|---|---|
| Q01 | pass | none | Regression | Anything |
| Q02 | fail | Gate 3 (gold complete, refused Yes) | Temporal Answer + stop extra date queries | RAG, decompose |
| Q03 | pass | none (stop label was wrong) | Regression; fix scorer | Stop-policy “too late” |
| Q04 | pass | Gate 1 bind + Gate 4 stop | Bind corpus; stop after empty | Answer |
| Q05 | fail | Gate 4 (oracle RAG now hits The Age) | Gather must pass `source` / keep the hop; then citations | Answer string (already Google) |
| Q06 | fail | Gate 3 (gold complete, refused No) | Comparison Answer | RAG |
| Q07 | pass | Gate 4 too_late only | Stop extra hops | Decompose (gold was found) |
| Q08 | fail | Gate 4 (oracle RAG now hits Tremblant with source+dates) | Gather source+dates, then Answer if still refusing | Answer-first |
| Q09 | pass | Gate 4 extra empty call | Stop policy; bind corpus | Answer |
| Q10 | fail | Gate 3 (Gather gold complete) | Comparison Answer; ignore CSV `rag` label | Index work as the e2e fix |
| Q11 | fail | Gate 3 (gold + citations, Yes vs No) | Temporal polarity | RAG, citations |

Parallel tracks after Phase A: **B = Q05+Q08 RAG**, **C = Q02+Q06+Q10+Q11 Answer**. Merge in Phase E.

---

### Independent tool-call program (detail)

Purpose: prove tools work **without** an LLM in the loop.

1. Load env + Chroma paths the same way `solution.py` does.
2. Instantiate `RetrievalTools`.
3. Assert `as_langchain_tools()` names include `search_facts` and `search_corpus`.
4. For every required GT tool row: call the method with `arguments`; store status, hit count, gold-URL hit count.
5. For every conditional corpus row (Q04, Q09): call `search_corpus` after empty facts; expect empty, not a crash.
6. Negative cases: empty query / bad dates → `invalid` or `empty` as specified today.
7. Q08: one run **without** dates (today’s agent behavior) and one run **with** GT windows; compare Tremblant gold-hit. That single pair tells you whether the miss is wording, date filtering, or the index.

No Gather, no Answer, no `answers.json` writes.

---

### Scope

**In:**

- GT files under `project/src/data/ground_truth/` only after a Gate 0 written reason.
- `project/src/tools/retrieval_tools.py` bind list; retrieval query/date/top-k behavior if Gate 2 requires it.
- `project/src/prompts/answer_agent.md` and `gather_agent.md` via prompt experiments then promotion.
- New test packages under `project/tests/` for live tool calls and oracle Answer (each with `README.md`).
- Existing `gt_facts_union_topk`, `gt_corpus_union_topk`, `end_to_end_gt_evaluation` runners/READMEs.
- Regenerated root `answers.json` and transcripts after Gate 5.

**Out:**

- Hand-authored answers in `answers.json`.
- Editing GT to match a refusal or a wrong Yes/No.
- Optimizing for an unseen evaluator GT set.
- Knowledge-graph bonus, MCP, TASK 07 README (except later documenting the real failure modes).
- Using live e2e as the first Answer or first RAG test.

---

### Gate 0 audit — 2026-08-27

**Status:** Complete. **Verdict: keep all 11.** No GT field changed.

**Scope of this pass:** `questions.json` + `Q01.json`–`Q11.json` vs `src/data/facts.json` only. Corpus was not audited (product no longer uses it). `expected_tool_calls` rows that name `search_corpus` on Q04/Q09 were not treated as answer/gold defects.

**Method:** Exact `url`+`fact` match into `facts.json` (title, source, category, `published_at` also compared). Citations checked against the same-file GT facts. Temporal items used gold `published_at`, not model output. Unanswerable items were grepped in `facts.json` for the named entities/outlets.

**Mechanical result:** 11/11 question texts match `questions.json`. Every gold fact on the 9 answerable questions is an exact `facts.json` row (no title/source/date drift). Every citation title+snippet equals its GT fact. `facts.json` has 251 rows / 150 URLs.

| ID | Answer | Verdict | Why |
|---|---|---|---|
| Q01 | Yes | keep | Both Sporting News hops are in the store. Cowboys beat Seattle in Week 13; Lions beat Green Bay 34–20 (TNF 28 Sep, Week 4 — the question does not require the same week). Conjunction holds. |
| Q02 | Yes | keep | Flipboard/TechCrunch `2023-12-18T16:00:49Z` is before Verge ActivityPub structure `2023-12-19T13:00:00Z`. Snippets have no dates; the temporal claim is on `published_at`. That is an Answer-prompt issue later, not a GT error. |
| Q03 | Sam Bankman-Fried | keep | Three hops name SBF / Bankman-Fried for the $14B instruction, alleged fraud, and Jane Street → Alameda/FTX recruit. |
| Q04 | Insufficient information | keep | Gold empty. `facts.json` has no Pets Best, pet insurance, WSJ, or Forbes. The only NYT row is an unrelated NFL Athletic piece. Refusal is the labeled success. |
| Q05 | Google | keep | Antitrust siphoning, Gemini Pro vs GPT-3.5, and Age “foul play on Google’s part” are all in the store under those URLs. |
| Q06 | No | keep | Age: people with an Aboriginal ancestor are not the same as Aboriginal identity — “a very long and different journey.” Guardian: Indigenous people “need to be heard.” Same identification process? No. Guardian is not about the same axis, but Age already falsifies “the same.” |
| Q07 | ChatGPT | keep | TechCrunch: general-purpose text chatbot; TechCrunch: debug code / compose music; Engadget: first anniversary. |
| Q08 | Yes | keep | Independent Travel 13 Oct = global luxury listicle (Zermatt → Vail). 25 Oct = Canada holidays, Tremblant/Quebec section. Different destinations and angle after the named date. Yes is fair. Date windows on the GT tool rows match those UTC calendar days. |
| Q09 | Insufficient information | keep | Gold empty. No Forerunner, space-exploration, Forbes, or BBC-space rows. The only BBC row is Taylor Swift / Entertainment & Arts. |
| Q10 | No | keep | TechCrunch gold fact *specifies* Microsoft’s investment as “around $10 billion,” so “unspecified” is false and the conjunction is false. Age gold is founding in late 2015; the three store facts on that Age URL also have no dollar figures. |
| Q11 | No | keep | Expected-Gemini TechCrunch `2023-11-30T14:10:43Z` is *before* lite Gemini Pro `2023-12-09T21:16:17Z`. “After the lite report” is false. |

**Must-verify items (closed):**

- Q02 “before”: Flipboard 18 Dec 16:00 UTC vs Verge 19 Dec 13:00 UTC — ~21h earlier. Keep Yes.
- Q08 “did coverage change”: two different Independent Travel listicles (luxury worldwide vs Canada / Tremblant). Keep Yes. Not a GT re-label.
- Q06/Q10 vs gold snippets: both `No` answers are supported by the store sentences, not by the agent’s refusals.
- Q11 polarity: keep No.

**Notes that are not GT edits:**

- Q08 Tremblant gold sentence never contains the word “Tremblant” (“Quebec’s premier ski resort” / “eponymous mountain”). Title + URL identify it. Stronger snippet is optional later; answer stays Yes.
- Q02/Q08/Q11 snippets omit dates. Gold `published_at` is what makes the temporal Yes/No true. Gate 3 prompt work, not Gate 0.
- Q04/Q09 `expected_tool_calls` still list conditional `search_corpus`. Irrelevant to the short answer while the product is facts-only. Leave those rows unless a later gate changes tool-policy scoring.

**GT edit rule this pass:** no fields changed.

### Source filter + GT tool args — 2026-08-27 — **Done**

Optional `source` on `search_facts`: catalog JSON next to Facts Chroma (unique outlet names + embeddings, written at index time), resolve by exact then unique substring then nearest-with-margin, then Chroma `where source == canonical`. Unresolved names drop the filter. After a resolved source, the 0.35 facts floor is not applied.

**GT `expected_tool_calls` only:** added `arguments.source` when that sub-question names an outlet (wording from the question, not a forced canonical string). Answers, facts, citations, and dates were not changed. Q03 hops name no outlet — no `source`. Q05 hops 1–2 name no outlet — `source` only on hop 3 (`The Age`). Q04/Q09 corpus rows unchanged.

Reason per field: the named outlet is in the sub-question text, so the oracle tool call must pass `source` the same way Gather is instructed to.

Live `tests/live_search_facts_gt_calls`: `outputs/metrics_2026-08-27_19-41-17.csv` and `19-37-44` both 11/11 `all_chunks_found=1` (9/9 answerable). Q05 Age 30.7%, Q08 Tremblant 25.3%. An earlier `19-28-26` run already had those two hops but Q09–Q11 were `invalid` from OpenRouter 429; that is not a retrieval miss.

## Success Criteria

- Gate 1: both tools bound; GT argument payloads runnable against live stores.
- Gate 2: 9/9 answerable gold-URL success on GT `search_facts` args.
- Gate 3: 11/11 oracle-Answer (9 answers + 2 refusals), prompt free of eval items and of isomorphic few-shot.
- Gate 5: 11/11 `e2e_success=1` on `end_to_end_gt_evaluation`.
- Any GT change has a one-line reason pointing at source facts/corpus, not at model output.
- Assignment interface (`solution.py`) unchanged.

## Definition of Done (this continuation only)

- [x] Gate 0 audit recorded for all 11 questions.
- [x] Gate 1 live `search_facts` GT-arg test exists and passes (`tests/live_search_facts_gt_calls`). `search_corpus` is not bound (facts-only).
- [x] Gate 2 facts Success on GT `search_facts` args is 9/9. First close: Top-5 `metrics_2026-08-27_19-41-17.csv`. Ranking close: Top-1, no rerank, `metrics_2026-08-27_22-25-11.csv`.
- [x] Gate 3 oracle-Answer test exists (`tests/oracle_answer_gt`).
- [x] Gate 3 is 11/11 with a prompt that does not contain evaluation items or isomorphic few-shot of them (`21-56-37`, `21-58-37`, `22-16-19`).
- [ ] Gate 4 stop/date/decompose changes only on hops that passed Gate 2.
- [ ] Gate 5 e2e CSV is 11/11.
- [ ] `answers.json` and transcripts regenerated from the public path.
- [ ] Original TASK 06 schema/transcript obligations still hold.

## Final Deliverable

A system that still emits schema-valid `answers.json` and transcripts through `solution.py`, plus stage tests that prove tools, oracle RAG, and oracle Answer separately, and a local-GT e2e CSV with 11/11 pass.

## SDD(s) Impacted

- none (same as the parent TASK; no per-feature SDD exists for this assignment)

## Rollback Strategy

Revert prompt, bind-list, and retrieval changes on this branch; restore any GT JSON from git; regenerate `answers.json` from the last green public run. Evaluation CSVs are disposable outputs.

## Open Questions (this continuation)

- Q08 “did coverage change”: closed in Gate 0 — keep Yes (luxury worldwide 13 Oct vs Canada/Tremblant 25 Oct).
- Whether Q04/Q09 `search_corpus` expected rows should be dropped from GT now that the product is facts-only (refusals already pass). Not an answer-label issue.
- Prompt-experiment model/budget for Gate 3 — closed: same cheap OpenRouter model as production; vendor-shape Answer prompt; no eval few-shot.
