---
name: "source-command-connect-branch"
description: "Connect every microservice in the workspace to an existing remote branch on origin (GitLab). Read-only against origin — never overrides anything local or remote."
---

# source-command-connect-branch

Use this skill when the user asks to run the migrated source command `connect-branch`.

## Command Template

# /connect-branch

Argument: a single branch name, exactly as it exists on GitLab. Example: `/connect-branch feature/PDA-3901-add-logger`.

## Procedure

1. For every immediate subdirectory of the workspace root that contains a `.git/` folder:
   1. `git -C <repo> fetch origin`
   2. `git -C <repo> checkout <branch>` — if it fails because the branch doesn't exist on origin, skip silently.

2. Report one row per repo: `CONNECTED` / `SKIPPED` / `ERROR: <reason>`.

## Hard Prohibitions

- NEVER run anything that mutates working tree, history, or remote: no `commit`, `push`, `pull`, `merge`, `rebase`, `reset`, `stash`, `clean`, `checkout -- .`.
- NEVER pass `--force`, `-f`, or `--force-with-lease`.
- NEVER create the branch on origin if it doesn't exist.
- NEVER lowercase, normalize, or "fix" the branch name. Pass it verbatim.
