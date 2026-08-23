# TASK 03 — Decision Log

**Status:** In Progress  
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
- Gain: the LLM sees `question` + optional dates only; one instance per question run; tests can bind a fake `task_data` without globals.
- Constraint honored: tools still call `run_retrieval` only; wrappers add no business logic.

**Not implemented until the remaining TASK 03 choices below are closed.**

### Parameters: question + optional dates only

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

---

## Open

none
