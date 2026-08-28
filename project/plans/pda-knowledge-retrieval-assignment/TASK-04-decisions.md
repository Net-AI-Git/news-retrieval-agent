# TASK 04 — Decision Log

**Status:** In progress  
**Scope:** Agentic grounded answering loop. Tool contracts stay as TASK 03. This loop binds `search_facts` only.

Closed decisions stay here with the trade-off that justified them. Open items stay listed until chosen.

---

## Closed

### LangGraph loop composing the TASK 03 tool list

**Choice:** Run the answering loop as a LangGraph graph. Bind only `search_facts` from `RetrievalTools.as_langchain_tools()`. Orchestration owns the graph, budgets, and stop conditions. The agent owns the prompt and the one-tool allowlist. `search_corpus` stays on the TASK 03 class and is not in this loop.

**Chosen over:**

- A hand-rolled OpenAI/Anthropic tool-calling while-loop — extra glue, and it ignores the StructuredTool surface TASK 03 already built for LangGraph.
- LangChain `AgentExecutor` — less explicit state, budgets, and stop nodes than a graph.

**Trade-off we accepted:**

- Cost: `langgraph` in the orchestration layer, plus LangChain chat/tool types at the agent boundary.
- Gain: one runtime from tools through the loop; explicit nodes for tool call, answer, refuse, and budget stop.
- Constraint honored: tools stay adapters; the graph does not reach Chroma or JSON files.

### Gather with tools + Answer with no tools

**Choice:** Two agents at first. `gather` has the `search_facts` allowlist. `answer` has no tools and sees only evidence accumulated in this run, then returns a name / `Yes` / `No` / refusal plus citations. Decomposition is gather prompt behavior, not a mandatory planner node. Stop-vs-rewrite later moved to Grade (see below).

**Superseded 2026-08-28:** Gather no longer binds tools. An isolated retrieve agent owns `search_facts`. See “Isolated retrieve hop” below.

**Chosen over:**

- One ReAct agent that both retrieves and answers — the answerer keeps tool access and can search or cite after the evidence window is supposed to be closed.
- A required decompose node that splits the question into sub-queries before any search — sequential hops need the next query to depend on retrieved entities; a fixed pre-split also makes orchestration, not the LLM, choose tools.

**Trade-off we accepted:**

- Cost: two prompts, two agent files, a graph edge from gather-stop to answer.
- Gain: tool choice stays LLM-directed where it belongs; the final claim cannot call retrieval or see raw corpus/facts files.
- Constraint honored: split is by tool access and context, not by workflow step number.

### Native function calling: `bind_tools` + `ToolNode`

**Choice:** Gather uses LangChain native tool calling. The chat model is bound with `bind_tools` on the TASK 03 `StructuredTool` list. LangGraph `ToolNode` executes calls and appends `ToolMessage` results. The model chooses the tool name and arguments; the graph only runs them.

**Superseded 2026-08-28:** `bind_tools` + `ToolNode` still execute `search_facts`. The bound agent is retrieve, not Gather.

**Chosen over:**

- ReAct text parsing (`Action: search_facts`) — extra parser, weaker contract, and it ignores the schema TASK 03 already exposed.
- A Python loop that calls tools from a pre-split query list — orchestration would choose tools, not the LLM.

**Trade-off we accepted:**

- Cost: Gather requires a chat model that supports tool calling; a model without that API is out.
- Gain: typed arguments, fewer parse failures, same tool objects from TASK 03 to the graph.
- Constraint honored: `ToolNode` still executes the tool adapters; it does not open Chroma or JSON files.

### OpenRouter chat model: `openai/gpt-4o-mini`

**Choice:** One chat model for Gather, retrieve, Grade, and Answer. Provider stays OpenRouter via existing `OPENAI_API_KEY` and `OPENAI_BASE_URL`. Model id is `openai/gpt-4o-mini`, read from `OPENAI_MODEL`. Embedding model stays on `OPENAI_EMBEDDING_MODEL`.

**Chosen over:**

