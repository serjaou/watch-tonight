# Handoff: `feat-009` — Spike: Atlas free tier and vector search

- **Type:** `spike`
- **Date:** 2026-11-15
- **Machine · Tool:** Mac · Antigravity
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `1 (0)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- Built `spikes/09-atlas/probe_atlas.py` and executed it against both the live **MongoDB Atlas M0 free-tier cluster** (`MongoDB 8.0.37`) and the local **`mongodb/mongodb-atlas-local:latest` Docker container** (`MongoDB 9.0.4`, `linux/aarch64` on Colima), recording all empirical results in `spikes/09-atlas/report.json` and `docs/spikes/09-atlas-vector-search.md` (`status: answered`):
  - **Q1 (Free tier limits & 20k-movie storage):** M0 hard limits are `512 MiB` storage, max `3` search/vector indexes total (we need `1`), and max `8,192` vector dimensions. A 20,000-movie corpus fits comfortably at `384`-d (`120.85 MiB` logical / `108.76 MiB` disk = `~27.6%` of M0 with HNSW index), `768`-d (`216.05 MiB` logical = `~54.2%` with HNSW), and `1024`-d (`279.72 MiB` logical = `~70.5%` with HNSW). Packing vectors with `bson.binary.Binary.from_vector(..., BinaryVectorDtype.FLOAT32)` reduces vector BSON bytes by `68.2%` (`17.4%–36.5%` of M0 including HNSW).
  - **Q2 (Pre-filters):** All 5 constraints (`streamable` `$in`, `runtime` `$lte`, `_id` `$nin`, `profile.intensity` `$lte`, `profile.content_warnings` `$nin`) combine in a single `$vectorSearch.filter` (`$and`) with `40/40` valid candidates and `0` violations. Every filtered path must be declared with `{"type": "filter", "path": "..."}` in the `vectorSearch` index (unindexed fields fail with `OperationFailure` code `8`). Verified `_id: {"$nin": [...]}` list sizes from `50` up to `5,000` IDs (`0` leaks, `72–138 ms` on M0).
  - **Q3 (`mongodb/mongodb-atlas-local`):** Confirmed multi-arch OCI manifest (`linux/amd64` + `linux/arm64`) and verified bit-for-bit filter and cosine-score parity between `atlas-local` on Mac ARM and Atlas M0 (`#18602: 0.579791247844696`, `#1056: 0.5737653970718384`, `#7423: 0.5728212594985962`). Index readiness time: **`4.64 s`** for a 50-doc integration-test fixture (`9.23 s` for 20k docs locally; `50.83 s` for 20k docs on M0). Updated `README.md` §Machine setup with Colima (`brew install docker colima && colima start --cpu 4 --memory 4`).
  - **Q4 (Python driver):** `pymongo.AsyncMongoClient` (`pymongo 4.20.0`) replaces deprecated `Motor` and supports full programmatic search index lifecycle (`create_search_index`, `list_search_indexes`, `update_search_index`, `drop_search_index`) via `SearchIndexModel`.
  - **Q5 (Latency):** Over 50 randomized 5-filter `$vectorSearch` queries (`numCandidates=400`, `limit=40`) on 20k docs (384-d): **`p50 = 60.50 ms`**, **`p95 = 120.78 ms`** on Atlas M0 (`p50 = 15.35 ms`, `p95 = 20.98 ms` on `atlas-local`), using only `1.2%` of the tentative `< 10,000 ms` end-to-end p95 budget (`Q7`).

## Verification Evidence
```text
Mac, 2026-11-14 / 2026-11-15:
$ uv run --with "pymongo[srv]>=4.11" python spikes/09-atlas/probe_atlas.py --target atlas
[atlas_m0] 384d stats: {'count': 20000, 'avg_obj_size_bytes': 6335, 'uncompressed_bson_mb': 120.85, 'wiredtiger_storage_mb': 108.17, 'btree_index_mb': 0.59, 'total_collection_disk_mb': 108.76, 'pct_of_512mb_m0_limit_disk': 21.24, 'pct_of_512mb_m0_limit_logical': 23.6}
[atlas_m0] Index ready: {'ready': True, 'elapsed_seconds': 50.83, 'statuses_seen': ['PENDING@0.4s', 'BUILDING@29.67s', 'READY@50.83s']}
[atlas_m0] Pre-filter satisfied=True (returned=40, violations=0)
[atlas_m0] Latency (384d): p50=60.5ms, p95=120.78ms
[atlas_m0] 768d stats: {'count': 20000, 'avg_obj_size_bytes': 11327, 'uncompressed_bson_mb': 216.05, ...}

$ uv run --offline --with "pymongo>=4.11" python spikes/09-atlas/probe_atlas.py --target local --local-uri "mongodb://localhost:27018/?directConnection=true"
[local_darwin_arm64] 50-doc fixture index ready: {'doc_count': 50, 'dims': 384, 'ready': True, 'elapsed_seconds': 4.64, 'statuses_seen': ['PENDING@0.03s', 'BUILDING@3.1s', 'READY@4.64s']}
[local_darwin_arm64] Index ready (20k docs): {'ready': True, 'elapsed_seconds': 9.23, 'statuses_seen': ['PENDING@0.04s', 'BUILDING@1.57s', 'READY@9.23s']}
[local_darwin_arm64] Pre-filter satisfied=True (returned=40, violations=0)
[local_darwin_arm64] Latency (384d): p50=15.35ms, p95=20.98ms

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
26 passed in 0.79s

Reviewer subagent (fdc7498c-442c-45c1-a8f6-77c0961f8d10):
Round 1: "No findings"
```
