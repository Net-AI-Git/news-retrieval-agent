# tests/ — Agent Guide

## Purpose
Workspace for **named test scenarios / experiments**. Every distinct task that has its own test fixtures, scripts, or analysis gets its **own subdirectory** under [`tests/`](.). This is not a traditional `pytest` mirror tree — each subdirectory is a self-contained experiment package.

Deterministic tests and offline prompt experiments both live here as isolated named scenarios. Prompt experiments never run against production users.

## Layout — One Subdirectory per Test/Experiment

```
tests/
├── AGENTS.md                     ← THIS FILE — the only AGENTS.md under tests/
├── tmp/                          ← scratch workspace for ad-hoc model experiments (throwaway)
├── <test_name>/                  ← one directory per scenario, snake_case
│   ├── README.md                 ← describes this specific test (REQUIRED)
│   ├── inputs/                   ← fixtures consumed by the test
│   ├── outputs/                  ← captured artifacts (logs, generated files) — gitignored if large
│   └── test_<name>.py            ← entry-point script or pytest module
└── another_test/
    └── ...
```

## Scratch Workspace — `tmp/`
- All ad-hoc files the model creates or runs during an experiment MUST live under [`tmp/`](tmp/).
- Contents of [`tmp/`](tmp/) are throwaway — no `README.md`, no structure requirements, no commitment to preserve.
- Do NOT write scratch files anywhere else in the repo. Do NOT promote a `tmp/` file to a real test — recreate it under a proper `<test_name>/` subdirectory instead.

## Coding Rules (specific to this directory)
- **Starting a new test = creating a new subdirectory**. Do NOT append unrelated test scripts to an existing test directory.
- Subdirectory name is the test name in `snake_case` (e.g. `invoice_extraction_v2/`, `prompt_ablation_seed_151/`).
- **Each test subdirectory contains a `README.md`** — never an `AGENTS.md`. The only `AGENTS.md` in this tree is **this file**.
- A subdirectory contains everything the test needs: fixtures, scripts, expected outputs, notes. No shared "global" fixtures pool — duplicate small fixtures across tests rather than coupling them.
- If two tests genuinely share large fixtures, place those fixtures in [`../src/data/`](../src/data/) and import — do not invent a top-level `tests/fixtures/` directory.
- External systems (Oracle, Azure OpenAI, CRM, Redis) are mocked inside each test directory. No real network calls without the user's explicit say-so.
- A test that is no longer relevant is **archived** (move into `tests/_archive/<name>/`), not deleted — historical results matter.

## Prompt A/B Experiments
- Create one named test directory per prompt experiment.
- Store the production baseline as `inputs/control.md` and experimental versions as `inputs/candidate_<variant_name>.md`.
- Store the fixed dataset and expected outcomes under `inputs/`; store captured metrics and model outputs under `outputs/`.
- Every candidate changes one named hypothesis while preserving the control's input and output contract.
- Define metrics and the promotion threshold in the experiment `README.md` before running it.
- The runner loads prompt files from the experiment directory and never changes [`../src/prompts/`](../src/prompts/) during execution.
- After explicit approval, copy only the winning content into the consumer's production prompt under [`../src/prompts/`](../src/prompts/).
- Keep the experiment directory as the reproducible record after promotion.

## Required `README.md` inside each test subdirectory
Each `<test_name>/README.md` must include:
- **Goal** — one sentence: what hypothesis or behavior this test verifies.
- **Scope** — which files in [`../src/`](../src/) are exercised.
- **How to run** — every terminal command required to reproduce the experiment end-to-end (env setup, install, data prep, execution), each on its own line, copy-paste runnable by an LLM with zero inference.
- **Inputs** — what is in `inputs/` and where it came from.
- **Expected outcome** — what success looks like.
- **Status** — `Active` / `Passing` / `Failing` / `Archived` + date of last run.

## Forbidden in this directory
- No `AGENTS.md` files inside test subdirectories — only this top-level file. Subdirectories use `README.md`.
- No `test_<feature>.py` files at the **top level** of [`tests/`](.) — every test belongs inside its own subdirectory.
- No production credentials, no real customer PII in fixtures.
- No imports of test code from production modules in [`../src/`](../src/).
- No tests that depend on execution order across subdirectories.
- No `print(...)` left in committed test code — use the framework's reporting.

## See Also
- [`../src/data/AGENTS.md`](../src/data/AGENTS.md:1) — shared sample documents.
- [`../src/prompts/AGENTS.md`](../src/prompts/AGENTS.md:1) — production prompt source of truth.
- [`.Codex/rules/03-code-quality.md`](../../.Codex/rules/03-code-quality.md:1) — naming + function-size rules apply to test code too.