- `openai/gpt-4.1-nano` or `google/gemini-2.5-flash-lite` — cheaper, weaker or less clean native tool calling for this loop.
- A `:free` OpenRouter model — rate limits and unreliable `tool_calls`.
- A second, stronger model for Answer — extra config for an assignment-scale token budget.

**Trade-off we accepted:**

- Cost: not the cheapest slug; still cents at assignment volume.
- Gain: reliable `bind_tools` with ChatOpenAI-compatible OpenAI payloads.
- Constraint honored: chat and embedding models are separate env vars.

### ChatOpenAI lives on the agent as runtime

**Choice:** Gather, retrieve, Grade, and Answer each construct `ChatOpenAI` from `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`. No `gpt_*_repository` for this feature. The LangChain chat model is the agent runtime (same class of dependency as LangGraph), not a one-shot GPT classification call.

**Chosen over:**

- A GPT repository wrapping `chat.completions.create` — cannot `bind_tools` / `ToolNode`.
- Constructing `ChatOpenAI` in orchestration at compile time — orchestration would own an external client, and the agent would not own its model.

**Trade-off we accepted:**

- Cost: agents import LangChain's OpenAI chat wrapper. A strict reading of "no external clients" on agents may flag this; we treat it as runtime and will record an approved SDD deviation on the agent files when they exist.
- Gain: `bind_tools` works; secrets stay in env; no factory and no GPT repo for an agentic loop.
- Constraint honored: agents still do not import services or repositories; tools remain the only path to retrieval.

### Graph state: messages plus evidence list

**Choice:** LangGraph state holds the question, the gather `messages` thread, and an `evidence` list of `RetrievedItem`. After each tool result, a reducer appends only items from the tool payload. Gather sees `messages`. Answer receives only `question` + `evidence`. Citations must come from that list.

**Chosen over:**

- Messages-only state — Answer would parse raw `ToolMessage` JSON and could cite text that is not a `RetrievedItem`.
- Evidence-only state — breaks native tool calling, which needs `AIMessage` / `ToolMessage` history.

**Trade-off we accepted:**

- Cost: custom graph state and a reducer besides `add_messages`.
- Gain: the answer node cannot see corpus files or leftover tool chatter; citation checks have a typed list to validate against.
- Constraint honored: evidence is still only what TASK 03 tools returned in this run.

### Answer structured output

**Choice:** Answer uses `with_structured_output` against a Pydantic model in `schemas/agent.py`. Fields: `status` (`answered` or `refused`), `answer` (entity / `Yes` / `No`, empty on refuse), `citations` (list of `article_title` + `url`). No prose parsing.

**Chosen over:**

- Free-text `Answer:` / `Citations:` blocks — brittle parser.
- JSON asked in the prompt without schema binding — still format failures.

**Trade-off we accepted:**

- Cost: Answer must support structured output (gpt-4o-mini does).
- Gain: orchestration reads fields, not regex; citation checks have a typed list.
- Constraint honored: the model schema lives in `schemas/`, not on the agent class.

### Gather stops when there are no tool_calls

**Choice:** The graph routes Gather → retrieve while Gather emits sub-questions, retrieve → tools while the hop emits `tool_calls`, and otherwise → Answer. After a tools batch, Grade routes continue vs Answer (see below). Gather has no `done` schema. Sufficiency of the final claim is Answer's. A step cap is a separate orchestration budget.

**Superseded the 2026-08-25 gather-emits-tool_calls routing.** Gather now routes on a structured sub-question list.

**Chosen over:**

- A Gather structured `continue` / `stop` flag plus tools — two output modes on one node, fights native function calling.
- Code that stops on tool `status` (`ok` / `empty`) — orchestration would decide the next search, not the LLM.

**Trade-off we accepted:**

- Cost: a model that never stops calling tools needs a hard cap (next decision).
- Gain: tool choice and hop count stay model-directed until the bound; Answer still cannot search.
- Constraint honored: routing is graph policy; Gather does not own budgets.

### Hard cap then Answer, not a crash

