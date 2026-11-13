---
name: handoff
description: >-
  End-of-session handoff routine. Use when the owner says they are stopping,
  closing the session, switching machines, or types /handoff.
---

# End of session (`/handoff`)

Run the **End of Session** steps in [AGENTS.md](../../../AGENTS.md), with these details:

1. First run `uv run poe check` and record the exact result.
2. The "Now" section of [PROGRESS.md](../../../PROGRESS.md) has these fields:
   - **Active feature:** id, name, branch
   - **State:** what is done and what remains
   - **Last check:** command, date and time, summary
   - **Next step:** the first concrete action for the next session
   - **Waiting on owner:** decisions or reviews the owner owes (`refine feat-XXX` when the next item isn't ready)
   - **Unverified:** anything not yet tested, including the CI run of the pushed commit
3. Log line format: `YYYY-MM-DD · <Mac|Windows> · <Antigravity|Claude Code> · <feat-id>: <summary>`.
4. When the task is complete (not for a mid-task handoff), open a PR from the feature branch to `main`:
   - with the GitHub CLI if installed: `gh pr create --base main --fill`;
   - otherwise give the owner the link `https://github.com/<owner>/<repo>/compare/main...<branch>?expand=1` (owner/repo from `git remote get-url origin`).
5. Show the owner the new "Now" block, the files changed, the commit hash, the PR link and what is unverified. Then stop.
