# Progress

## Now
- **Active feature:** `feat-004` Harness review: first Windows session, Claude Code support, inception review · branch `chore/harness-review` (not pushed yet).
- **State:** Done and committed on the branch:
  - stop-gate test independent of git state (CI on `main` red since 26f3ebf; green once this merges);
  - product language: English only at launch;
  - workflow (ADR 0004): a ready task runs end to end (build, check, review + fixes, handoff, PR); the owner decides at spec approval, merge and human-decision points; "step by step" on request; `/defend` optional with a target (branch, feature id, commit/range);
  - enforcement: CI `PR gates` (`tests-approved` label for `tests/acceptance/` and `evals/`); pre-commit uses the project's ruff;
  - Claude Code adapters (ADR 0003; Antigravity on Mac, Claude Code on Windows), Windows encoding/BOM fixes in `stop_gate.py`;
  - skills point to AGENTS.md; reviewer sees committed work; `docs/conventions.md`; inception docs marked historical; README machine and repository setup; harness-log entries; backlog feat-005…feat-009.

  Remaining: owner reviews the branch, then push, PR, green CI, merge.
- **Last check:** `uv run poe check` green, 2026-11-12, Windows (ruff, pyright strict 0 errors, import-linter 2/2 kept, pytest 25 passed). `pre-commit run --all-files` passed (gitleaks, ruff check, ruff format). Real Claude Code Stop hook verified on Windows: blocks on a real lint error, silent when green.
- **Next step:** after merge, `feat-005` (architecture v0 + spike question files). It's a chore, so it's ready.
- **Waiting on owner:**
  1. Review the branch; decide on push + PR. Check the order of feat-005…feat-009.
  2. After the merge: GitHub branch protection on `main` and the `tests-approved` label (README "Repository settings").
- **Unverified:**
  - CI and the new `PR gates` workflow on GitHub (branch not pushed).
  - Antigravity on the Mac with this branch: Stop hook after the `stop_gate.py` changes, reviewer tool name `read_file` (its docs only show `view_file`), running `/review` and `/handoff` on its own (feat-009).

## Log (newest first, 1–3 lines each)
- 2026-11-12 · Windows · Claude Code · feat-004: first Windows session. Installed uv; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, a reviewer that missed committed work, and a pre-commit/project ruff mismatch, all fixed. Added Claude Code support (ADR 0003), autonomous task runs with owner gates (ADR 0004), PR gates CI, English-only launch language, and backlog items feat-005…feat-009.
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
