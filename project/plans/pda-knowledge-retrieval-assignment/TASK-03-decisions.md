# TASK 03 — Decision Log

**Status:** Done  
**Scope:** Retrieval tool surface only. Agent loop stays in TASK 04.

Closed decisions stay here with the trade-off that justified them. Open items stay listed until chosen.

---

## Closed

### Two tools: `search_facts` then `search_corpus`

Chosen earlier. Facts first for compact answers; Corpus for follow-up and cross-article context. Not a single combined search (weaker store selection). Not a third lookup-by-article tool (deferred).

### LangGraph binding: wrap existing methods; index stays on the instance

**Choice:** Expose `search_facts` and `search_corpus` to LangGraph as `StructuredTool` / `@tool` wrappers around the bound instance methods. Chroma paths, `task_data`, and `flow_id` stay on `RetrievalTools` and never appear in the LLM schema.

**Chosen over:**

- Module-level `@tool` functions with the index in a contextvar — hidden global state, conflicts with layering (`task_data` + `flow_id` must be explicit through the service call).
- Deferring the wrapper to TASK 04 — TASK 03 owns the runtime-facing tool surface; TASK 04 should only compose the graph.

**Trade-off we accepted:**

- Cost: `langchain-core` in the tools layer, used only as a schema/adapter, not as retrieval or prompts.
- Gain: one instance per question run; tests can bind a fake `task_data` without globals. The LLM schema later also includes optional `source` (see below).
- Constraint honored: tools still call `run_retrieval` only; wrappers add no business logic.

**Not implemented until the remaining TASK 03 choices below are closed.**

### Parameters: question + optional dates only

**Superseded in part:** optional `source` was added later (see “Optional `source`” below). `limit`, `category`, entity, and pagination stayed out.

**Choice:** Do not add `limit`, `source`, `category`, entity, or pagination to the LLM-facing tools.

**Chosen over:**

- Optional `limit` capped at 10 — extra parameter the model can misuse; `RETRIEVAL_TOP_K` already bounds the context.
- `source` / `category` filters — metadata exists in Chroma but exact publisher/category names are brittle for an LLM; a wrong value looks like “no evidence”.
- Entity field + pagination — no entity index; page 2 of cosine top-k is low-value noise.

**Trade-off we accepted:**

- Cost: narrowing is only via question wording and optional `published_from` / `published_to`.
- Gain: smallest schema, matches what retrieval already implements, fewer empty-result false negatives.
- Later: source/category filters can be added if evaluation shows the agent cannot isolate a publisher by query text.

### Status values: `ok`, `low_confidence`, `empty`, `invalid`

**Choice:** Keep these four only. Do not add `ambiguous`. Do not merge `empty` with `low_confidence`.

**Chosen over:**

- An `ambiguous` status when several sources appear — that flags multi-hop evidence as a problem; the agent in TASK 04 decides if results conflict or need another hop.
- Merging `empty` and `low_confidence` into one `no_match` — loses the signal to retry a weaker hit vs truly nothing found.

**Trade-off we accepted:**

- Cost: competing sources still look like `ok`; sufficiency and contradiction are not the tool's job.
- Gain: the tool reports retrieval quality only; `invalid` is a bad call, `empty` is no hits, `low_confidence` is weak hits, `ok` is strong enough hits.

### No third tool for article-by-title

**Choice:** Keep only `search_facts` and `search_corpus`. Follow-up is another search with a tighter question (the title can go in `question` text). Passages stay the retrieval unit.

**Chosen over:**

- `get_passages_by_title(article_title)` — useful for hops, but a third tool and exact-title matching is brittle.
- A full-article fetch — blows the context window and fights bounded retrieval.

**Trade-off we accepted:**

- Cost: no one-click “more from this article”.
- Gain: two-tool surface stays small; citation fields already include `article_title`.

### Answer-time access proof: test + README sentence

**Choice:** A unit test that tools call only `run_retrieval` (not `corpus.json` / `facts.json`). README states that at answer time knowledge is reached only through these tools. Full agent-side enforcement waits for TASK 04.

**Chosen over:**

- Import bans in empty `agents/` / `orchestration/` now — nothing to enforce yet.
- A sandbox / permission layer — too heavy for the assignment.

**Trade-off we accepted:**

- Cost: TASK 03 does not prove the future agent cannot cheat; it proves the tool layer has no back door.
- Gain: matches TASK 03 DoD with a reviewable check; TASK 04 owns the loop.

### No MCP server or client

**Choice:** Do not wrap tools as MCP. LangGraph will receive a Python list from the bound `RetrievalTools` instance (`StructuredTool` wrappers). New tools are added on that instance, not by standing up a protocol.

**Chosen over:**

- MCP server + client for “easy swapping” — extra process and SDK; the LLM still depends on the exposed names/descriptions. A dynamic tool list already lets the graph stay tool-agnostic.
- Many extra tools for robustness — usually worse tool selection, not better.

**Trade-off we accepted:**

- Cost: no bonus MCP demo; swapping a *remote* tool server later needs new work.
- Gain: less moving parts for the assignment; robustness stays in a small surface (`search_facts`, `search_corpus`) plus TASK 04 prompting.

### README: retrieval chapter

