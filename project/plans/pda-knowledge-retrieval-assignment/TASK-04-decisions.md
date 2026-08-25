# TASK 04 — Decision Log

**Status:** In progress  
**Scope:** Agentic grounded answering loop. Tool contracts stay as TASK 03.

Closed decisions stay here with the trade-off that justified them. Open items stay listed until chosen.

---

## Closed

### LangGraph loop composing the TASK 03 tool list

**Choice:** Run the answering loop as a LangGraph graph. Bind `search_facts` and `search_corpus` from `RetrievalTools.as_langchain_tools()`. Orchestration owns the graph, budgets, and stop conditions. The agent owns the prompt and the two-tool allowlist.

**Chosen over:**

- A hand-rolled OpenAI/Anthropic tool-calling while-loop — extra glue, and it ignores the StructuredTool surface TASK 03 already built for LangGraph.
- LangChain `AgentExecutor` — less explicit state, budgets, and stop nodes than a graph.

**Trade-off we accepted:**

- Cost: `langgraph` in the orchestration layer, plus LangChain chat/tool types at the agent boundary.
- Gain: one runtime from tools through the loop; explicit nodes for tool call, answer, refuse, and budget stop.
- Constraint honored: tools stay adapters; the graph does not reach Chroma or JSON files.

### Gather with tools + Answer with no tools

**Choice:** Two agents. `gather` has the `search_facts` / `search_corpus` allowlist and decides the next hop, reformulation, or stop. `answer` has no tools and sees only evidence accumulated in this run, then returns a name / `Yes` / `No` / refusal plus citations. Decomposition is gather prompt behavior, not a mandatory planner node.

**Chosen over:**

- One ReAct agent that both retrieves and answers — the answerer keeps tool access and can search or cite after the evidence window is supposed to be closed.
- A required decompose node that splits the question into sub-queries before any search — sequential hops need the next query to depend on retrieved entities; a fixed pre-split also makes orchestration, not the LLM, choose tools.

**Trade-off we accepted:**

- Cost: two prompts, two agent files, a graph edge from gather-stop to answer.
- Gain: tool choice stays LLM-directed where it belongs; the final claim cannot call retrieval or see raw corpus/facts files.
- Constraint honored: split is by tool access and context, not by workflow step number.

### Native function calling: `bind_tools` + `ToolNode`

**Choice:** Gather uses LangChain native tool calling. The chat model is bound with `bind_tools` on the TASK 03 `StructuredTool` list. LangGraph `ToolNode` executes calls and appends `ToolMessage` results. The model chooses the tool name and arguments; the graph only runs them.

**Chosen over:**

- ReAct text parsing (`Action: search_facts`) — extra parser, weaker contract, and it ignores the schema TASK 03 already exposed.
- A Python loop that calls tools from a pre-split query list — orchestration would choose tools, not the LLM.

**Trade-off we accepted:**

- Cost: Gather requires a chat model that supports tool calling; a model without that API is out.
- Gain: typed arguments, fewer parse failures, same tool objects from TASK 03 to the graph.
- Constraint honored: `ToolNode` still executes the tool adapters; it does not open Chroma or JSON files.

### OpenRouter chat model: `openai/gpt-4o-mini`

**Choice:** One chat model for Gather and Answer. Provider stays OpenRouter via existing `OPENAI_API_KEY` and `OPENAI_BASE_URL`. Model id is `openai/gpt-4o-mini`, read from `OPENAI_MODEL`. Embedding model stays on `OPENAI_EMBEDDING_MODEL`.

**Chosen over:**

- `openai/gpt-4.1-nano` or `google/gemini-2.5-flash-lite` — cheaper, weaker or less clean native tool calling for this loop.
- A `:free` OpenRouter model — rate limits and unreliable `tool_calls`.
- A second, stronger model for Answer — extra config for an assignment-scale token budget.

**Trade-off we accepted:**

- Cost: not the cheapest slug; still cents at assignment volume.
- Gain: reliable `bind_tools` with ChatOpenAI-compatible OpenAI payloads.
- Constraint honored: chat and embedding models are separate env vars.

### ChatOpenAI lives on the agent as runtime

**Choice:** Gather and Answer each construct `ChatOpenAI` from `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`. No `gpt_*_repository` for this feature. The LangChain chat model is the agent runtime (same class of dependency as LangGraph), not a one-shot GPT classification call.

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

