# Handoff: `feat-001` — Repo skeleton and core harness setup

- **Type:** `chore`
- **Date:** 2026-11-11
- **Machine · Tool:** Mac · Antigravity
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `n/a` *(bootstrap)*
- **Escaped / owner fixes:** `3` *(caught in `feat-001`/`004`, logged in [docs/harness-log.md](../harness-log.md))*

## Summary & Outcome
- Drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, and added Step 1 repo hygiene files.
- Added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers (`domain`, `application`, `infra`, `api`, `mcp_server`, `jobs`), `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), `.github/workflows/ci.yml`, and core harness files (`PROGRESS.md`, `LEARNING.md`, skills, Stop hook, `tests/harness/test_harness.py`).

## Verification Evidence
```text
uv run poe check
-> ruff check: All checks passed!
-> ruff format --check: 10 files already formatted
-> pyright: 0 errors, 0 warnings
-> lint-imports: 2 kept, 0 broken
-> pytest: 5 passed (including tests/harness/test_harness.py)
```
