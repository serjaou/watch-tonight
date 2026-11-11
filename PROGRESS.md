# Progress

## Now
- **Active feature:** `feat-001` Repo skeleton and harness v0 (`type: chore`)
- **State:** Local repo skeleton and harness v0 complete (`.gitignore`, `.gitattributes`, `.env.example`, `README.md`, `AGENTS.md`, `PROGRESS.md`, `feature_list.json`, `.python-version`, `pyproject.toml`, `uv.lock`, Clean Architecture package skeleton in `src/watch_tonight/`, `tests/test_smoke.py`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`).
- **Last check:** `uv run poe check` green, 2026-11-11 20:16 (`ruff`, `pyright` strict, `import-linter` 2/2 contracts kept, `pytest` 1 passed).
- **Next step:** Commit and push to verify GitHub Actions CI is green, and refine `docs/spikes/02-tmdb-and-providers.md` for `feat-002`.
- **Waiting on owner:** refine `feat-002` (create `docs/spikes/02-tmdb-and-providers.md` questions) and decide on branching/ways of working before pushing.
- **Unverified:** GitHub Actions CI run on remote and handoff to the Windows laptop.

## Log (newest first, 1–3 lines each)
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
