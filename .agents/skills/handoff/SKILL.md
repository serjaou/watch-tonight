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
3. Log line format (1 line per entry in `PROGRESS.md`): `YYYY-MM-DD · <Mac|Windows> · <Antigravity|Claude Code> · `<feat-id>`: <short summary> → [<feat-id>.md](docs/handoffs/<feat-id>.md)`.
4. When the task is complete (not for a mid-task handoff):
   - create `docs/handoffs/<feat-id>.md` with the task metadata, summary/outcome, and full verification command + output evidence;
   - move the feature entry from [feature_list.json](../../../feature_list.json) to the top of `docs/handoffs/done_features.json` with `status: "done"` and a 1-line `evidence` (`<= 160` chars) starting with `docs/handoffs/<feat-id>.md — ...`;
   - add an index row for `<feat-id>` at the top of the `/handoff` table in [docs/metrics.md](../../../docs/metrics.md) linking to `handoffs/<feat-id>.md` (and fill in its spike baseline row in §1.4 if it is a spike);
   - open a PR from the feature branch to `main`:
     - with the GitHub CLI if installed: `gh pr create --base main --fill`;
     - otherwise give the owner the link `https://github.com/<owner>/<repo>/compare/main...<branch>?expand=1` (owner/repo from `git remote get-url origin`).
5. Show the owner the new "Now" block, the files changed, the commit hash, the PR link and what is unverified. Then stop.
