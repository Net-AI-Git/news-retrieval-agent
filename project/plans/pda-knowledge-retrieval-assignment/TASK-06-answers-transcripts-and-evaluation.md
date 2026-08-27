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

**Status:** Draft  
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

#### Gate 0 — Freeze the target (GT audit)

**What:** For each `Q01.json`–`Q11.json`, check that `answer`, `facts`/`corpus`, `citations`, `sub_questions`, and `expected_tool_calls` match the source files and the question text (especially temporal “before”/“after” and Yes/No conjunctions).

**How:** Read GT vs `src/data/facts.json` and `src/data/corpus.json`. For temporal items, compare `published_at` across the two gold articles. Do not use the model’s answer as evidence that GT is wrong.

**Pass:** A written keep / fix / unclear verdict per question. Unclear items stay open; they do not block Gates 1–3.

**Likely keep (verify, do not assume):** Q11 `No` is supported — expected-Gemini fact is 2023-11-30, lite-Gemini-Pro fact is 2023-12-09, so “after the lite release” is false. Q04/Q09 empty gold + refusal. Q01/Q03/Q07 already e2e-correct.

**Must verify:** Q02 “before” using Flipboard vs Verge `published_at`. Q08 “did coverage change” given two different Independent Travel articles on two dates. Q06/Q10 comparison claims vs the actual gold snippets (not vs the agent’s refusal).

**GT edit rule:** One documented reason per changed field. Prefer fixing a wrong snippet/date/sub-question over changing the short answer. Never edit GT because the agent refused.

#### Gate 1 — Isolated tool invocation (no agent, no Gather)

**What:** Call `RetrievalTools.search_facts` and `RetrievalTools.search_corpus` in process, with no LLM.

**Why first:** `search_corpus` is implemented and unit-tested, but `as_langchain_tools()` currently binds **only** `search_facts`. GT Q04/Q09 mark `search_corpus` as conditional after empty facts. The agent cannot call a tool that is not bound. Direct calls answer “can the tool run”; the bind list answers “can Gather call it”.

**How:** New named test package under `project/tests/` (own `README.md`). For each GT `expected_tool_calls` entry, invoke that tool with the recorded `arguments` (including Q08 `published_from`/`published_to`). Also call each tool with a known-empty query, invalid dates, and a known-hit query from Q01.

**Pass:**

- Both tools are in the LangChain bind list Gather actually receives.
- Direct calls return `ok` / `empty` / `invalid` as designed, never raw store internals.
- Q08 GT date-window calls are executed as recorded, not stripped.

Existing `tests/retrieval_tool_surface` covers mocked contracts. This gate is **live against the real Chroma stores** using GT argument payloads.

#### Gate 2 — Oracle RAG (GT queries, no Gather)

**What:** Retrieval quality when the query is the GT query, not the agent’s paraphrase.

**Why before blaming Gather:** `tests/gt_facts_union_topk` already shows the holes: answerable Success@5 **7/9**, misses **Q05 (The Age)** and **Q08 (Tremblant)**. Those hops are index/query/date-filter problems. They are not decompose problems until a GT query retrieves them.

**How:** Keep `gt_facts_union_topk` and `gt_corpus_union_topk`. Add (or extend) a runner that uses **exact** `expected_tool_calls` arguments, including date filters. Compare: GT-query recall vs agent-query recall vs date-filtered GT-query recall.

**Pass:** 9/9 answerable gold-URL Success on facts using GT required `search_facts` args (or a documented irrecoverable miss that forces a Gate 0 GT change). Q04/Q09 stay empty on facts.

**Do not:** Score Gather `too_early` as a Gather bug on a hop that is still red here.

#### Gate 3 — Oracle Answer (gold evidence injected, no Gather)

**What:** Run `run_answer` with evidence built from that question’s GT `facts` (empty list for Q04/Q09). No tools, no Gather.

**Why this exists:** This is how you test Answer **without** waiting for RAG. It is the missing test. Live e2e cannot do this job for Q05/Q08; it already can for Q02/Q06/Q10/Q11.

**Pass:** 9/9 answerable match GT short answers with GT citation titles; 2/2 unanswerable refuse with empty citations.

**Known expected reds today:** Q02 (refused vs Yes), Q06 (refused vs No), Q10 (refused vs No), Q11 (Yes vs No). Entity oracles Q01/Q03/Q07 should already pass and become regressions.

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

1. Gate 0 GT audit notes (keep in this TASK or a short log under the eval test `README`, not a new SDD unless one is requested).
2. Gate 1 live tool-call test package; bind `search_corpus` in `as_langchain_tools()` so the agent can actually call it.
3. Gate 3 oracle-Answer test package (inject GT facts).
4. Fix the e2e stop scorer so same-batch parallel is not `too_late` (Q03). Do not treat Q10 `failure_stage=rag` as a retrieval bug when Gather URL recall is 1.0.