**Choice:** Orchestration counts Gather LLM visits and tool executions. Caps: 6 Gather LLM runs, 8 tool calls (`conts.py`). Hitting either cap routes to Answer with current `evidence`. Answer may refuse. No dollar/token budget. LangGraph `recursion_limit` is a backstop, not the user-facing stop.

**Chosen over:**

- Relying only on LangGraph recursion — the run dies as an error instead of answer/refuse.
- A spend/token budget — extra metering for assignment-scale cost.

**Trade-off we accepted:**

- Cost: a cap can cut a long multi-hop short.
- Gain: the loop always terminates with a structured Answer payload.
- Constraint honored: budgets live in orchestration; constants in `conts.py`.

### Citation identity check, not snippet check

**Choice:** After Answer returns, orchestration keeps a citation only if its `url` equals a `url` in this run's `evidence`. If the citation has no `url`, keep it only if `article_title` equals an evidence title exactly. Snippet text and match percentage are not used. If `status` was `answered` and no citations remain, coerce to `refused` with an empty answer. Invalid citations are dropped; the run does not crash.

**Chosen over:**

- Trusting the prompt alone — fabricated titles/URLs could ship.
- Crashing on a bad citation — no structured refuse payload.
- Matching against `snippet` — not an identifier; cannot verify a short answer against a passage in code.

**Trade-off we accepted:**

- Cost: a slightly mistyped URL is dropped even if the title is right (unless url is missing and title matches).
- Gain: every shipped citation is an article the tools actually returned.
- Constraint honored: this is validation/routing in orchestration, not retrieval logic.

### Empty evidence refuses in code; otherwise Answer judges

**Choice:** If `evidence` is empty after Gather (including cap/stop), skip the Answer LLM and return `refused` with empty answer and no citations. If `evidence` is non-empty, Answer decides: entity / `Yes` / `No` only when that claim is stated in the supplied items; otherwise refuse. No extra code threshold on match percentage.

**Chosen over:**

- Always calling Answer, even with an empty list — wasted call, same refuse.
- Auto-refuse when match percentage is below a second cutoff — retrieval already filtered; a second numeric gate drops usable hits.

**Trade-off we accepted:**

- Cost: sufficiency for non-empty evidence is prompt-judged, so a sloppy Answer prompt can still over-claim (citations still have to survive the URL/title check).
- Gain: empty-run refuse is deterministic; non-empty judgment can handle contradiction and missing hops.
- Constraint honored: no answer-time corpus/facts files; Answer only sees this run's `evidence`.

### Two prompts: Gather searches, Answer claims

**Choice:** Production prompts stay in `prompts/`, one file per consuming agent, no prompt text in Python. Gather decomposes and must not answer or call tools. Retrieve calls `search_facts` once per isolated sub-question. Answer: only the question plus this run's `evidence`; return an entity / `Yes` / `No` or refuse; cite only listed items; no world-knowledge fill-in. `search_corpus` is not in this loop. Stop-vs-rewrite is Grade after tools.

**Superseded 2026-08-28 in part:** Gather no longer searches. See “Isolated retrieve hop”.

**Chosen over:**

- One prompt that both searches and answers — Answer would keep tool access.
- Prompt strings in Python — forbidden; prompts live in `prompts/`.

**Trade-off we accepted:**

- Cost: two files to keep in sync with graph behavior.
- Gain: Gather cannot emit the final claim; Answer cannot search.
- Constraint honored: filename stem matches the consuming agent module.

### Grade after tools (Gate 4)

**Choice:** After each tools batch, a Grade agent with no tools returns structured `enough` / `rewrite` / `missing_hop` / `empty_stop`. Orchestration routes continue (`rewrite` / `missing_hop`) back to Gather with a short note, or stop to Answer. Live Gather prompt experiments capped at 7/11 (`too_early` / missing gold on the same hops); a third prompt was not the next lever.

**Chosen over:**

- Another Gather-prompt round — three honest 7/11 runs, Q05/Q07 unchanged.
- A supervisor/orchestrator LLM — extra hop, no new tool access split.
- A planner node before any search — later hops still depend on retrieved entities.

**Trade-off we accepted:**

