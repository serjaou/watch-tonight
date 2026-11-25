---
id: feat-030
stories: [US1, US2, US3]
status: draft   # draft -> approved (set by the owner only)
---
# Walking skeleton, part 2: search on local Atlas

## Goal
Replace part 1's in-memory catalogue and search ([feat-018](18-walking-skeleton.md)) with MongoDB adapters on `mongodb-atlas-local`, and verify what the spikes left unverified: managing the vector index from code, every pre-filter together, the audience rule, and the container on Windows (Q4). Vectors still come from part 1's fake embedder; the real one is part 3 (`feat-028`).

## Acceptance tests (written or approved by the owner)
All marked `@pytest.mark.integration` (they need Docker), in `tests/acceptance/test_atlas_local_search.py`. They load part 1's fictional fixture films, with their fake vectors.

- [ ] **Index lifecycle.** Given an empty database, when the code creates the vector index, waits until it can be queried, updates it (adds a filter path) and drops it, then each step succeeds, and any error is raised, never silenced (spike 09 silenced them) -> `tests/acceptance/test_atlas_local_search.py::test_vector_index_create_update_drop_from_code`
- [ ] **All pre-filters together.** Given the fixture films, when one `$vectorSearch` (`limit=150`) uses every filter path at once (`streamable`, `runtime`, `year`, `original_language`, `profile.intensity`, `profile.content_warnings`, and `_id` not in a 5,000-id list), then it runs without `OperationFailure`, every returned film meets every filter (checked with part 1's step-4 check functions), and every film built to pass is returned -> `tests/acceptance/test_atlas_local_search.py::test_vector_search_applies_all_prefilters_together`
- [ ] **Audience on Atlas.** Given kids and teens requests, and fixture films with a US rating, only a Spanish rating, or none, then the Atlas-backed search returns exactly the films the [audience rule](../architecture.md#decided-owner-and-spikes-2026-11-13-to-2026-11-16) (Q16) accepts. The evidence records which path held the rule: an Atlas pre-filter (an `$or` with the no-rating case) or step 4 -> `tests/acceptance/test_atlas_local_search.py::test_audience_rule_on_atlas_matches_domain_rule`
- [ ] **End to end on Atlas.** Given the API wired to the Atlas adapters, when part 1's success and exclusion scenarios run through `POST /search`, then they pass with the same assertions, and the top-level `availability_updated_at` is the newest date stored in the database (P6) -> `tests/acceptance/test_atlas_local_search.py::test_search_end_to_end_on_atlas`
- [ ] **Database down.** Given the database can't be reached, when `POST /search` is called, then HTTP 503 with `state="service_unavailable"` comes back within a few seconds (a short server-selection timeout), never a hang or empty results, and no step-5 call is made (Q8) -> `tests/acceptance/test_atlas_local_search.py::test_search_returns_503_when_database_is_down`
- [ ] **Seed mapping.** Given a hand-written TMDB bundle (not real TMDB data), when it is mapped and stored, then the document follows the [data model](../architecture.md#5-data-model-mongodb-v1): `streamable` holds only flat-rate offers, as `"country:provider"` for ES, US and BO; `certification_us` and `certification_es` are the first non-empty, non-`NR` value, or `null`; keywords ending in `stinger` are dropped; `collection_id`, `poster_path` and `availability_updated_at` (with its time zone) are set. Storing it twice leaves one document -> `tests/acceptance/test_atlas_local_search.py::test_seed_maps_tmdb_bundle_and_is_idempotent`

## Evidence (recorded in the handoff, not tests)
- Q4: `uv run poe test-all` output on Windows, and on the Mac.
- The seed run on spike 16's 300 films against local Atlas: the document count and one sample document.
- The CI integration job green on the PR.

## Out of scope
- Atlas M0 in the cloud; `numCandidates` and latency at K = 150 on the full corpus (`feat-021`).
- Real embeddings of the 300 films (part 3, `feat-028`).
- The TMDB client as a reusable `MovieSource` port, the crawl, the refresh, the real provider list, Wikidata signals and `quality_score` (`feat-020`).

## Design notes (with C# comparison)
- **Image** (checked 2026-11-25): `mongodb/mongodb-atlas-local:8.0.38-20261124T121746Z`, the dated build of the newest 8.0 patch. Atlas M0 runs MongoDB 8.0; spike 09 used `latest` (9.0). Even `8.0.38` is rebuilt in place, so only the dated tag (or the digest) is reproducible. Updating it is a deliberate one-line change.
- **Driver:** `pymongo`'s `AsyncMongoClient` (Motor is deprecated, feat-009), created with `tz_aware=True`, because pymongo returns naive datetimes otherwise and the evals require dates with a time zone.
- **Index:** one vector index, 384 dimensions, declaring every filter path of the data model (Atlas raises `OperationFailure` on an undeclared path, spike 09). The local index builds asynchronously, so the code waits until it can be queried. A normal index on `availability_updated_at` serves `MovieRepository.latest_availability_update()` (the newest date; feat-020 may switch to the last completed refresh in `ingestion_runs`).
- **Audience:** try the pre-filter first. If Atlas can't express the `$or` with the no-rating case, `CandidateSearch` leaves `audience` out of the pre-filter and step 4 applies it ([ADR 0005](../decisions/0005-closed-vocabulary-mirror-schema.md)). Step 4 re-checks it either way.
- **Movie fields:** `Movie` gains the TMDB fields of the data model (`original_title`, `genres`, `keywords`, `overview`, `tagline`, `credits`, `tmdb_vote_average`, `tmdb_vote_count`, `tmdb_popularity`), optional where TMDB may lack them. `quality_score`, `critic_score` and `awards_count` stay `null` until feat-020. Provenance fields record what the seed knows (`embedding_model` names the fake embedder).
- **Seed** (owner, 2026-11-24): `scripts/seed_skeleton.py` fetches the 300 films of spike 16's `pool_b_profiles.jsonl` (variant `base`) from TMDB with `TMDB_API_KEY` (about 300 calls: details, release dates, watch providers), joins them with the committed profiles, embeds them with the fake embedder, and upserts them. Raw TMDB data is never committed. The tests never depend on it; they use the fictional fixtures. The bundle-to-document mapping lives in `infra`, so `feat-020` can reuse it; the script only fetches and calls it.
- **Tests on one event loop:** the integration tests are `async` and share one loop for the module (pytest-asyncio `loop_scope`), because an `AsyncMongoClient` is bound to the loop it was created on. Part 1's `ApiClient` (one `asyncio.run` per request) can't share a client across requests.
- **Verify, don't assume** ([checkpoint finding 2](../checkpoint-2026-11-16/review.md#finding-2-some-weak-numbers-became-facts-in-the-decision-records)): spike 09 tested the 5,000-id exclusion with only two filters, and never verified index update or drop.
- **CI:** a second job on `ubuntu-latest` runs the integration tests (GitHub's Linux runners have Docker), so the Atlas behaviour is checked on every PR, not only when someone runs `test-all` by hand.
- **Configuration** (owner, 2026-11-25): `pydantic-settings` reads settings from the environment or `.env` (like `IOptions<T>` bound from configuration). The app's database is `WATCH_TONIGHT_MONGODB_URI`, defaulting to the local container. `MONGODB_URI` (the cloud M0 cluster) is never read by default. The seed script refuses any host that isn't `localhost` unless given `--allow-remote`.
- **Running local Atlas by hand** (owner, 2026-11-25): a `compose.yaml` with the pinned image, and `poe` tasks `db-up`, `db-down`, `seed` and `serve-atlas` (the API on the local database, with part 1's fake embedder and LLM). `poe serve` stays in-memory.
- **New dependencies:** `pymongo` and `pydantic-settings`; dev: `testcontainers[mongodb]` 4.15+ (its `MongoDBAtlasLocalContainer` starts and stops the pinned image from pytest, on any machine and in CI, like Testcontainers for .NET). The seed uses `httpx`, already a dev dependency.

## Open questions (must be empty before status: approved)
- None (the database variable and the local tooling were decided by the owner on 2026-11-25; see the design notes).
