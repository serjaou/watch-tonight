# Handoff: `feat-015` — Split growing state and log docs into index files plus per-entry detail files

- **Type:** `chore`
- **Date:** 2026-11-14
- **Machine · Tool:** Mac · Antigravity
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `1 (0)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- Implemented a **Hot / Cold JSON split** for the backlog (`feature_list.json` holds only active/upcoming `todo|in_progress|blocked` items — 57 lines — while completed `done` items move to `docs/handoffs/done_features.json`), and converted `PROGRESS.md`, `LEARNING.md`, `docs/harness-log.md`, and `docs/metrics.md` into slim, bounded index files that link to per-entry detail files:
  - `docs/handoffs/<feat-id>.md` (backfilled for `feat-001`, `feat-000`, `feat-004`, `feat-007`, `feat-005`, `feat-013`, `feat-014`, `feat-006`, plus `feat-015`);
  - `docs/learning/<YYYY-MM-DD>-<slug>.md` (backfilled for `2026-11-12-feat-001.md`, `2026-11-12-feat-000.md`, `2026-11-13-feat-004-007.md`);
  - `docs/harness-log/<YYYY-MM-DD>-<slug>.md` (backfilled for all 9 harness incidents across `feat-001`, `feat-004`, `feat-007`, and `feat-014`).
- Updated `AGENTS.md`, `.agents/skills/handoff/SKILL.md`, `.agents/skills/defend/SKILL.md`, `docs/workflow.md`, and `docs/conventions.md` to maintain the hot/cold split and index + detail pattern automatically.
- Added automated sensors in `tests/harness/test_harness.py`:
  - enforces line limits on all hot/index files (`AGENTS.md <= 150`, `feature_list.json <= 120`, `PROGRESS.md <= 80`, `LEARNING.md <= 120`, `docs/harness-log.md <= 100`, `docs/metrics.md <= 150`);
  - enforces that `feature_list.json` contains no `done` items, `docs/handoffs/done_features.json` contains only `done` items, and dependency/uniqueness invariants hold across both files combined;
  - enforces `len(evidence) <= 160` and `docs/handoffs/<feat-id>.md` existence + link for every `done` feature;
  - enforces 1-to-1 link synchronization (no broken links, no unindexed orphan files) between `PROGRESS.md`/`docs/metrics.md`/`done_features.json` ↔ `docs/handoffs/`, `LEARNING.md` ↔ `docs/learning/`, and `docs/harness-log.md` ↔ `docs/harness-log/` (verified failing sensor with a temporary `docs/handoffs/orphan.md`).

## Verification Evidence
```text
Mac, 2026-11-14:
$ uv run poe check
Poe => ruff check src tests scripts
All checks passed!
Poe => ruff format --check src tests scripts
14 files already formatted
Poe => pyright
0 errors, 0 warnings, 0 informations
Poe => lint-imports
Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration'
..........................                                               [100%]
26 passed in 0.78s

Sensor failure check:
Created temporary docs/handoffs/orphan.md -> pytest test_index_and_detail_files_are_synced exited 1 (unindexed files=['orphan.md']); removed temporary file.

Reviewer subagent (e5bea56d-c96d-463e-a821-cbcf1c363e5e):
Round 1: "No findings"
```
