---
id: feat-009
type: spike
status: answered
timebox: 2 sessions
---
# Spike: Atlas free tier, vector-search pre-filters and the atlas-local image

## Why
Query step 3 (filtered vector search), the shape of `streamable`, the corpus size and the integration tests all depend on what Atlas supports for free. Architecture open questions Q3 and Q4.

## Questions & Findings
Each answer records the finding, the evidence (official documentation links, command and output from `spikes/09-atlas/probe_atlas.py` / `spikes/09-atlas/report.json`), and what it changes in the architecture.

---

### 1. Free tier limits
> Storage, number of search/vector indexes, maximum vector dimensions. Does a 20k-movie corpus (document + one vector) fit, and with how much headroom?
> - *Changes:* corpus size.

- **Finding:**
  1. **Atlas M0 Free Tier hard limits:**
     - **Storage:** **512 MiB** (`536,870,912` bytes) across all databases, collections, B-tree indexes, and search/vector index metadata on the cluster.
     - **Search / Vector Search index count:** Maximum **3** search/vector indexes total on an M0 cluster. `watch-tonight` requires only **1** `vectorSearch` index (`movies_vector_idx` on `movies.embedding`, with all 5 pre-filter paths declared inside that single index), leaving **2** spare index slots.
     - **Maximum vector dimensions (`numDimensions`):** **Up to 8,192 dimensions** per vector field (`cosine`, `euclidean`, or `dotProduct`).
  2. **20,000-movie corpus storage & headroom (measured on live Atlas M0 `MongoDB 8.0.37` + `bson.encode` models in `spikes/09-atlas/report.json`):**
     - A realistic `movies` document (title, year, runtime, genres, 5 keywords, 320-char overview, director + 5 cast credits, `poster_path`, 1–5 `streamable` entries, full `profile` subdocument with 350-char summary, `source_hash`, timestamps) uses **`1,424` bytes of BSON metadata** before the embedding vector.
     - **Yes — 20,000 movies fit comfortably at `384`, `768`, and `1024` dimensions:**

       | Vector Dimensions | Encoding | Avg Doc Size (`B`) | 20k Uncompressed BSON (`MiB`) | 20k WiredTiger Disk + `_id` Index (`MiB`) | Est. HNSW Index (`MiB`) | Est. Total (`MiB` / `%` of 512 MiB) | Headroom |
       |---:|---|---:|---:|---:|---:|---:|---|
       | **384-d** | BSON `double` array | `6,335` | `120.85` | `108.76` *(measured)* | `~32.35` | **`~141.1 MiB` (`27.6%`)** | **~3.6× (~371 MiB free)** |
       | **384-d** | BSON `Binary` `FLOAT32` | `2,983` | `56.89` | `~52.0` *(est.)* | `~32.35` | **`~89.2 MiB` (`17.4%`)** | **~5.7× (~423 MiB free)** |
       | **768-d** | BSON `double` array | `11,327` | `216.05` | `~183.4` *(measured delta)* | `~61.65` | **`~277.6 MiB` (`54.2%`)** | **~1.8× (~234 MiB free)** |
       | **768-d** | BSON `Binary` `FLOAT32` | `4,520` | `86.22` | `~78.0` *(est.)* | `~61.65` | **`~147.9 MiB` (`28.9%`)** | **~3.5× (~364 MiB free)** |
       | **1024-d** | BSON `double` array | `14,666` | `279.72` | `~240.0` *(est.)* | `~81.18` | **`~360.9 MiB` (`70.5%`)** | **~1.4× (~151 MiB free)** |
       | **1024-d** | BSON `Binary` `FLOAT32` | `5,538` | `105.62` | `~95.0` *(est.)* | `~81.18` | **`~186.8 MiB` (`36.5%`)** | **~2.7× (~325 MiB free)** |

  3. **Why `Binary.from_vector(..., FLOAT32)` saves 68% of vector BSON size:** Standard BSON arrays encode each element as an 8-byte IEEE-754 `double` plus its ASCII array index key (`"0"`, `"1"`, …, `"383"`), costing `~12.8 bytes/dim` (`4,903` B for 384 floats). PyMongo 4.10+ / MongoDB 8.0+ supports `bson.binary.Binary.from_vector(vec, BinaryVectorDtype.FLOAT32)` (BSON Binary Subtype 9), packing contiguous 4-byte `float32` values (`1,559` B for 384 floats) while remaining natively indexable by `$vectorSearch`. Even without binary vector packing, standard float arrays fit a 20k corpus at 384d (`27.6%` of M0) and 768d (`54.2%` of M0).
