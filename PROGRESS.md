# Progress

## Now
- **Active feature:** none in progress. feat-018 is merged (PR #19). Its follow-up (owner decisions of 2026-11-25) is on branch `feat-018-followups`, in a PR that waits for the owner's `tests-approved` label and merge. Next: `/spec` refinement of `feat-030`.
- **State:**
  - feat-018: `POST /search` works end to end with in-memory adapters (no Docker, no key). With the follow-up: unknown request fields → 422; a top-level `availability_updated_at` (the catalogue's newest refresh, read in step 3); 25 acceptance cases, six evals at 100%, 99 tests. `uv run poe serve` runs it locally (`/docs`). Detail and evidence: [feat-018.md](docs/handoffs/feat-018.md).
  - The walking skeleton continues in three parts: part 2 local Atlas (`feat-030`, draft spec `docs/specs/30-atlas-local-search.md`), part 3 real embedder (`feat-028`), part 4 real LLM (`feat-029`). Notes from part 1 for parts 2 and 4 are in their `docs/backlog.md` sections.
  - Facts for feat-030 (checked 2026-11-25): Docker Desktop runs on Windows (server 29.9.3); `mongodb/mongodb-atlas-local` 8.0 is at `8.0.38`, and even that tag is rebuilt, so pin the dated tag `8.0.38-20261124T121746Z` (or the digest); `testcontainers` 4.15 has `MongoDBAtlasLocalContainer`; `.env` has `TMDB_API_KEY`; `MONGODB_URI` in `.env` is the **cloud** M0 cluster, so part 2 must use a separate local-only variable.
  - Active window in `feature_list.json`: `feat-030`, `feat-028`, `feat-029`, `feat-027`, `feat-026`, `feat-031`, `feat-019`.
  - Raw crawl rows (gitignored, Windows laptop only): `spikes/16-recommendation/data/catalog.jsonl` (2026-11-16) and `data/catalog_2026-11-21.jsonl`; also `data/pool_b_movies.jsonl` (spike 16's 300 films, no posters, Spanish ratings or availability).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 99 passed), 2026-11-25, Windows, branch `feat-018-followups`.
- **Next step:**
  - `/spec` for `feat-030` with the owner: refine `docs/specs/30-atlas-local-search.md` with the facts above, then the owner approves it; build after the follow-up PR is merged.
- **Waiting on owner:**
  - **Rotate the Atlas M0 database user's password** and update `.env`: a session command printed it (2026-11-25, [harness log](docs/harness-log/2026-11-25-feat-018-secret-printed-to-session.md)).
  - feat-018 follow-up PR: review it (tests and evals included), add the `tests-approved` label, merge.
  - Refine and approve `feat-030` (`docs/specs/30-atlas-local-search.md`).
- **Unverified:**
  - CI on the follow-up PR.
  - The items under "Unverified" in `docs/handoffs/feat-012.md` and `docs/handoffs/feat-017.md`: extra pre-filters, `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, Q4 on Windows, and multi-month churn rates.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
- 2026-11-25 · Windows · Claude Code · `feat-018` follow-up: unknown request fields → 422, top-level availability date (P6), `httpx` kept; 99 tests; reviewer 1 (2 + 4 low) → [feat-018.md](docs/handoffs/feat-018.md)
- 2026-11-25 · Windows · Claude Code · `feat-018`: walking skeleton part 1, `POST /search` end to end in memory; 10 acceptance tests, 6 evals at 100%, 95 tests; reviewer 2 (13 + 3) → [feat-018.md](docs/handoffs/feat-018.md)
- 2026-11-21 · Windows · Claude Code · `feat-017`: churn from two full crawls 5.3 days apart, verified against `/watch/providers` (G7: ≈ 6 leave/day, ≈ 24.5 admitted/day); daily schedule kept → [feat-017.md](docs/handoffs/feat-017.md)
- 2026-11-16 · Windows · Claude Code · `feat-012`: architecture v1 + ADRs 0005–0008, MVP sliced skeleton-first (active window + `docs/backlog.md`), sizing as guides → [feat-012.md](docs/handoffs/feat-012.md)
- 2026-11-16 · Windows · Claude Code · `feat-016`: answered recommendation spike Q1–Q4 (G7 gate 14,478 films, no IMDb/reviews, v1 mirror schema, K=150 hybrid; $0.13) → [feat-016.md](docs/handoffs/feat-016.md)
- 2026-11-16 · Windows · Claude Code · `feat-011`: answered runtime LLM spike Q1–Q6 (`gpt-6-luna` `$0.00067`/query, 0 schema errors; Gemini free tier not usable for EEA users) → [feat-011.md](docs/handoffs/feat-011.md)
- 2026-11-15 · Mac · Antigravity · `feat-010`: answered embedding runtime spike Q1–Q6 (`fastembed` `bge-small-en-v1.5` 384-d: `p50=5.04ms`, `279MB` RSS, `212MB` disk) → [feat-010.md](docs/handoffs/feat-010.md)
- 2026-11-15 · Mac · Antigravity · `feat-008`: answered TMDB terms, rate limits (25.2 req/s), ES/US/BO coverage, and 24.5h provider churn → [feat-008.md](docs/handoffs/feat-008.md)
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
