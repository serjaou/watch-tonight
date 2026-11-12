---
name: start
description: >-
  Start-of-session routine. Use when the owner opens a new session, switches
  machines, or types /start.
---

# Start-of-Session Routine (`/start`)

Follow the **Session start protocol** in [AGENTS.md](../../../AGENTS.md):

1. Run `git status` and `git pull --ff-only` (if a remote tracking branch exists), then `uv sync` and `uv run poe check`.
   - If `uv run poe check` fails, fixing it is the session's first task.
2. Read the `Now` section of [PROGRESS.md](../../../PROGRESS.md), then inspect [feature_list.json](../../../feature_list.json) and the active item's spec or spike file.
3. Determine the session task using the priority rules in `AGENTS.md`:
   - Ready `in_progress` or `todo` item → build/continue it.
   - Top unblocked `todo` item missing an approved spec → run `/spec` with the owner.
   - Unknown blocking a spec → propose/run a `spike`.
4. Report to the owner in **at most 8 lines**:
   - Branch & `uv run poe check` result
   - Active feature ID, name, and readiness
   - Proposed 3-line plan for this session
   - Any blocking questions, then wait for `"go"` if the spec isn't approved yet.