**Exit:** You can say, per question, which gate is red. You are not yet chasing 11/11.

#### Phase B — Oracle RAG to 9/9 (Gate 2)

Do this **before** any Gather-decompose rewrite aimed at Q05/Q08.

Priority hops:

1. **Q08 Tremblant** — gold fact exists in GT; live agent and isolated GT-query both missed it; required date windows were not used (0/2). Try, in order: exact GT args **with** dates; query text closer to the gold sentence; `search_corpus` fallback on empty facts; top-k / embedding only if those fail.
2. **Q05 The Age** — same miss on oracle and agent. Entity text is already “Google”; e2e fails on the missing citation. Fix retrieval of that URL, not the Answer string.

Q10 oracle miss is **not** this phase’s e2e blocker (Gather already found both URLs). Still make the GT query retrieve The Age so Gate 2 is clean.

**Exit:** `gt_facts_union_topk` Success@5 = 9/9 on answerable questions. Only then may Q05/Q08 e2e Answer be believed.

#### Phase C — Oracle Answer to 11/11 (Gate 3) — parallel with Phase B

Highest e2e payoff. Safe to run in parallel because evidence is injected.

Change `src/prompts/answer_agent.md` (and only if needed, Answer schema/examples). Hypotheses to test **one at a time** via a prompt experiment directory under `project/tests/` (control vs candidate; promote only the winner):

1. **Use `published_at` for temporal Yes/No.** Snippets often lack dates; Q02/Q08/Q11 need article dates. Today the prompt both lists `published_at` on evidence and says “answer only when the claim is stated in a snippet” — that contradiction produces refusals.
2. **Cross-article Yes/No** (Q06, Q10): require both hops, then Yes/No on the conjunction, not refuse because snippets are not word-for-word the question.
3. **Confidence 4–5 refuse band:** keep it for empty/contradictory evidence; do not use it to refuse a fully supported No.
4. **Q11 polarity:** expected Gemini (30 Nov) is **before** lite Pro (9 Dec), so “after the lite report” is No. Oracle evidence already contains both snippets.

Do not loosen citation copying. Orchestration already drops paraphrased snippets. Entity questions Q01/Q03/Q07 are the regression set.

**Exit:** Gate 3 11/11. Projected live e2e if RAG is also green: 11/11. If RAG is still red, live e2e should still rise to **9/11** (all except Q05/Q08).

#### Phase D — Gather query, dates, stop (Gate 4)

Only on hops that passed Gate 2.

1. **Date filters on temporal questions** (Q08 required; Q02/Q11 may need dates in Answer even if Gather did not filter).
2. **Stop after empty required facts** (Gather example 02 already says this; Q04 ran 6 facts calls and hit the turn cap; Q09 added a third). Bind corpus so the conditional GT path is possible, then stop if corpus is also empty.
3. **No extra tools turn after gold is complete** (Q02 date-rewrites, Q07 extra hops). Parallel first-turn batches stay allowed.
4. **Decompose only where Gate 2 hits and the agent query misses.** Do not “improve overlap” on Q07’s packed query if gold is found.

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
| Q05 | fail | Gate 2 The Age URL | Oracle RAG, then citations come for free | Answer string (already Google) |
| Q06 | fail | Gate 3 (gold complete, refused No) | Comparison Answer | RAG |
| Q07 | pass | Gate 4 too_late only | Stop extra hops | Decompose (gold was found) |
| Q08 | fail | Gate 2 Tremblant + dates | Oracle RAG with GT date windows, then Answer if still refusing | Answer-first |
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

## Success Criteria

- Gate 1: both tools bound; GT argument payloads runnable against live stores.
- Gate 2: 9/9 answerable gold-URL success on GT `search_facts` args.
- Gate 3: 11/11 oracle-Answer (9 answers + 2 refusals).
- Gate 5: 11/11 `e2e_success=1` on `end_to_end_gt_evaluation`.
- Any GT change has a one-line reason pointing at source facts/corpus, not at model output.
- Assignment interface (`solution.py`) unchanged.

## Definition of Done (this continuation only)

- [ ] Gate 0 audit recorded for all 11 questions.
- [ ] Gate 1 live tool-call test exists and passes; `search_corpus` is bound for Gather.
- [ ] Gate 2 facts Success@5 is 9/9 or an irrecoverable miss is turned into a Gate 0 GT fix.
- [ ] Gate 3 oracle-Answer test exists and is 11/11.
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

- Whether Q08 “did coverage change” is fairly a Yes given two different listicles, or whether Gate 0 should re-label it after reading both articles.
- Whether binding `search_corpus` on Q04/Q09 should be required for e2e (refusals already pass) or only for GT tool-policy completeness.
- Prompt-experiment model/budget for Gate 3 — keep using the same cheap OpenRouter model as production, one hypothesis per run.
