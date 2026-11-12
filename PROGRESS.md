# Progress

## Now
- **Active feature:** None (`feat-001` and `feat-000` dry run are `done`; next in queue is `feat-002` Spike: TMDB terms, rate limits and watch-provider coverage for ES, US and BO)
- **State:** Complete core agentic harness built and verified on Mac (`docs/workflow.md`, `docs/product.md`, `docs/decisions/0001..0002`, `LEARNING.md`, `docs/harness-log.md`, `.agents/` skills/reviewer/hooks, `scripts/hooks/stop_gate.py`, `tests/harness/test_harness.py`, and `feat-000` dry run). Ready to test cross-machine handoff on the second PC.
- **Last check:** `uv run poe check` green, 2026-11-12 10:30 (`ruff`, `pyright` strict, `import-linter` 2/2 contracts kept, `pytest` 13 passed).
- **Next step (on the other PC):**
  1. Clone/pull the repo, set personal git identity (`git config user.email ...`), and run `/start` (which runs `uv sync` and `uv run poe check`).
  2. Verify the agent on the second PC picks up context purely from the repo without needing extra explanation (log any gap in `docs/harness-log.md`).
  3. Run `/spec` to refine `feat-002` (`docs/spikes/02-tmdb-and-providers.md`) when ready to start the Week 1 spikes.
- **Waiting on owner:** Switch to the other PC, run `/start` to test the cross-machine handoff, then refine `feat-002`.
- **Unverified:** GitHub Actions CI run on remote and cross-machine handoff on the second PC.

## Log (newest first, 1–3 lines each)
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
