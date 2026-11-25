# Handoff: `feat-030` — Walking skeleton, part 2: search on local Atlas

- **Type:** `feature` · spec [docs/specs/30-atlas-local-search.md](../specs/30-atlas-local-search.md) (approved 2026-11-25)
- **Date:** 2026-11-25
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (13 + 3)`: round 1 found 1 high (a broken `.env.example` line), 3 medium and 9 low; round 2 confirmed every fix and found 3 low, fixed after it.
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- **What works:** the search from part 1 now runs on `mongodb-atlas-local`, through `MongoCatalogue` (`MovieRepository` + `CandidateSearch`). The vector index is managed from code, the pre-filter carries every limit, the seed loads spike 16's 300 films from TMDB, and `poe serve-atlas` serves the API on the local database. The LLM and the embedder are still part 1's fakes.
- **All 6 acceptance tests of the spec pass** (7 cases, `@pytest.mark.integration`, testcontainers): index lifecycle, all pre-filters together, audience on Atlas (kids, teens), end to end on Atlas (part 1's success and exclusion assertions), database down or index missing → 503, seed mapping.
- **Verified for the first time** (`mongodb-atlas-local:8.0.38-20261124T121746Z`, Windows):
  - **Q4:** `$vectorSearch` runs on Windows (testcontainers and compose). The Mac run is still to do.
  - **All 9 filter paths in one `$vectorSearch`** (availability, `_id` `$nin` with 5,000 ids, runtime, intensity, `avoid`, year range, language, US and Spanish ratings through the audience rule), with films that each break exactly one limit, so each filter is shown to exclude on its own.
  - **The audience rule works as a pre-filter:** an `$or` with `$eq: null` for the no-rating case. It runs in the database and again in step 4.
  - **Index lifecycle:** create and drop work from code. The same name with a different definition raises; the same definition again is a no-op. **In-place `updateSearchIndex` fails for a vector index** (`"mappings" is required`, and the command has no `type` field), so a definition change drops and re-creates the index.
  - **A missing index makes `$vectorSearch` return nothing, not an error,** so the adapter checks the index when a search finds nothing and answers 503 instead of an empty *Partial*.
  - **pymongo's `timeoutMS` replaces the server-selection timeout** (a down database took 10.2 s instead of 3 s), so the client uses `socketTimeoutMS` to bound stalled reads.
- **Code:**
  - `infra/mongodb.py`: client (`tz_aware=True`, 3 s server selection, 10 s socket timeout), document mapping, pre-filter, index create/update/drop with readiness waits, `ensure_catalogue`, `wait_until_searchable`, `MongoCatalogue`, `ATLAS_LOCAL_IMAGE`.
  - `infra/tmdb_mapping.py`: TMDB bundle → `Movie` (flat-rate only in ES/US/BO, first non-empty non-`NR` rating, no `*stinger` keywords, top 5 cast, admission data checks, `unstreamable_since` when it streams nowhere).
  - `infra/settings.py`: `WATCH_TONIGHT_MONGODB_URI` (local by default) and the local-host guard.
  - `domain`: `Movie` gains the TMDB data-model fields; the audience rule is one table (`AUDIENCE_RULES`) used by step 4 and the pre-filter.
  - `compose.yaml`, `poe db-up` / `db-down` / `seed` / `serve-atlas`, `scripts/seed_skeleton.py`, `scripts/serve_atlas.py`, `.env.example`, the CI `integration` job.
- **Dependencies:** `pymongo` 4.20, `pydantic-settings` 2.16; dev `testcontainers[mongodb]` 4.15.
- **Owner decisions (2026-11-25):** the local-only `WATCH_TONIGHT_MONGODB_URI` with a seed guard; `compose.yaml` and the `poe` tasks.

## Notes for later features
- **feat-021 (M0):** check the in-place index update, the audience pre-filter, `numCandidates`, and `exact: true` with a `limit` above 10,000 (notes in `docs/backlog.md`).
- **feat-020 (ingest):** reuse `movie_from_bundle`, but keep the earliest `unstreamable_since` on refresh; the freshness date could come from `ingestion_runs`.
- **feat-022 (ranking):** Atlas scores are `(1 + cos) / 2`, the in-memory catalogue's are cosine; put them on one scale.

## Verification Evidence
```text
$ uv run poe check   (2026-11-25 19:19 CET, Windows)
Poe => ruff check src tests scripts evals
All checks passed!
Poe => ruff format --check src tests scripts evals
44 files already formatted
Poe => pyright
0 errors, 0 warnings, 0 informations
Poe => lint-imports
Domain layer is independent KEPT
Application layer depends only on domain KEPT
Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration'
116 passed, 7 deselected in 8.08s

$ uv run pytest -m integration -rA   (Docker Desktop 29.9.3, image pulled: 2.1 GB, digest sha256:7320595f400f...)
PASSED test_vector_index_create_update_drop_from_code
PASSED test_vector_search_applies_all_prefilters_together
PASSED test_audience_rule_on_atlas_matches_domain_rule[kids-expected0]
PASSED test_audience_rule_on_atlas_matches_domain_rule[teens-expected1]
PASSED test_search_end_to_end_on_atlas
PASSED test_search_returns_503_when_database_is_down
PASSED test_seed_maps_tmdb_bundle_and_is_idempotent
7 passed, 116 deselected in 25.66s   (28 s with the container start; the two ERROR log lines are the expected 503 cases)

$ uv run poe db-up && uv run poe seed   (all 300 films, before the review)
Profiles: 300 (spike 16, variant base)
TMDB bundles: 300 of 300
Stored: 300 upserted; 300 in 'movies'; 300 searchable
Sample: {'_id': 170, 'title': '28 Days Later', 'year': 2002, 'certification_us': 'R', 'certification_es': '18', 'streamable': ['ES:2241', 'ES:149', 'BO:1899'], 'availability_updated_at': datetime(2026, 11, 25, 17, 51, 41, 136000, tzinfo=UTC)}
(21 s; after the review's reordering, a 5-film run gave 5 of 5 stored and searchable)

$ WATCH_TONIGHT_MONGODB_URI="mongodb+srv://...example.mongodb.net/" uv run python scripts/seed_skeleton.py
WATCH_TONIGHT_MONGODB_URI is not a database on this machine. Refusing to seed; pass --allow-remote if you really mean it.

$ uv run poe serve-atlas   (real HTTP, 300 seeded films, fake LLM and embedder)
200 success 2026-11-25T17:51:41.136000Z
   10373 Quadrophenia 1979 ['Movistar Plus+ Ficción Total']
   489 Good Will Hunting 1997 ['Netflix', 'Movistar Plus+ Ficción Total']   (5 results; order is meaningless with fake vectors)
trace: {'understand': 0.037, 'embed': 0.199, 'retrieve': 123.622, 'freshness': 4.33, 'check': 0.306, 'pick_and_pitch': 0.069}

$ in-place update probe (local Atlas, 2026-11-25)
plain -> "mappings" is required
type=vectorSearch -> BSON field 'updateSearchIndex.type' is an unknown field.
```

## Unverified
- Q4 on the Mac (`uv run poe test-all` there).
- CI's new `integration` job (first run on the PR).
- Everything on Atlas M0 (feat-021).
