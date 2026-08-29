# Source catalog resolve

## Goal

Verify that an optional `source` argument is resolved against the facts source catalog with exact match, unique substring, then embedding nearest-with-margin, and that unmatched names drop the filter.

## Scope

Exercises `src/services/source_resolve_service.py` with a mocked catalog and mocked embeddings. No live network calls and no Chroma.

## How to run

```text
cd project
uv run python -m unittest tests.source_resolve_catalog.test_source_resolve_catalog
```

## Inputs

No files in `inputs/`. Tests construct an in-memory catalog of source names and 2-d embeddings.

## Expected outcome

Exact `"The Age"` and unique substring `"Age"` resolve to `The Age` without embedding. `"Independent"` with three Independent titles embeds and picks `The Independent - Travel` when that vector is nearest with margin. Empty source, missing catalog, low similarity, and a tight two-way margin all return no resolved source.

## Status

Active — 2026-08-27
