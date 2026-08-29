# Local ground truth

Hop fields on `Q01.json`–`Q11.json` follow the Gather / retrieve split. Answers, facts, citations, and corpus gold are unchanged. Grade boards live in sibling `grade_*.json` files and are not exam questions.

| Field / files | Owner | What it scores |
| --- | --- | --- |
| `sub_questions` on `Q01`–`Q11` | Gather | Hop inventory. One standalone string per need. Named outlet and publication window stay in the string of the claim they belong to. Wording is an example, not a verbatim match. |
| `expected_tool_calls` where `agent` is `retrieve` | Retrieve | Isolated `search_facts` fill. `arguments.question` copies that hop’s sub-question. `source` only when that string names a news outlet. ISO-8601 publication dates only when that string names a publication window (Q08). |
| `expected_tool_calls` where `agent` is `unbound` | none | Conditional `search_corpus` on Q04/Q09. Not bound in the answering loop. |
| `facts` / `citations` / `answer` | Answer + retrieval gold | Short answer and supporting snippets. Not Gather or retrieve output. |
| `grade_coverage.json` | Grade | Frozen mid-loop `{question, prior_queries, evidence}` plus `expected_verdict`. Invented questions over real index snippets. Not Q01–Q11. |
| `grade_invented_midloop_stop_continue.json` | Grade | Invented-domain mid-loop `{question, prior_queries, evidence}` plus `expected_route` (`stop` / `continue`). Not the exam set. |

Retrieve never sees the parent question or sibling hops. Packed two-outlet strings fail Gather, then retrieve cannot fill `source`.

## Grade coverage (`grade_coverage.json`)

One JSON array. Each object is an isolated Grade state. `id` is unique. `class` and `expected_verdict` are one of `enough`, `missing_hop`, `empty_stop`. Evidence uses the production shape (`article_title`, `snippet`, `url`, `published_at`, `match_percentage`) with no `source` field. Evidence is append-only and every accumulated chunk reaches Answer. Do not retarget a label to fit a weak `grade_agent.md`.

| `id` | `class` | What the frozen state checks |
| --- | --- | --- |
| `grade_enough_flipboard_and_activitypub` | enough | Two named outlets, both covering snippets. |
| `grade_enough_complete_plus_nfl_noise` | enough | Same covering pair plus an unrelated NFL hit; still stop. |
| `grade_enough_zermatt_and_chatgpt` | enough | Two independent named-outlet facts, both covered. |
| `grade_missing_hop_second_outlet_never_searched` | missing_hop | One outlet covered; the other named outlet was never searched. |
| `grade_missing_hop_unused_publish_date` | missing_hop | Named publication-date filter unused; related wrong-date hit. |
| `grade_missing_hop_second_named_outlet` | missing_hop | One named outlet covered; second named outlet never searched. |
| `grade_missing_hop_keyword_overlap` | missing_hop | Need remains uncovered after a keyword-overlap chunk; keep it and search again. |
| `grade_missing_hop_wrong_outlet` | missing_hop | Need remains uncovered after a wrong-outlet hit; keep it and search the required outlet. |
| `grade_missing_hop_off_topic_entities` | missing_hop | Need remains uncovered after an off-topic hit; keep it and search the missing fact. |
| `grade_empty_stop_unrelated_hits` | empty_stop | On-target search; unrelated hit; fact not in the index. |
| `grade_empty_stop_amount_not_in_snippet` | empty_stop | On-target search; snippet names the event, not the asked amount. |
| `grade_empty_stop_two_outlets_no_cover` | empty_stop | Both named outlets searched; neither chunk covers. |

Scored by `tests.live_grade_coverage.run_live_grade_coverage`.

## Invented mid-loop stop/continue (`grade_invented_midloop_stop_continue.json`)

One JSON array. Each object is an invented-domain Grade state with `expected_route` of `stop` or `continue`. Scored by `tests.live_grade_gt.run_live_grade_gt`.
