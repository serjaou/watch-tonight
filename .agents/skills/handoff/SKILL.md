---
name: handoff
description: >-
  End-of-session handoff routine. Use when the owner says they are stopping,
  closing the session, switching machines, or types /handoff.
---

# End-of-Session Handoff (`/handoff`)

Follow the **Session end protocol** in [AGENTS.md](../../../AGENTS.md):

1. Run `uv run poe check` and record the exact result.
2. Rewrite the `Now` section of [PROGRESS.md](../../../PROGRESS.md) with:
   - `Active feature` (ID, name, branch)
   - `State` (what is done and what remains)
   - `Last check` (command + timestamp + summary)
   - `Next step` (concrete first action for the next session)
   - `Waiting on owner` (include `refine feat-XXX` if the next item in `feature_list.json` is not ready yet)
   - `Unverified` (anything not yet tested)
3. Prepend a 1–3 line entry to the `Log` section of `PROGRESS.md` (`YYYY-MM-DD · <Mac|Windows> · Antigravity · <feat-id>: <summary>`).
4. Update the active item's `status` and `evidence` in [feature_list.json](../../../feature_list.json).
5. Ask yourself: *"What do I know now that the next session needs and is not in the repo?"* Save any new knowledge in the right file (`docs/decisions/`, `docs/specs/`, `docs/harness-log.md`, or `LEARNING.md`).
6. Stage, commit (WIP commits on a feature branch are encouraged; never push broken checks to `main`), and push if requested by the owner.
7. Show the owner the updated `Now` block, any files updated, the commit hash, and what remains unverified.
