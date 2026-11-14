# Progress

## Now
- **Active feature:** none on this branch. `feat-015` (Split growing state and log docs into index files plus per-entry detail files) is `done` on branch `chore/split-index-files`; its PR waits for the owner's merge. (`feat-008` Session 1 WIP is saved on `origin/spike/tmdb-and-providers` waiting ≥24h after `2026-11-14T14:48:37Z` for Snapshot 2.)
- **State:** `feat-015` delivered:
  - split `feature_list.json` (hot: only `todo|in_progress|blocked` items, `57` lines) and `docs/handoffs/done_features.json` (cold: all `done` items);
  - converted `PROGRESS.md`, `LEARNING.md`, `docs/harness-log.md`, and `docs/metrics.md` into slim index files linked to per-entry detail files in `docs/handoffs/` (`9` files), `docs/learning/` (`3` files), and `docs/harness-log/` (`9` files);
  - wired `AGENTS.md`, `.agents/skills/handoff/SKILL.md`, `.agents/skills/defend/SKILL.md`, `docs/workflow.md`, and `docs/conventions.md`;
  - added line-limit budgets (`feature_list.json <= 120`, etc.), active/done partition checks, `evidence <= 160` chars check, and 1-to-1 index-to-detail sync checks in `tests/harness/test_harness.py`.
- **Last check:** `uv run poe check` green, 2026-11-14 17:01 CET, Mac (ruff check + format check passed, pyright strict 0 errors, import-linter 2/2 kept, pytest 26 passed in 0.78s).
- **Next step:** After merging `feat-015`, switch back to `spike/tmdb-and-providers` (merge `main` into it) on or after `2026-11-15 15:49 CET` to run Snapshot 2 and finish `feat-008` Q7 (or reorder `feat-009` ahead in `feature_list.json` to run the Atlas spike first).
- **Waiting on owner:**
  1. Review and merge the `feat-015` PR (`chore/split-index-files` → `main`).
  2. Wait ≥24h (until after `2026-11-15 15:49 CET`) to run Session 2 of `feat-008` on `spike/tmdb-and-providers` (or reorder `feat-009` ahead in `feature_list.json`).
  3. Before `feat-011`: put LLM API keys in local `.env`.
- **Unverified:** CI on the `feat-015` PR.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
- 2026-11-14 · Mac · Antigravity · `feat-015`: split state/log docs into slim index files + per-entry files in `docs/{handoffs,learning,harness-log}/` → [feat-015.md](docs/handoffs/feat-015.md)
- 2026-11-13 · Mac · Antigravity · `feat-006`: added `docs/metrics.md` and `/handoff` process tracking → [feat-006.md](docs/handoffs/feat-006.md)
- 2026-11-13 · Mac · Antigravity · `feat-014`: validated harness with `validate-harness.mjs` (`60/100` → `92/100`) → [feat-014.md](docs/handoffs/feat-014.md)
- 2026-11-13 · Windows · Claude Code · `feat-013`: recorded owner decisions Q8–Q11, posters, zero-cost budget → [feat-013.md](docs/handoffs/feat-013.md)
- 2026-11-13 · Windows · Claude Code · `feat-005`: wrote `docs/architecture.md` v0 and spike question files `08`–`11` → [feat-005.md](docs/handoffs/feat-005.md)
- 2026-11-12 · Mac · Antigravity · `feat-007`: verified `feat-004` Stop hook and native reviewer on the Mac → [feat-007.md](docs/handoffs/feat-007.md)
- 2026-11-12 · Windows · Claude Code · `feat-004`: first Windows session, Claude Code support (ADR 0003), autonomous runs (ADR 0004) → [feat-004.md](docs/handoffs/feat-004.md)
- 2026-11-12 · Mac · Antigravity · `feat-000`: end-to-end harness dry run (mood prompt validator P4) → [feat-000.md](docs/handoffs/feat-000.md)
- 2026-11-11 · Mac · Antigravity · `feat-001`: repo skeleton, `pyproject.toml`, layers, CI, and core harness v0 → [feat-001.md](docs/handoffs/feat-001.md)
