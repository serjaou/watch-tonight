# Progress

## Now
- **Active feature:** none in progress. `feat-018` (walking skeleton, part 1) is done on branch `feat-018-walking-skeleton`; its PR waits for the owner's `tests-approved` label and merge.
- **State:**
  - feat-018: `POST /search` works end to end with in-memory adapters (no Docker, no key): all 10 acceptance tests (23 cases), the six deterministic evals at 100%, 95 tests. `uv run poe serve` runs it locally (`/docs`). Detail and evidence: [feat-018.md](docs/handoffs/feat-018.md).
  - The walking skeleton continues in three parts: part 2 local Atlas (`feat-030`, draft spec `docs/specs/30-atlas-local-search.md`), part 3 real embedder (`feat-028`), part 4 real LLM (`feat-029`). Notes from part 1 for parts 2 and 4 are in their `docs/backlog.md` sections.
  - Owner decisions of 2026-11-24 are recorded in the specs, ADR 0005, architecture §3 and `docs/backlog.md` (four-part split, content limits as `feat-031` after `feat-026`, findability work in `feat-027`).
  - Active window in `feature_list.json`: `feat-030`, `feat-028`, `feat-029`, `feat-027`, `feat-026`, `feat-031`, `feat-019`.
  - Raw crawl rows (gitignored, Windows laptop only): `spikes/16-recommendation/data/catalog.jsonl` (2026-11-16) and `data/catalog_2026-11-21.jsonl`; also `data/pool_b_movies.jsonl` (spike 16's 300 films, no posters, Spanish ratings or availability).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 95 passed), 2026-11-25 10:38 CET, Windows.
- **Next step:**
  - After the merge: `/spec` refinement of `feat-030` with the owner (its spec is a draft; start rule 3b), then build it.
  - Start Docker Desktop before part 2 (`feat-030`): its integration tests answer Q4 on Windows.
- **Waiting on owner:**
  - feat-018 PR: review it (tests and evals included), add the `tests-approved` label, merge.
  - Three decisions from the feat-018 review (detail in [feat-018.md](docs/handoffs/feat-018.md)): `httpx` or `httpx2` as the dev dependency; unknown request fields ignored or rejected with 422 (recommended: reject); freshness on a zero-result response.
  - Refine `feat-030`: review and approve `docs/specs/30-atlas-local-search.md`.
- **Unverified:**
  - CI on the feat-018 PR.
  - The items under "Unverified" in `docs/handoffs/feat-012.md` and `docs/handoffs/feat-017.md`: extra pre-filters, `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, Q4 on Windows, and multi-month churn rates.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
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