- **Evidence:**
  - [MongoDB Atlas M0 Free Cluster Limitations](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/) & [Atlas Vector Search Limits](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/#limits).
  - Command and live M0 output (`spikes/09-atlas/report.json`):
    ```bash
    uv run --with "pymongo[srv]>=4.11" python spikes/09-atlas/probe_atlas.py --target atlas
    # [atlas_m0] 384d stats: {'count': 20000, 'avg_obj_size_bytes': 6335, 'uncompressed_bson_mb': 120.85,
    #   'wiredtiger_storage_mb': 108.17, 'btree_index_mb': 0.59, 'total_collection_disk_mb': 108.76,
    #   'pct_of_512mb_m0_limit_disk': 21.24, 'pct_of_512mb_m0_limit_logical': 23.6}
    # [atlas_m0] 768d stats: {'count': 20000, 'avg_obj_size_bytes': 11327, 'uncompressed_bson_mb': 216.05, ...}
    ```
- **Changes:**
  - **Corpus size ceiling confirmed:** Atlas M0 comfortably holds the full **20,000-movie target corpus** whether `feat-010` chooses a `384`-d, `768`-d, or `1024`-d embedding model. (If `feat-010` picks `768`-d or `1024`-d, storing embeddings as `Binary.from_vector(..., FLOAT32)` is an optional one-line optimization that keeps total M0 usage under `37%`.)

---

### 2. Pre-filters
> Can one `$vectorSearch` pre-filter combine:
> - "array field `streamable` contains any of a list of strings";
> - `runtime ≤ N`;
> - `_id` not in a list of up to ~50 IDs;
> - `profile.intensity ≤ N` and "`profile.content_warnings` contains none of a list" (P3 avoid constraints, architecture Q11)?
>
> How must those fields be indexed? Is there a limit on list sizes?
> - *Changes:* the `streamable` design, query steps 3 and 4, US2 and US3 (`exclude_ids`).

- **Finding:**
  1. **All 5 constraints combine in a single `$vectorSearch` `filter` (`$and`):**
     - Verified on 20,000 synthetic movies on Atlas M0 (`spikes/09-atlas/report.json` → `atlas_m0.prefilter_verification`):
       ```python
       filter = {
           "$and": [
               {"streamable": {"$in": ["ES:8", "ES:337", "ES:119"]}},
               {"runtime": {"$lte": 120}},
               {"_id": {"$nin": exclude_50_ids}},
               {"profile.intensity": {"$lte": 3}},
               {"profile.content_warnings": {"$nin": ["sexual_violence", "animal_harm", "self_harm"]}},
           ]
       }
       ```
     - Returned **`40/40` valid candidates with `0` constraint violations** (`all_constraints_satisfied: true`).
     - Specifically verified that `{"profile.content_warnings": {"$nin": [...]}}` on an array field correctly returns both movies with **empty** `content_warnings: []` (`26/40` returned docs) and movies with **non-overlapping** warnings like `["gore", "substance_abuse"]` (`14/40` returned docs), while excluding every movie whose array intersects the forbidden list.
  2. **How pre-filter fields must be indexed:**
     - Every field path used inside `$vectorSearch.filter` **must** be declared with `{"type": "filter", "path": "<field_path>"}` inside the `vectorSearch` index's `fields` list:
       ```json
       {
         "fields": [
           {"type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine"},
           {"type": "filter", "path": "streamable"},
           {"type": "filter", "path": "runtime"},
           {"type": "filter", "path": "_id"},
           {"type": "filter", "path": "profile.intensity"},
           {"type": "filter", "path": "profile.content_warnings"}
         ]
       }
       ```
     - Attempting to filter on a field not declared as `type: "filter"` (`year` in our test) fails immediately with `pymongo.errors.OperationFailure` (error code `8`):
       `PlanExecutor error during aggregation :: caused by :: Path 'year' needs to be indexed as filter`.
  3. **List size limits on `$in` / `$nin`:**
     - Tested `_id: {"$nin": [...]}` inside `$vectorSearch.filter` across list sizes of **`50`, `100`, `250`, `500`, `1,000`, `2,000`, and `5,000` IDs**:
       - **All 7 list sizes succeeded (`ok: true`, `20/20` returned, `0` leaked excluded IDs)**.
       - Latency remained fast (`72–138 ms` across `250`–`5,000` excluded IDs; `93.83 ms` at `5,000` IDs).
       - This provides **100× headroom** above the `~50` excluded IDs needed by US3 ("Show me 5 different ones").
- **Evidence:**
  - [Atlas Vector Search Pre-Filter Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/#atlas-vector-search-pre-filter).
  - Empirical results in `spikes/09-atlas/report.json` (`atlas_m0.prefilter_verification`).
- **Changes:**
  - **Confirms `streamable: ["ES:8", "US:8", ...]` flattened string-array design** (`docs/architecture.md` §5).
  - **Confirms Query Step 3 (`docs/architecture.md` §3):** all five constraints (`streamable` `$in`, `runtime` `$lte`, `_id` `$nin`, `profile.intensity` `$lte`, and `profile.content_warnings` `$nin`) can be pushed down directly into the `$vectorSearch` pre-filter so all top 30–50 candidates returned by Atlas already satisfy P1, US2, US3, and P3 (with Step 4 keeping its deterministic in-memory guard as defense-in-depth).

---

### 3. Local image
> Does the `mongodb/mongodb-atlas-local` Docker image run `$vectorSearch` with the same filters on the Mac (ARM) and on Windows (x86, Docker Desktop)? How long does a search index take to become queryable after creation?
> - *Changes:* integration tests (`poe test-all`), test setup and teardown.

- **Finding:**
  1. **Multi-architecture image support (`linux/arm64` + `linux/amd64`) & filter parity:**
     - `docker manifest inspect mongodb/mongodb-atlas-local:latest` confirms official OCI images for both **`linux/amd64`** (`sha256:af6a81d98205d7985931726368ed02b00d24b59e16d151f3960d7de4bd8f53a5`, used by Windows x86 Docker Desktop and GitHub Actions `ubuntu-latest`) and **`linux/arm64`** (`sha256:ef3afdc5444ec35a8637866b7488c8e936031236654418bd88f29c541dc85fd8`, used by Apple Silicon Mac).
     - Both bundle `mongod` (`MongoDB 9.0.4` in `latest`) and the `mongot` (Java/Lucene) search coordinator inside a single container.
     - **Verified on Mac ARM (`local_darwin_arm64` via Colima `linux/aarch64`, `spikes/09-atlas/report.json`):**
       - Ran the exact same 20,000-document corpus and 5-way `$vectorSearch` pre-filter (`streamable` `$in`, `runtime` `$lte`, `_id` `$nin`, `profile.intensity` `$lte`, `profile.content_warnings` `$nin`) against `mongodb/mongodb-atlas-local:latest`.
       - **Bit-for-bit parity with Atlas M0:** returned the exact same `40/40` candidates (`0` violations, `26` empty-warning docs + `14` disjoint-warning docs) and identical top-3 IDs and cosine similarity scores (`#18602: 0.579791247844696`, `#1056: 0.5737653970718384`, `#7423: 0.5728212594985962`), identical `OperationFailure (code 8)` on unindexed field `year`, and `100%` pass on `_id: {"$nin": [...]}` list sizes `50` through `5,000`.
       - Local container query latency over 20k docs (50 queries): **`p50 = 15.35 ms`**, **`p95 = 20.98 ms`** (`min = 12.16 ms`, `max = 27.65 ms`).
       - *(Note: `probe_atlas.py --target local` can also be run on the Windows laptop at any time to append `local_windows_amd64` to `report.json`.)*
  2. **Index creation readiness time (measured on both fixture size and full 20k corpus):**

     | Environment | Corpus Size (`384`-d) | Status Progression | Time to `READY` (`queryable=True`) |
     |---|---:|---|---:|
     | **`mongodb-atlas-local` (Mac ARM)** | **50 docs** *(integration-test fixture size)* | `PENDING@0.03s` → `BUILDING@3.1s` → `READY@4.64s` | **`4.64 s`** |
     | **`mongodb-atlas-local` (Mac ARM)** | **20,000 docs** *(full corpus)* | `PENDING@0.04s` → `BUILDING@1.57s` → `READY@9.23s` | **`9.23 s`** |
     | **Atlas M0 Free Tier (cloud)** | **20,000 docs** *(full corpus)* | `PENDING@0.4s` → `BUILDING@29.67s` → `READY@50.83s` | **`50.83 s`** |

- **Evidence:**
  - [Run Atlas Search and Vector Search Locally with Docker](https://www.mongodb.com/docs/atlas/cli/current/atlas-cli-deploy-docker/).
  - Commands and output (`spikes/09-atlas/report.json` → `local_darwin_arm64` and `atlas_m0`):
    ```bash
    docker run -d --rm --name watch-tonight-atlas-local -p 27018:27017 mongodb/mongodb-atlas-local:latest
    uv run --offline --with "pymongo>=4.11" python spikes/09-atlas/probe_atlas.py \
      --target local --local-uri "mongodb://localhost:27018/?directConnection=true"
    # [local_darwin_arm64] 50-doc fixture index ready: {'doc_count': 50, 'dims': 384, 'ready': True,
    #   'elapsed_seconds': 4.64, 'statuses_seen': ['PENDING@0.03s', 'BUILDING@3.1s', 'READY@4.64s'], ...}
    # [local_darwin_arm64] Index ready (20k docs): {'ready': True, 'elapsed_seconds': 9.23,
    #   'statuses_seen': ['PENDING@0.04s', 'BUILDING@1.57s', 'READY@9.23s'], ...}
    # [local_darwin_arm64] Pre-filter satisfied=True (returned=40, violations=0)
    # [local_darwin_arm64] Latency (384d): p50=15.35ms, p95=20.98ms
    ```
- **Changes:**
  - **Integration test fixture design (`tests/integration/`, `poe test-all`):**
    1. Because `create_search_index()` returns immediately while `mongot` builds the Lucene/HNSW graph asynchronously (`~4.6 s` for 50 docs locally), integration tests must **never** query immediately or use a hardcoded `sleep()`.
    2. Use a **session-scoped pytest fixture** that seeds a small fixture corpus (`~20–50` movies), creates `movies_vector_idx` once, and polls `collection.list_search_indexes()` until `status == "READY" and queryable is True` (adding only `~5 s` once per `poe test-all` run).
    3. Reuse that index across tests instead of dropping/recreating the vector search index per test function.
  - **macOS setup documentation (`README.md`):** Note that `brew install docker` on macOS installs only the CLI client; pair it with `brew install colima && colima start --cpu 4 --memory 4` (or Docker Desktop) and map a free host port (e.g. `-p 27018:27017`) if Homebrew `mongodb-community` is using `27017`.

---

### 4. Python driver
> Is PyMongo's async API the current recommendation (vs Motor)? Can search indexes be created and updated from code?
> - *Changes:* the `infra` MongoDB adapter, index setup in the ingest job.

- **Finding:**
  1. **Use `pymongo.AsyncMongoClient` — `Motor` is officially deprecated:**
     - MongoDB officially deprecated **Motor** on **May 14, 2025** (standard support ends May 14, 2026; final EOL in 2027) in favor of PyMongo's native `asyncio` client: `from pymongo import AsyncMongoClient` (Generally Available since PyMongo 4.13; verified here on **`pymongo 4.20.0`**).
     - Unlike `Motor` (which delegated operations to synchronous PyMongo over a thread pool), `AsyncMongoClient` performs native `asyncio` socket I/O directly on the event loop. (In C#/.NET terms, `Motor` was `Task.Run(() => SyncDriver())` over thread-pool threads, whereas `AsyncMongoClient` is true non-blocking `async`/`await` all the way down to the socket.)
     - Note on packaging: in `pymongo 4.20.0`, `dnspython` is included or resolved without needing the legacy `[srv]` extra (which emits a harmless warning in `uv`).
  2. **Programmatic search index lifecycle works end-to-end from `AsyncMongoClient`:**
     - Verified all four operations asynchronously against MongoDB `8.0.37` in `spikes/09-atlas/probe_atlas.py`:
       - **Create:** `await collection.create_search_index(SearchIndexModel(definition=..., name="movies_vector_idx", type="vectorSearch"))`
       - **Inspect / poll readiness:** `cursor = await collection.list_search_indexes(name="movies_vector_idx"); indexes = await cursor.to_list()`
       - **Update in place:** `await collection.update_search_index("movies_vector_idx", new_definition)` (`updated_via_code: true` in `report.json`)
       - **Drop:** `await collection.drop_search_index("movies_vector_idx")`
- **Evidence:**
  - [PyMongo Async Migration Guide (Motor to PyMongo Async)](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/) & [PyMongo Atlas Vector Search Indexes](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/indexes/atlas-search-index/).
  - Verified on `pymongo 4.20.0` (`pymongo.asynchronous.mongo_client.AsyncMongoClient`) in `spikes/09-atlas/report.json`.
- **Changes:**
  - **Single MongoDB driver dependency:** Add `pymongo>=4.13` ( plus `dnspython>=2.6` for `mongodb+srv://` URIs) when building the `infra` MongoDB adapter; **never add `motor`**.
  - **Code-first index management:** The offline ingest/embed job (and integration test bootstrap) will ensure `movies_vector_idx` exists and matches the current schema via `create_search_index` / `update_search_index` using `SearchIndexModel`.

---

### 5. Latency
> p50/p95 of one filtered vector search over ~20k documents on the free tier.
> - *Changes:* the p95 latency budget (open question Q7).

- **Finding:**
  - Measured **50 consecutive randomized filtered `$vectorSearch` queries** (after 5 warmup queries) over **20,000 synthetic documents (`384`-d)** on the live Atlas M0 free-tier cluster (`cluster0.n32tseq.mongodb.net`), with `numCandidates: 400`, `limit: 40`, and all 5 pre-filters active (`streamable` `$in` 3 providers, `runtime <= 135`, `_id` `$nin` 50 random IDs, `profile.intensity <= 4`, `profile.content_warnings` `$nin` 2 warnings):

    | Metric | Measured Latency (`ms`) |
    |---|---:|
    | **`min`** | `46.23 ms` |
    | **`p50` (median)** | **`60.50 ms`** |
    | **`mean`** | `71.69 ms` |
    | **`p90`** | `115.75 ms` |
    | **`p95`** | **`120.78 ms`** |
    | **`max`** | `135.84 ms` |

- **Evidence:**
  - `spikes/09-atlas/report.json` (`atlas_m0.latency_384d`).
- **Changes:**
  - **Architecture Q7 (p95 latency budget):** Filtered vector search over 20k documents on Atlas M0 takes only **`~61 ms` at p50 and `~121 ms` at p95** (including network round-trip to Atlas). This uses just **1.2%** of the tentative `< 10,000 ms` p95 end-to-end budget (`docs/product.md` §6), confirming that MongoDB Atlas M0 is **not** a latency bottleneck and leaving `~9.8 s` of budget for query embedding (`feat-010`) and the two online LLM calls (`feat-011`).