**Choice:** The graph routes Gather → tools while the model emits `tool_calls`, and Gather → Answer when it does not. Gather has no `done` schema. Sufficiency is Answer's: it answers or refuses from `evidence`. A step cap is a separate orchestration budget.

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

**Choice:** Two production prompt files, one per agent module, no prompt text in Python. Gather: do not answer the user; call tools; decompose into standalone information needs; finish `search_facts` for every need before any `search_corpus`; call corpus only for needs whose facts are empty, weak, or missing a hop; stop with no `tool_calls` when enough or stuck. Answer: only the question plus this run's `evidence`; return an entity / `Yes` / `No` or refuse; cite only listed items; no world-knowledge fill-in. No third agent.

**Chosen over:**

- One prompt that both searches and answers — Answer would keep tool access.
- Prompt strings in Python — forbidden; prompts live in `prompts/`.

**Trade-off we accepted:**

- Cost: two files to keep in sync with graph behavior.
- Gain: Gather cannot emit the final claim; Answer cannot search.
- Constraint honored: filename stem matches the consuming agent module.

### Gather: finish FACTS for every need, then CORPUS only as fallback

**Choice:** Gather must complete `search_facts` for every identified information need before starting `search_corpus`. After all FACTS results return, CORPUS is called only for needs whose FACTS are empty, weak, or missing a required hop. The first CORPUS fallback for a need reuses the same `question` and date filters as that need's FACTS call. Reformulation or following a retrieved entity happens only after both stores still miss a hop.

**Chosen over:**

- Interleaving FACTS and CORPUS per sub-question — spends the tool budget on corpus before every fact need is checked, and fights the GT pattern of required facts calls then conditional corpus.
- A different, tighter corpus query on the first fallback — a second wording with no measurement that the FACTS query already retrieves the passage.
- Encoding FACTS-then-CORPUS as graph edges — orchestration would choose tools, not the LLM.

**Trade-off we accepted:**

- Cost: more FACTS calls before any corpus hop; an 8-call cap can expire before corpus on a wide question.
- Gain: corpus is a fallback, not a parallel first look; first corpus query is comparable to the facts query that just failed.
- Constraint honored: tool choice stays in the Gather prompt; the graph still only routes on `tool_calls` vs stop.

### Prompt confidence 4–5 is a stop/refuse gate

**Choice:** Gather may emit a tool call only when the next query would score 4 or 5 as useful; scores 1–3 stop with no tool calls. Answer may return a non-refusal only at score 4 or 5; 1–3 must refuse. This is prompt policy. Retrieval still drops by `RETRIEVAL_FACTS_MIN_SIMILARITY` / `RETRIEVAL_CORPUS_MIN_SIMILARITY` (both 0.35). Answer still has no second numeric `match_percentage` cutoff in code.

**Chosen over:**

- No prompt score bar — Gather keeps calling weak follow-ups until the orchestration cap.
- A code gate on `match_percentage` in Answer — duplicates the retrieval floor and drops usable hits the model can still refuse.

**Trade-off we accepted:**

- Cost: a model that ignores the score still needs the 6/8 caps.
- Gain: stop/refuse is stated in the same 1–5 scale the prompt standard requires; retrieval floors stay in `conts.py`.
- Constraint honored: filtering by the retrieval floor remains service logic; the prompt score does not replace it.

### Retrieval floors stay in the retrieval service, split by store

**Choice:** Drop matches below 0.35 in Facts and below 0.35 in Corpus, as two constants. Calibrated on GT union Top-5 after the sub-question rewrites: 0.30 kept FACTS noise and Q09 CORPUS false positives; 0.40 would kill the weakest gold FACTS hit (Q02 35.21) and the Q06 Guardian CORPUS hit (35.17). High-confidence status stays 0.40 and is not a drop filter. Live embeddings stay raw (no NVIDIA prefixes, no `input_type`); A/B/C measurements are in `tests/gt_union_topk_retrieval_report/README.md` and the README retrieval chapter.

**Chosen over:**

- One shared `RETRIEVAL_MIN_SIMILARITY` — the stores have different hit/miss curves; they should be able to move separately.
- NVIDIA `query:` / `passage:` prefixes or `extra_body input_type` — measured, did not improve Success or recall.

**Trade-off we accepted:**

- Cost: two constants that currently hold the same number.
- Gain: each store can be retuned without retuning the other; the live floor sits just under the weakest gold hit we still need.
- Constraint honored: Answer still does not apply a second numeric cutoff; this is retrieval only.

---

## Open

- none (prompt example source is asked before prompt files are written; examples are not invented).
