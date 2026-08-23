# static/ — Agent Guide

## Purpose
Static assets served by FastAPI — primarily the Swagger UI bundle for offline API docs.

## Contains
- [`swagger-ui-bundle.js`](swagger-ui-bundle.js:1) — Swagger UI JavaScript.
- [`swagger-ui.css`](swagger-ui.css:1) — Swagger UI styles.

## Coding Rules (specific to this directory)
- Files here are **third-party assets**, kept locally for offline / air-gapped environments.
- Replace the entire file when upgrading — do not hand-edit minified vendor code.
- Pin the Swagger UI version in [`../README.md`](../README.md:1) so upgrades are explicit.
- Referenced from [`../src/routes/docs.py`](../src/routes/docs.py:1) via FastAPI's `StaticFiles` mount.

## Forbidden in this directory
- No source code (`.py`).
- No business logic, no configuration files.
- No proprietary or unlicensed assets.
- No edits to vendor files — replace, do not patch.

## See Also
- [`../src/routes/docs.py`](../src/routes/docs.py:1) — how these assets are served.
