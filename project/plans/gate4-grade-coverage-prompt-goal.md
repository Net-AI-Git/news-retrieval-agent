# GOAL — Grade in three verdicts with accumulated evidence

**Status:** Superseded — 2026-08-29. Frozen 12-case coverage board stalled at 9/12. Next Grade spec: [`gate4-grade-e2e-visits-prompt-goal.md`](gate4-grade-e2e-visits-prompt-goal.md).  
**Author:** N/A  
**Created:** 2026-08-28  
**Updated:** 2026-08-29  
**SDD(s) Impacted:** none; the user explicitly approved continuing without an existing SDD  

This file is closed. Do not resume it. Do not use it for prompt wording. The active Grade-only spec is [`gate4-grade-e2e-visits-prompt-goal.md`](gate4-grade-e2e-visits-prompt-goal.md).

---

## Updated product decision

The `rewrite` verdict was cancelled.

Grade returns only:

- `enough`
- `missing_hop`
- `empty_stop`

Every CHUNK that was retrieved is kept in evidence. Grade does not delete, filter, or ask to ignore a CHUNK. A CHUNK that does not cover a need simply is not counted as coverage, but it stays in state and is sent to Answer at the end.

The three coverage cases that were previously classified `rewrite` are now classified `missing_hop`: continue searching for the missing information and keep the existing CHUNK.

---

## Friend review — you will fail if you do these

1. Do not put in the prompt questions, answers, titles, snippets, URLs, sub-questions, or imitations of Q01–Q11 or of `grade_coverage.json`.
2. `grade_agent.md` stays under 40 lines and under 350 words.
3. The structure is `# Identity`, then `# Instructions`, and `# Examples` optional only. No `# Context`.
4. No templates `[INSTRUCTIONS]`, `[DEFINITIONS]`, `ROLE:`, `TASK:`, `RULES:`, `CONFIDENCE SCORE`, `[EXAMPLE 01]`, or `RESPONSE FORMAT`.
5. The only legal verdicts are `enough`, `missing_hop`, `empty_stop`.
6. `note` is empty on `enough` and on `empty_stop`; on `missing_hop` it is not empty and does not repeat `prior_queries.question`.

Before every live run, open the prompt, check the six items, and verify `prompt_leak_hit=0`.

---

## Model and contract

**Model:** `OPENAI_GRADE_MODEL=openai/gpt-4.1-mini`  
**Input:** `{question, evidence, prior_queries}`  
**Output:** `GradeResult` with `verdict` and `note`  

`GradeResult.verdict` is limited in the schema to the three legal values. Another value is not part of the contract.

---

## The flow

```text
Question
    → Gather
    → Retrieve
    → Tools      adds CHUNKs to evidence
    → Grade      enough / missing_hop / empty_stop
        missing_hop → Gather, without deleting evidence
        enough / empty_stop → Answer with all accumulated evidence
```

`GroundedAnsweringState.evidence` is accumulated state. Every Tools result is appended to the existing list. `answer_node` passes the full list to Answer; citation filtering afterward does not delete evidence from Answer's input.

---

## The three states

### `enough`

All information needs are covered together in the accumulated evidence. Stop immediately. Noise does not prevent stopping. `note` is empty.

### `missing_hop`

At least one need is still not covered and an additional search must be performed. This includes:

- a need that has not yet been searched;
- a newspaper or publication-date filter that has not yet been used;
- a partial or unrelated CHUNK;
- a CHUNK from the wrong newspaper or the wrong publication date;
- keyword overlap without the requested fact.

All existing evidence is kept. `note` aims only at the next need or correction and differs from every previous question.

### `empty_stop`

All required needs and filters have already been searched, the accumulated evidence still does not allow an answer, and no substantially different search remains. Stop and send all evidence to Answer. `note` is empty.

---

## Coverage and search