- Cost: one extra LLM call per tools batch.
- Gain: stop vs rewrite is a separate judgment from query writing; retrieve keeps `search_facts`.
- Constraint honored: Grade has no tools; Answer still cannot search; `search_corpus` stays unbound.

### Gather uses FACTS only; corpus is out of this task

**Choice:** Retrieve calls `search_facts` only. Reformulation or following a retrieved entity is another Gather turn that emits new sub-questions, then retrieve again. `search_corpus` is not bound and is not a fallback in this task.

**Superseded 2026-08-28 in part:** the Facts allowlist moved from Gather to retrieve.

**Chosen over:**

- Binding `search_facts` and `search_corpus` in this loop — current scope is facts-only.
- Encoding a corpus fallback as graph edges — would add a tool this task does not bind.

**Trade-off we accepted:**

- Cost: questions that need passages cannot retrieve corpus evidence in this task and must refuse if facts are not enough.
- Gain: one allowlist, one store, no corpus hops against the 8-call cap.
- Constraint honored: tool arguments stay in the retrieve prompt; the graph routes Gather on sub-questions and retrieve on `tool_calls` vs stop.

### Prompt confidence 4–5 is a Gather stop gate only

**Choice:** Gather may emit a tool call only when the next query would score 4 or 5 as useful; scores 1–3 stop with no tool calls. Answer no longer uses a 1–5 confidence band. Facts retrieval has no cosine drop floor and returns one chunk per hop. Corpus still drops below `RETRIEVAL_CORPUS_MIN_SIMILARITY` (0.35) and is unbound in this loop. Answer still has no second numeric `match_percentage` cutoff in code.

**Chosen over:**

- Keeping the 4–5 refuse band on Answer — it refused supported `No` and multi-hop conclusions that are not written in one snippet.
- A code gate on `match_percentage` in Answer — duplicates retrieval filtering and drops usable hits the model can still refuse.

**Trade-off we accepted:**

- Cost: Gather can still ignore the score and hit the 6/8 caps. Answer sufficiency is prompt-judged plus the snippet/url citation filter.
- Gain: Answer can return a supported `No` and a comparison that is inferred from two items.
- Constraint honored: Facts keep the top-1 hit; Corpus filtering stays in the retrieval service if that store is queried.

### Retrieval: Facts top-1, Corpus floor only, no rerank

**Choice:** Facts return the single nearest chunk (`RETRIEVAL_TOP_K=1`) with no cosine drop. Corpus still drops below 0.35. High-confidence status stays 0.40 and is not a drop filter. There is no rerank between Gather and Answer. Path and rejected alternatives: `TASK-03-decisions.md` (Ranking path). Live proof: `tests/live_search_facts_gt_calls` `metrics_2026-08-27_22-25-11.csv`.

**Chosen over:** a shared Facts/Corpus drop floor, Top-5 unions, and OpenRouter NVIDIA rerank. The Facts floor killed Q05/Q08 gold. Rerank scores were not a usable filter. Per-hop gold is already rank 1.

**Trade-off we accepted:**

- Cost: Q04/Q09 still emit one noise chunk per hop; cosine cannot delete them without deleting Q08 gold (25.3%).
- Gain: answerable hops send only the gold sentence; Answer context is two or three facts, not a noisy union.
- Constraint honored: Answer still does not apply a second numeric cutoff.

### Answer prompt: OpenAI vendor shape, no eval leakage

**Choice:** `src/prompts/answer_agent.md` follows OpenAI GPT developer-message order: `# Identity`, `# Instructions`, optional `# Examples` with `<user_query>` / `<assistant_response>`. The user JSON is `{"evidence": ..., "question": ...}` (evidence first). The prompt is short. Structured `AnswerResult` already constrains output, so the prompt does not ask for a markdown JSON block or a 1–5 score.

**Chosen over:**

- The project `[INSTRUCTIONS]` / `ROLE:` / `TASK:` / `RULES:` / `CONFIDENCE SCORE` template — written for a different outline; it fought GPT-4o-mini and the 4–5 band refused valid answers.
- Claude-style XML instruction tags as the main outline — not this model's documented shape.
- Few-shot from the 11 evaluation questions, or toy clones of those traps (coverage-change, `unspecified` + `while`) — that is exam leakage. A numeric 11/11 from that method is invalid.

