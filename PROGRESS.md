# Progress

## Now
- **Active feature:** `feat-004` Harness review: first Windows session, Claude Code support, inception review · branch `chore/harness-review` (not pushed yet).
- **State:** Done and committed on the branch:
  - stop-gate test made independent of git state (CI on `main` red since 26f3ebf; green once this merges);
  - product language: English only at launch;
  - stepped workflow only (ADR 0004), skills point to AGENTS.md, reviewer/`/defend` diff against `origin/main`, new `docs/conventions.md`, inception docs marked historical;
  - Claude Code adapters (ADR 0003): `.claude/` stubs, Stop hook, `CLAUDE.md`; Windows encoding/BOM fixes in `stop_gate.py`;
  - README machine setup, harness-log entries, backlog items feat-005…feat-009.

  Remaining: the owner reviews the branch, then push, PR, green CI, merge.
- **Last check:** `uv run poe check` green, 2026-11-12, Windows (ruff, pyright strict 0 errors, import-linter 2/2 kept, pytest 20 passed). Real Claude Code Stop hook verified on Windows: blocks on a real lint error, silent when green.
- **Next step:** after merge, `feat-005` (architecture v0 + spike question files). It's a chore, so it's ready.
- **Waiting on owner:**
  1. Install pre-commit on this machine: `uv tool install pre-commit`, then `pre-commit install` (the agent wasn't allowed to install the git hook).
  2. Set up the personal Claude Code profile (`claude-personal`, README "Machine setup") and use it from the next session on.
  3. Review the branch; decide on push + PR. Check the order of feat-005…feat-009.
- **Unverified:**
  - CI on the branch (not pushed).
  - Antigravity Stop hook on Windows: `python3` is the Microsoft Store stub here, and Antigravity isn't installed (feat-009).
  - The Antigravity reviewer's `read_file` tool name: its docs only show `view_file` as an example (feat-009).
  - Claude Code Stop hook on the Mac.

## Log (newest first, 1–3 lines each)
- 2026-11-12 · Windows · Claude Code · feat-004: first Windows session. Installed uv; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, and a reviewer that missed committed work, all fixed. Added Claude Code support (ADR 0003), stepped-only workflow (ADR 0004), English-only launch language, and backlog items feat-005…feat-009.
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