**Choice:** Record the tool surface, statuses, LangGraph wrappers, no-MCP, and answer-time-only access in the existing retrieval section of `project/README.md`. This log stays the working decision file, not the evaluator-facing doc.

**Chosen over:** a separate SDD (duplication) or documenting only here (evaluators will not open this file).

### Optional `source` on `search_facts` (supersedes “dates only”)

**Choice:** Add optional `source` to the LLM-facing Facts tool. Resolve the string against a catalog written at facts index time (exact name → unique substring → nearest catalog embedding with a similarity floor and a margin). Then Chroma `where source == canonical`. Unresolved names drop the filter. GT `expected_tool_calls` pass `source` only when that sub-question names an outlet.

**Chosen over:** keeping the earlier “question + dates only” schema. That schema could not isolate The Age or Independent Travel; cosine alone ranked Q05 Age at 30.7% and Q08 Tremblant at 25.3%, below a 0.35 drop floor.

**Trade-off we accepted:**

- Cost: a wrong outlet string used to look like “no evidence”; resolve-or-drop avoids that.
- Gain: Gate 2 hit Q05 and Q08 on the GT query (`metrics_2026-08-27_19-41-17.csv`).
- Later: cosine floor on Facts was removed entirely (below), so source is a narrowing aid, not the only way a weak gold survives.

### Facts: no cosine drop floor; one chunk per hop; no reranker

**Choice:** `search_facts` returns `RETRIEVAL_TOP_K=1` with no Facts cosine drop. Corpus still drops below `RETRIEVAL_CORPUS_MIN_SIMILARITY=0.35` (unbound in this loop). There is no rerank stage. Answer sees the concatenated top-1 Facts hits from Gather hops. Q04/Q09 still return one non-gold chunk per hop; that is not a retrieval-score problem.

**Chosen over:** Top-5 + cosine floor, Top-5 with no floor then NVIDIA rerank, one-fact-per-URL collapse, and any absolute `relevance_score` cutoff. The path and measurements are in “Ranking path” below.

**Trade-off we accepted:**

- Cost: unanswerable hops still emit a first-ranked noise sentence (Q04 NFL/Flexport, Q09 Taylor Swift/OpenAI). Cosine cannot drop those without also dropping Q08 gold (25.3%).
- Gain: live GT args `metrics_2026-08-27_22-25-11.csv` — 9/9 answerable gold URL+snippet at rank 1, 0 false-positive URLs on those questions, two or three facts sent to Answer instead of a 8–22 union.
- Constraint honored: ranking stays in retrieval; Gather/Answer still judge sufficiency. No second numeric gate in Answer.

---

## Ranking path (what we tried)

This is the working log for the assignment’s retrieval-reasoning requirement. Evaluator-facing summary: `project/README.md` (Traceable Retrieval Indexes). Live numbers: `tests/live_search_facts_gt_calls/outputs/`.

1. **Top-5 + 0.35 Facts floor.** Needed for a first bounded list. Failed Gate 2 on Q05 Age (30.7%) and Q08 Tremblant (25.3%). Cosine vs the hop sub-question is not a success rate; a floor at 0.35 threw gold.

2. **Source filter + relax floor after a resolved source.** Closed those two hops at Top-5 (`19-41-17` / `19-37-44`, 9/9 recall). Union per question was still large (often 8–22 facts) because every hop kept five rows.

3. **Drop the Facts cosine floor entirely.** Weak golds must survive even when Gather omits `source`. Corpus keeps 0.35. Status `ok` vs `low_confidence` still uses 0.40 and is not a drop.

4. **Rerank the Gather union vs the original question.** Local MiniLM / FlashRank were rejected (wanted a free API). The only free dedicated rerank on OpenRouter was `nvidia/llama-nemotron-rerank-vl-1b-v2:free` (`POST /rerank`, one request, not a chat prompt). After Gather stopped: unique snippets → rerank → keep 8, `min_score=0`. API failure kept the gathered list.

   NVIDIA `relevance_score` sat around `1e-5`–`0.17` and was not a confidence. The weakest gold (Q06, `0.00024`) scored below 31/74 noise rows across questions. Keep-8 by embedding cosine already retained every gold snippet on this GT; rerank did not add recall. It helped order Q01/Q05/Q11 weak golds and buried a Q03 gold (embedding rank 3 → rerank rank 7). Q04/Q09 still forwarded all retrieved noise. **Removed.** Tests live under `tests/_archive/rerank_evidence/`.

5. **Dedup.** Repeated *titles* in the rerank CSV were different sentences from the same article, which is allowed. Collapsing to one fact per URL (`20-55-40`) was the wrong fix and was reverted. Same *snippet text* from two hops is sent once.

6. **Inspect rank inside each hop, not the union.** Every answerable gold fact is rank 1 of *its* sub-question (`hops_2026-08-27_21-52-47.csv` and `22-10-43.csv`). The “16.75% Lions” score was Cowboys-hop retrieving the other hop’s gold as rank 4. Union cosine is the wrong ranking unit.

7. **Ship Top-1 per hop, no rerank.** `22-25-11`: 9/9 gold, 0 extra URLs on answerable questions. Q04/Q09 still send two noise facts. Filtering those is Gather/Answer (empty store for Pets Best / Forerunner), not a retrieval cutoff.

---

## Open

none