**Trade-off we accepted:**

- Cost: Gather is a short vendor prompt; stop-vs-rewrite is Grade after tools. Answer examples, if any, must be invented format items (`example.test`), not exam rows.
- Gain: Gate 3 oracle-Answer is 11/11 without eval items in the prompt (`tests/oracle_answer_gt` `metrics_2026-08-27_21-56-37.csv`, `21-58-37`, independent re-run `22-16-19`).
- Constraint honored: prompt file in `prompts/`; no eval gold in the study guide.

### Answer uses `published_at` and combines hops

**Choice:** Treat `article_title` and `published_at` as facts. A conclusion may come from combining items; it need not appear in one snippet. For “A before B” / “A after B”, bind A/B to the clauses around the relation word, then compare those items’ `published_at` only (`before` ⇒ timestamp(A) < timestamp(B); `after` ⇒ timestamp(A) > timestamp(B); else `No`). Multi-clause: `Yes` only if every clause holds; a false clause makes the whole claim `No`. Empty evidence refuses. Citations copy `article_title`, `url`, and `snippet` exactly — orchestration keeps a citation only when `snippet` and `url` match an evidence item character-for-character.

**Chosen over:**

- “Answer only when the claim is stated in one snippet” — that refused temporal and cross-article items whose dates live in metadata.
- Isomorphic few-shot of the remaining failing rows — leakage; deleted in round 2.
- Matching citations by URL or title only — a paraphrased snippet could ship; the filter now requires the exact snippet string.

**Trade-off we accepted:**

- Cost: a paraphrased snippet is coerced to refuse even if the short answer was right. Temporal polarity on long “after” questions can still flip if the model binds A/B backwards; the clause-binding line is the mitigation, not a Gemini example.
- Gain: supported `No`, before/after, and coverage change work from gold evidence without teaching the 11-item exam.
- Constraint honored: Answer still sees only this-run evidence; no world knowledge.

### Isolated retrieve hop (Gate 4, 2026-08-28)

**Choice:** Split first-hop work into two agents. Gather emits a structured list of standalone sub-questions and has no tools. Orchestration fans those strings into retrieve, one invoke per sub-question, with only that string as the user message (no parent question, no sibling hops). Retrieve binds `search_facts` (`tool_choice` forced), copies a short outlet token into `source` when this sub-question names a news outlet, fills `published_from` / `published_to` when it names a publication window, and must not answer. Source catalog resolve stays inside `run_resolve_source` (exact → unique substring → embedding only on those substring hits, or the full catalog when substring is empty; drop the filter below similarity 0.5 or a 0.05 margin). Graph: Gather → retrieve → tools → Grade → Gather | Answer. Caps unchanged (6 Gather LLM turns, 8 tool calls). Same `openai/gpt-4o-mini` for all agents.

**Chosen over:**

- Another Gather-prompt round on one agent that both splits and fills `source` / dates. That agent sees every named outlet at once. Tightening “copy source on every named outlet” fixed pairing questions and copied `The Age` onto Q05’s TechCrunch hops. Relaxing “omit source unless the clause names the outlet” fixed Q05 and left `source` empty on “Did TechCrunch report…”. That is one context doing two jobs, not a wording miss.
- A stronger chat model with the old one-agent Gather. Cross-claim leakage is structural; the same `OPENAI_MODEL` also drives Grade and Answer.
- Making source resolve a second LLM tool. Catalog match already runs after `source` is filled. Unresolved names already drop the Chroma filter. A resolve tool would not have stopped Q05 if the hop still saw the full user question.
- Shipping `RETRIEVAL_TOP_K=2` to paper over packed queries and rank-1 variance. Trial: `tests/live_gather_first_hop` `metrics_2026-08-28_16-04-44.csv` (9/11) and `16-09-10.csv` (10/11). Gold coverage rose on Q01/Q07. Q05 still failed (`source=The Age` on all three calls). Reverted to 1 so Answer still sees one Facts chunk per hop.