- Split the user question into independent needs.
- A newspaper is attached only to the claim it is supposed to report on.
- A date is a filter only when the user limits the article publication date.
- A CHUNK covers a need only when the snippet supplies the information and the URL or title matches the attached newspaper.
- Refuting a yes/no assumption covers the assumption.
- A prior query counts as a search of a need only when it includes the fact and the required newspaper/publication dates.
- A CHUNK that does not cover is kept and is not deleted.

---

## GT and board

The gold is `project/src/data/ground_truth/grade_coverage.json`: 12 frozen states.

| Class | Number of cases |
|---|---:|
| `enough` | 3 |
| `missing_hop` | 6 |
| `empty_stop` | 3 |

The three cases that were converted to `missing_hop` are:

- `grade_missing_hop_keyword_overlap`
- `grade_missing_hop_wrong_outlet`
- `grade_missing_hop_off_topic_entities`

Score from `project/`:

```text
$env:OTEL_SDK_DISABLED="true"
uv run python -m tests.live_grade_coverage.run_live_grade_coverage
```

Do not use `tests/live_grade_gt` or `tests/live_gather_gt` as the score. Old results and candidate snapshots remain as history of the four-verdict contract and are not the source of truth for the new contract.

---

## Success

`case_success=1` when:

- `predicted_verdict` equals `expected_verdict`;
- `prompt_leak_hit=0`;
- `runtime_error` is empty;
- `enough` / `empty_stop`: `note` is empty;
- `missing_hop`: `note` is not empty and is not equal to a previous question.

Pass is the two newest `metrics_*.csv` files in a row, the same prompt and the same model, with 12/12 in every file.

---

## Scope

**Runtime:**

- `project/src/conts.py`
- `project/src/schemas/agent.py`
- `project/src/orchestration/grounded_answering_workflow.py`
- `project/src/prompts/grade_agent.md`

**GT and tests:**

- `project/src/data/ground_truth/grade_coverage.json`
- `project/src/data/ground_truth/README.md`
- `project/tests/live_grade_coverage/`
- `project/tests/grounded_answering/`

**Active documentation:**

- `project/plans/gate4-grade-coverage-prompt-goal.md`
- Grade section in `project/README.md`

**Out of scope:**

- Gather, Retrieve, and Answer content;
- Q01–Q11 and their GT;
- search tools and vector stores;
- historical snapshots and CSV;
- the old Grade/Gather tests.

---

## Verification

1. An active search verifies there is no `GRADE_VERDICT_REWRITE` or `rewrite` in the runtime contract, the prompt, or the new GT.
2. A deterministic test verifies that `GradeResult` rejects `rewrite`.
3. A deterministic test verifies that Answer receives all evidence, including an irrelevant CHUNK.
4. Friend review and leakage checks pass.
5. The live Grade board passes 12/12 twice in a row, or reports precisely if additional prompt experiment is required.

---

## Live results

- `candidate_append_only_three_verdicts.md`: 9/12, zero leakage, zero runtime errors.
- `candidate_three_verdict_precedence.md`: 8/12, zero leakage, zero runtime errors — kept as history and not promoted.
- The eight additional experiments from 2026-08-29:

| Candidate | Score |
|---|---:|
| `hard_missing_precedence` | 9/12 |
| `stop_before_near_miss` | 8/12 |
| `exclusive_case_order` | 9/12 |
| `evidence_only_coverage` | 9/12 |
| `silent_need_states` | 8/12 |
| `closed_empty_stop_list` | 8/12 |
| `boolean_decision_table` | 7/12 |
| `hard_stop_exceptions` | 9/12 |

All eight experiments ended with zero leakage and zero runtime errors. `candidate_evidence_only_coverage.md` remains in production as the tie-breaker: it keeps a snippet-only coverage rule and does not return `enough` without an explicit answer in the evidence.

A double pass was not achieved. The remaining boundary is between `missing_hop` and `empty_stop` when all needs have already been searched but CHUNK quality differs.

---

## Open questions

- none
