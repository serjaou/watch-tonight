# Progress

## Now
- **Active feature:** none on this branch. `feat-009` (Spike: Atlas free tier and vector search) is `done` on branch `spike/atlas-vector-search`; its PR waits for the owner's merge. (`feat-008` Session 1 WIP is saved on `origin/spike/tmdb-and-providers` waiting ≥24h after `2026-11-14T14:48:37Z` — until `2026-11-15 15:49 CET` — for Snapshot 2.)
- **State:** `feat-009` delivered:
  - `spikes/09-atlas/probe_atlas.py` and `spikes/09-atlas/report.json` (probed both live Atlas M0 `MongoDB 8.0.37` and local `mongodb/mongodb-atlas-local:latest` `MongoDB 9.0.4` on Mac ARM Colima via `pymongo 4.20.0` `AsyncMongoClient`);
  - answered all 5 questions in `docs/spikes/09-atlas-vector-search.md` (`status: answered`) and `docs/metrics.md` §1.4:
    - **Q1:** M0 512 MiB limit, max 3 search/vector indexes, max 8,192 dims; 20k synthetic movies fit at 384-d (`120.85 MiB` logical / `108.76 MiB` disk = `~27.6%` w/ HNSW), 768-d (`216.05 MiB` = `~54.2%` w/ HNSW), and 1024-d (`279.72 MiB` = `~70.5%` w/ HNSW); `Binary.from_vector(..., FLOAT32)` cuts vector BSON by `68.2%` (`17.4%–36.5%` of M0);
    - **Q2:** all 5 pre-filters (`streamable` `$in`, `runtime` `$lte`, `_id` `$nin`, `profile.intensity` `$lte`, `profile.content_warnings` `$nin`) combine in one `$vectorSearch` (`40/40` valid, `0` violations; `_id` `$nin` verified up to `5,000` IDs);
    - **Q3:** `mongodb/mongodb-atlas-local` (`linux/arm64` + `linux/amd64`) matched Atlas M0 bit-for-bit; index ready in `4.64 s` (50-doc fixture) / `9.23 s` (20k docs locally) vs `50.83 s` (20k docs on M0); documented Colima in `README.md`;
    - **Q4:** `pymongo.AsyncMongoClient` replaces deprecated `Motor` and supports programmatic `SearchIndexModel` create/list/update/drop;
    - **Q5:** 50-query filtered `$vectorSearch` over 20k docs on M0: `p50 = 60.50 ms`, `p95 = 120.78 ms` (`atlas-local`: `p50 = 15.35 ms`, `p95 = 20.98 ms`).
- **Last check:** `uv run poe check` green, 2026-11-15 11:36 CET, Mac (ruff check + format check passed, pyright strict 0 errors, import-linter 2/2 kept, pytest 26 passed in 0.78s); reviewer round 1: "No findings".
- **Next step:** After merging `feat-009`, either start `feat-010` (Spike: query-time embedding runtime in `docs/spikes/10-embedding-runtime.md`, ready now) or switch to `spike/tmdb-and-providers` (merge `main` into it) on or after `2026-11-15 15:49 CET` to capture Snapshot 2 and finish `feat-008` Q7.
- **Waiting on owner:**
  1. Review and merge the `feat-009` PR (`spike/atlas-vector-search` → `main`).
  2. Wait until `2026-11-15 15:49 CET` (≥24h after Snapshot 1) to run Session 2 of `feat-008` on `spike/tmdb-and-providers` (or reorder `feat-010` ahead in `feature_list.json`).
  3. Before `feat-011`: put LLM API keys in local `.env`.
- **Unverified:** CI on the `feat-009` PR; optional Windows `x86_64` run of `probe_atlas.py --target local` (OCI `linux/amd64` manifest verified).

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
- 2026-11-15 · Mac · Antigravity · `feat-009`: answered Atlas M0 + `atlas-local` vector search spike Q1–Q5 (`p50=60.5ms`/`p95=120.8ms`, 5-way pre-filter, 20k storage) → [feat-009.md](docs/handoffs/feat-009.md)
- 2026-11-14 · Mac · Antigravity · `feat-015`: split state/log docs into slim index files + per-entry files in `docs/{handoffs,learning,harness-log}/` → [feat-015.md](docs/handoffs/feat-015.md)
- 2026-11-13 · Mac · Antigravity · `feat-006`: added `docs/metrics.md` and `/handoff` process tracking → [feat-006.md](docs/handoffs/feat-006.md)
- 2026-11-13 · Mac · Antigravity · `feat-014`: validated harness with `validate-harness.mjs` (`60/100` → `92/100`) → [feat-014.md](docs/handoffs/feat-014.md)
- 2026-11-13 · Windows · Claude Code · `feat-013`: recorded owner decisions Q8–Q11, posters, zero-cost budget → [feat-013.md](docs/handoffs/feat-013.md)
- 2026-11-13 · Windows · Claude Code · `feat-005`: wrote `docs/architecture.md` v0 and spike question files `08`–`11` → [feat-005.md](docs/handoffs/feat-005.md)
- 2026-11-12 · Mac · Antigravity · `feat-007`: verified `feat-004` Stop hook and native reviewer on the Mac → [feat-007.md](docs/handoffs/feat-007.md)
- 2026-11-12 · Windows · Claude Code · `feat-004`: first Windows session, Claude Code support (ADR 0003), autonomous runs (ADR 0004) → [feat-004.md](docs/handoffs/feat-004.md)
- 2026-11-12 · Mac · Antigravity · `feat-000`: end-to-end harness dry run (mood prompt validator P4) → [feat-000.md](docs/handoffs/feat-000.md)
- 2026-11-11 · Mac · Antigravity · `feat-001`: repo skeleton, `pyproject.toml`, layers, CI, and core harness v0 → [feat-001.md](docs/handoffs/feat-001.md)
