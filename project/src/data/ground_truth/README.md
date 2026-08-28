# Local ground truth (`Q01.json`–`Q11.json`)

Hop fields follow the Gather / retrieve split. Answers, facts, citations, and corpus gold are unchanged.

| Field | Owner | What it scores |
| --- | --- | --- |
| `sub_questions` | Gather | Hop inventory. One standalone string per need. Named outlet and publication window stay in the string of the claim they belong to. Wording is an example, not a verbatim match. |
| `expected_tool_calls` where `agent` is `retrieve` | Retrieve | Isolated `search_facts` fill. `arguments.question` copies that hop’s sub-question. `source` only when that string names a news outlet. ISO-8601 publication dates only when that string names a publication window (Q08). |
| `expected_tool_calls` where `agent` is `unbound` | none | Conditional `search_corpus` on Q04/Q09. Not bound in the answering loop. |
| `facts` / `citations` / `answer` | Answer + retrieval gold | Short answer and supporting snippets. Not Gather or retrieve output. |

Retrieve never sees the parent question or sibling hops. Packed two-outlet strings fail Gather, then retrieve cannot fill `source`.
