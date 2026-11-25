# Progress

## Now
- **Active feature:** none in progress. `feat-030` (walking skeleton, part 2: search on local Atlas) is done on branch `feat-030-atlas-local`; its PR #21 (CI `check` and `integration` green) waits for the owner's `tests-approved` label and merge.
- **State:**
  - feat-030: the search runs on `mongodb-atlas-local` (pinned `8.0.38-20261124T121746Z`): 6 acceptance tests (7 cases) green on Windows via testcontainers, so Q4 holds on Windows; all 9 filter paths verified in one query, the audience rule as a pre-filter; spike 16's 300 films seeded from TMDB; `poe db-up` / `seed` / `serve-atlas` / `db-down`. Facts learned (in-place index update fails locally, a missing index returns nothing, `timeoutMS` vs server selection) are in architecture §3 and [feat-030.md](docs/handoffs/feat-030.md).
  - feat-018 (part 1) and its follow-up are merged: `POST /search` in memory, 25 acceptance cases, six evals at 100%.
  - Next in the walking skeleton: part 3 real embedder (`feat-028`), part 4 real LLM (`feat-029`). Neither has a spec yet; their notes are in `docs/backlog.md`.
  - Active window in `feature_list.json`: `feat-028`, `feat-029`, `feat-027`, `feat-026`, `feat-031`, `feat-019`.
  - Raw crawl rows (gitignored, Windows laptop only): `spikes/16-recommendation/data/catalog.jsonl` (2026-11-16) and `data/catalog_2026-11-21.jsonl`; also `data/pool_b_movies.jsonl` (spike 16's 300 films, no posters, Spanish ratings or availability).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 116 passed), plus `pytest -m integration` 7 passed (Docker), 2026-11-25 19:19 CET, Windows.
- **Next step:**
  - After the merge: `/spec` for `feat-028` (real `fastembed` embedder) with the owner; it has no spec yet (start rule 3b).
- **Waiting on owner:**
  - **Rotate the Atlas M0 database user's password** and update `.env`, if not done yet (2026-11-25, [harness log](docs/harness-log/2026-11-25-feat-018-secret-printed-to-session.md)).
  - feat-030 PR: review it (acceptance tests included), add the `tests-approved` label, merge.
  - Refine `feat-028`: be available for its `/spec` interview.
  - On the Mac: run `uv run poe test-all` once (Q4 on the Mac with the pinned image).
- **Unverified:**
  - Q4 on the Mac. (CI's new `integration` job passed on Linux on PR #21, 47 s.)
  - Everything on Atlas M0 (feat-021): in-place index update, audience pre-filter, `numCandidates`, exact search above 10,000.
  - The items under "Unverified" in `docs/handoffs/feat-012.md` and `docs/handoffs/feat-017.md`: `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, multi-month churn rates.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
- 2026-11-25 · Windows · Claude Code · `feat-030`: walking skeleton part 2, search on local Atlas; 7 integration cases green (Q4 on Windows), all pre-filters + audience verified, 300-film seed; reviewer 2 (13 + 3) → [feat-030.md](docs/handoffs/feat-030.md)
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