**Trade-off we accepted:**

- Cost: one extra LLM call per sub-question; retrieve hops run sequentially to stay under OpenRouter rate limits; Gather can still pack two outlets into one string (Q04) or over-split (Q07).
- Gain: Q05 first-hop gold complete when The Age is only in that hop’s text (`metrics_2026-08-28_16-44-21.csv`). Q03 stopped inventing `source=FTX` / `news outlet`.
- Constraint honored: retrieve still cannot import services or the catalog; tools call `run_retrieval`; prompts stay in `prompts/` with no exam text.

**First-hop experiments (same board, no Grade/Answer):** `tests/live_gather_first_hop/`. Leak-scan Gather and retrieve prompts against local GT. `first_hop_success` requires gold URL+snippet in the first batch (or sourced calls on unanswerable rows) plus named date filters.

Prompt-only Gather (decompose and tool args in one `bind_tools` turn):

- Best clean k=1: 9/11 `metrics_2026-08-28_14-44-01.csv` (`inputs/candidate_every_named_outlet.md`). Misses: Q05 Age-on-all, Q07 packed abilities, occasional Q01 rank-1 miss.
- Re-run of that prompt: 8/11 `15-42-42.csv`.
- Eight further first-hop candidates the same day (omit-unless-named, invented-news `# Examples`, pairing/source wording). Scores 4–9/11. Examples taught some two-outlet unanswerable calls and did not teach filling `source` on “Did {Outlet} report…”. Invented-news clones were allowed as non-exam data; they still failed the pairing vs Q05 tradeoff.
- Prompt-only Gather+Grade earlier: 7/11 then 9/11 (`tests/live_gather_gt`). Standalone-retry track stopped at 7/11. Those boards include later turns; they are not this first-hop score.

k=2 then revert: documented above.

Split Gather/retrieve, k=1, production prompts: 8/11 `metrics_2026-08-28_16-44-21.csv`.

- Pass: Q02, Q03, Q05 (Age only on hop 3), Q06, Q08, Q09, Q10, Q11.
- Q01: `source=Sporting News` filled; gold not rank 1.
- Q04: Gather packed NYT and WSJ into one sub-question; retrieve left `source` empty; unanswerable source-count failed.
- Q07: seven hops, featured-in extras, missing the second TechCrunch gold URL.

Working prompts: `src/prompts/gather_agent.md`, `src/prompts/retrieve_agent.md`. Snapshot: `tests/live_gather_first_hop/inputs/candidate_decompose_only.md`. Local GT hop fields already matched this split (`sub_questions` vs required `search_facts` args). 2026-08-28 labeled each tool row `agent: retrieve` or `unbound`; answers/facts were not rewritten. See `src/data/ground_truth/README.md`.

**Agent contracts (follow-up work splits here):**

Gather owns only hop inventory. Input is `{question, prior_queries, grade_note}`. Output is `sub_questions: list[str]`. Copy the outlet or publication window that belongs to that claim into that string. One need, one outlet, one string. Do not pack NYT+WSJ. Do not attach The Age to a TechCrunch claim. Do not emit featured-in-only hops. Never answer. Never call tools. Retry emits only new strings that follow `grade_note` and differ from every `prior_queries` question. Remaining first-hop Gather misses: Q04 packed, Q07 over-split.

Retrieve owns only one `search_facts` fill. Input is one isolated `HumanMessage(sub_question)` — no parent question, no siblings. Copy the string into `question`. If this string names a news outlet, `source` is a short token from this string; else omit. Never person/company/topic as `source`. If this string names a publication window, ISO-8601 with UTC offset (`T00:00:00+00:00` / `T23:59:59+00:00`). Event dates stay in `question`. Never answer. Catalog canonicalize is `run_resolve_source`, not this agent. Q01 with `source` filled and gold not rank 1 is retrieval/k, not retrieve isolation.

Orchestration fans Gather’s list into sequential retrieve invokes, merges `tool_calls`, runs `ToolNode`, then Grade. Grade and Answer are out of this split.

---

## Open

- none
