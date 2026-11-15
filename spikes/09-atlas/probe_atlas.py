"""Throwaway spike script for feat-009: Atlas free tier, vector search pre-filters, and atlas-local.

Answers Q1-Q5 in docs/spikes/09-atlas-vector-search.md with empirical measurements.
Run against Atlas M0 (reads MONGODB_URI from .env):
    uv run --with "pymongo>=4.11" python spikes/09-atlas/probe_atlas.py --target atlas

Run against local mongodb/mongodb-atlas-local Docker container:
    uv run --with "pymongo>=4.11" python spikes/09-atlas/probe_atlas.py --target local
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
import random
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import bson
import pymongo
from bson.binary import Binary, BinaryVectorDtype
from pymongo import AsyncMongoClient
from pymongo.operations import SearchIndexModel

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = REPO_ROOT / "spikes" / "09-atlas" / "report.json"

SPIKE_DB_NAME = "watch_tonight_spike_09"
SPIKE_COLL_NAME = "movies_synthetic"
VECTOR_INDEX_NAME = "movies_vector_idx"

PROVIDERS = [
    "ES:8",
    "ES:119",
    "ES:337",
    "ES:1899",
    "ES:63",
    "ES:149",
    "US:8",
    "US:9",
    "US:337",
    "US:1899",
    "US:15",
    "US:386",
    "BO:8",
    "BO:119",
    "BO:337",
    "BO:1899",
]
GENRES = ["Action", "Comedy", "Drama", "Horror", "Romance", "Science Fiction", "Thriller"]
TONES = ["dark", "warm", "tense", "playful", "melancholic", "uplifting", "wry", "dreamy"]
PACINGS = ["slow", "measured", "fast", "relentless"]
THEMES = ["identity", "grief", "friendship", "rebellion", "survival", "family", "obsession"]
CONTENT_WARNINGS = [
    "violence",
    "gore",
    "sexual_violence",
    "self_harm",
    "animal_harm",
    "substance_abuse",
    "flashing_lights",
    "child_peril",
]


def load_dotenv_var(key: str) -> str | None:
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return None
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None


def random_unit_vector(rng: random.Random, dims: int) -> list[float]:
    vec = [rng.gauss(0.0, 1.0) for _ in range(dims)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def build_synthetic_movie(doc_id: int, rng: random.Random, dims: int) -> dict[str, Any]:
    streamable_count = rng.randint(1, 5)
    warnings_count = rng.choices([0, 1, 2, 3], weights=[40, 35, 20, 5], k=1)[0]
    return {
        "_id": doc_id,
        "title": f"Synthetic Movie #{doc_id}: The Long Winding Road Ahead",
        "year": rng.randint(1960, 2026),
        "runtime": rng.randint(75, 195),
        "genres": rng.sample(GENRES, k=rng.randint(1, 3)),
        "keywords": [
            "atmospheric",
            "character study",
            "slow burn",
            "neo-noir",
            f"kw_{doc_id % 200}",
        ],
        "overview": (
            "A grounded synthetic overview matching the typical 320-character length of a TMDB "
            "movie synopsis so BSON storage and WiredTiger compression reflect production data "
            f"accurately for document {doc_id}. Everything here is deterministic synthetic text."
        ),
        "credits": {
            "directors": [f"Director {doc_id % 500}"],
            "cast": [
                f"Actor A{doc_id % 1000}",
                f"Actor B{doc_id % 1000}",
                f"Actor C{doc_id % 1000}",
                f"Actor D{doc_id % 1000}",
                f"Actor E{doc_id % 1000}",
            ],
        },
        "poster_path": f"/synthetic_poster_{doc_id:06d}.jpg",
        "streamable": rng.sample(PROVIDERS, k=streamable_count),
        "availability_updated_at": "2026-11-14T03:00:00Z",
        "profile": {
            "tone": rng.sample(TONES, k=2),
            "pacing": rng.choice(PACINGS),
            "intensity": rng.randint(1, 5),
            "themes": rng.sample(THEMES, k=3),
            "content_warnings": rng.sample(CONTENT_WARNINGS, k=warnings_count),
            "summary": (
                "An atmospheric, character-driven drama with measured pacing and quiet tension, "
                "exploring themes of identity and survival without relying on cheap shocks."
            ),
            "evidence": ["overview", "keywords", "genres"],
            "model": "gemini-2.5-flash",
            "prompt_version": "p1",
        },
        "embedding": random_unit_vector(rng, dims),
        "embedding_model": f"synthetic-{dims}d",
        "source_hash": f"sha256:{doc_id:064x}",
        "updated_at": "2026-11-14T03:00:00Z",
    }


def measure_bson_document_sizes() -> dict[str, Any]:
    rng = random.Random(42)
    out: dict[str, Any] = {}
    for dims in (384, 768, 1024):
        sample_docs = [build_synthetic_movie(i, rng, dims) for i in range(1, 51)]
        sizes = [len(bson.encode(d)) for d in sample_docs]
        avg_bytes = statistics.mean(sizes)
        vec_only_bytes = len(bson.encode({"embedding": sample_docs[0]["embedding"]}))
        bin_vec = Binary.from_vector(sample_docs[0]["embedding"], BinaryVectorDtype.FLOAT32)
        bin_vec_bytes = len(bson.encode({"embedding": bin_vec}))
        metadata_only_bytes = round(avg_bytes - vec_only_bytes, 1)
        avg_bin_doc_bytes = round(metadata_only_bytes + bin_vec_bytes, 1)
        # Estimate HNSW vector index overhead (~4B per float32 + HNSW graph links ~160B/doc)
        est_vector_idx_bytes_per_doc = dims * 4 + 160
        est_20k_bson_mb = round((avg_bytes * 20_000) / (1024 * 1024), 2)
        est_20k_bin_bson_mb = round((avg_bin_doc_bytes * 20_000) / (1024 * 1024), 2)
        est_20k_vector_idx_mb = round((est_vector_idx_bytes_per_doc * 20_000) / (1024 * 1024), 2)
        out[f"{dims}d"] = {
            "avg_bson_bytes_per_doc_float64_array": round(avg_bytes, 1),
            "avg_bson_bytes_per_doc_float32_binary": avg_bin_doc_bytes,
            "metadata_bson_bytes": metadata_only_bytes,
            "vector_float64_array_bson_bytes": vec_only_bytes,
            "vector_float32_binary_bson_bytes": bin_vec_bytes,
            "est_20k_uncompressed_bson_mb_float64_array": est_20k_bson_mb,
            "est_20k_uncompressed_bson_mb_float32_binary": est_20k_bin_bson_mb,
            "est_20k_hnsw_index_mb": est_20k_vector_idx_mb,
            "est_20k_total_uncompressed_mb_float64_array": round(
                est_20k_bson_mb + est_20k_vector_idx_mb, 2
            ),
            "est_20k_total_uncompressed_mb_float32_binary": round(
                est_20k_bin_bson_mb + est_20k_vector_idx_mb, 2
            ),
            "pct_of_512mb_m0_limit_uncompressed_float64_array": round(
                ((est_20k_bson_mb + est_20k_vector_idx_mb) / 512.0) * 100, 1
            ),
            "pct_of_512mb_m0_limit_uncompressed_float32_binary": round(
                ((est_20k_bin_bson_mb + est_20k_vector_idx_mb) / 512.0) * 100, 1
            ),
        }
    return out


def vector_index_definition(dims: int) -> dict[str, Any]:
    return {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": dims,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "streamable"},
            {"type": "filter", "path": "runtime"},
            {"type": "filter", "path": "_id"},
            {"type": "filter", "path": "profile.intensity"},
            {"type": "filter", "path": "profile.content_warnings"},
        ]
    }


async def wait_for_search_index_ready(
    collection: Any, index_name: str, timeout_s: float = 240.0
) -> dict[str, Any]:
    t0 = time.perf_counter()
    last_status = "UNKNOWN"
    statuses_seen: list[str] = []
    while (time.perf_counter() - t0) < timeout_s:
        cursor = await collection.list_search_indexes(name=index_name)
        indexes = await cursor.to_list(length=10)
        if indexes:
            idx = indexes[0]
            status = idx.get("status", "UNKNOWN")
            queryable = bool(idx.get("queryable", False))
            if status != last_status:
                elapsed_s = round(time.perf_counter() - t0, 2)
                statuses_seen.append(f"{status}@{elapsed_s}s")
                print(
                    f"  -> Index '{index_name}' status={status} "
                    f"queryable={queryable} ({elapsed_s}s)"
                )
                last_status = status
            if queryable and status == "READY":
                return {
                    "ready": True,
                    "elapsed_seconds": round(time.perf_counter() - t0, 2),
                    "statuses_seen": statuses_seen,
                    "index_meta": {
                        "id": idx.get("id"),
                        "name": idx.get("name"),
                        "type": idx.get("type"),
                        "status": status,
                        "queryable": queryable,
                    },
                }
        await asyncio.sleep(1.5)
    return {
        "ready": False,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "statuses_seen": statuses_seen,
    }


async def wait_for_local_cluster_ready(client: AsyncMongoClient[dict[str, Any]]) -> float:
    """Wait for mongod and mongot (search coordinator) to accept commands after container boot."""
    t0 = time.perf_counter()
    while (time.perf_counter() - t0) < 90.0:
        try:
            hello = await client.admin.command("hello")
            if hello.get("isWritablePrimary") or hello.get("ismaster"):
                # Also verify mongot is reachable by listing search indexes on a dummy collection
                test_coll = client[SPIKE_DB_NAME]["_warmup_check"]
                await test_coll.insert_one({"_id": 1})
                cursor = await test_coll.list_search_indexes()
                await cursor.to_list(length=5)
                await test_coll.drop()
                return round(time.perf_counter() - t0, 2)
        except Exception:
            await asyncio.sleep(1.5)
    raise RuntimeError("Timed out waiting for local mongod + mongot to become ready")


async def measure_small_fixture_index_ready(db: Any, dims: int = 384) -> dict[str, Any]:
    """Measure index creation -> READY time on a 50-doc integration-test-sized fixture."""
    coll = db["movies_fixture_50"]
    await coll.drop()
    rng = random.Random(77)
    docs = [build_synthetic_movie(i, rng, dims) for i in range(1, 51)]
    await coll.insert_many(docs)
    model = SearchIndexModel(
        definition=vector_index_definition(dims),
        name=VECTOR_INDEX_NAME,
        type="vectorSearch",
    )
    created_name = await coll.create_search_index(model=model)
    wait_res = await wait_for_search_index_ready(coll, created_name)
    with contextlib.suppress(Exception):
        await coll.drop_search_index(VECTOR_INDEX_NAME)
    await coll.drop()
    return {"doc_count": 50, "dims": dims, **wait_res}


async def insert_corpus(
    collection: Any, count: int, dims: int, batch_size: int = 2000
) -> dict[str, Any]:
    await collection.delete_many({})
    rng = random.Random(100 + dims)
    t0 = time.perf_counter()
    inserted = 0
    for start in range(1, count + 1, batch_size):
        end = min(start + batch_size, count + 1)
        batch = [build_synthetic_movie(doc_id, rng, dims) for doc_id in range(start, end)]
        await collection.insert_many(batch, ordered=False)
        inserted += len(batch)
    elapsed = round(time.perf_counter() - t0, 2)
    return {"doc_count": inserted, "dims": dims, "insert_seconds": elapsed}


async def collect_storage_stats(db: Any, coll_name: str) -> dict[str, Any]:
    stats = await db.command("collStats", coll_name)
    count = stats.get("count", 0)
    size_bytes = stats.get("size", 0)
    storage_bytes = stats.get("storageSize", 0)
    total_index_bytes = stats.get("totalIndexSize", 0)
    total_bytes = stats.get("totalSize", storage_bytes + total_index_bytes)
    return {
        "count": count,
        "avg_obj_size_bytes": stats.get("avgObjSize", 0),
        "uncompressed_bson_mb": round(size_bytes / (1024 * 1024), 2),
        "wiredtiger_storage_mb": round(storage_bytes / (1024 * 1024), 2),
        "btree_index_mb": round(total_index_bytes / (1024 * 1024), 2),
        "total_collection_disk_mb": round(total_bytes / (1024 * 1024), 2),
        "pct_of_512mb_m0_limit_disk": round((total_bytes / (512 * 1024 * 1024)) * 100, 2),
        "pct_of_512mb_m0_limit_logical": round((size_bytes / (512 * 1024 * 1024)) * 100, 2),
    }


async def run_prefilter_verification(collection: Any, dims: int) -> dict[str, Any]:
    rng = random.Random(999)
    query_vec = random_unit_vector(rng, dims)
    allowed_streamable = ["ES:8", "ES:337", "ES:119"]
    max_runtime = 120
    max_intensity = 3
    avoid_warnings = ["sexual_violence", "animal_harm", "self_harm"]

    # Pick 50 IDs that would otherwise match and exclude them
    matching_cursor = collection.find(
        {
            "streamable": {"$in": allowed_streamable},
            "runtime": {"$lte": max_runtime},
            "profile.intensity": {"$lte": max_intensity},
            "profile.content_warnings": {"$nin": avoid_warnings},
        },
        {"_id": 1},
    ).limit(50)
    matching_docs = await matching_cursor.to_list(length=50)
    exclude_ids = [d["_id"] for d in matching_docs]

    combined_filter = {
        "$and": [
            {"streamable": {"$in": allowed_streamable}},
            {"runtime": {"$lte": max_runtime}},
            {"_id": {"$nin": exclude_ids}},
            {"profile.intensity": {"$lte": max_intensity}},
            {"profile.content_warnings": {"$nin": avoid_warnings}},
        ]
    }

    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_vec,
                "numCandidates": 400,
                "limit": 40,
                "filter": combined_filter,
            }
        },
        {
            "$project": {
                "_id": 1,
                "title": 1,
                "runtime": 1,
                "streamable": 1,
                "profile.intensity": 1,
                "profile.content_warnings": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    # Wait briefly if the index just became READY and needs a moment to serve the first results
    results: list[dict[str, Any]] = []
    for _ in range(15):
        cursor = await collection.aggregate(pipeline)
        results = await cursor.to_list(length=40)
        if results:
            break
        await asyncio.sleep(2.0)

    violations: list[str] = []
    empty_warnings_docs = 0
    non_empty_disjoint_warnings_docs = 0
    for doc in results:
        if not (set(doc["streamable"]) & set(allowed_streamable)):
            violations.append(f"Doc {doc['_id']} failed streamable $in")
        if doc["runtime"] > max_runtime:
            violations.append(f"Doc {doc['_id']} failed runtime <= {max_runtime}")
        if doc["_id"] in exclude_ids:
            violations.append(f"Doc {doc['_id']} failed _id $nin")
        if doc["profile"]["intensity"] > max_intensity:
            violations.append(f"Doc {doc['_id']} failed intensity <= {max_intensity}")
        doc_warnings = doc["profile"]["content_warnings"]
        if set(doc_warnings) & set(avoid_warnings):
            violations.append(f"Doc {doc['_id']} failed content_warnings $nin")
        if len(doc_warnings) == 0:
            empty_warnings_docs += 1
        else:
            non_empty_disjoint_warnings_docs += 1

    # Also test what happens when filtering on an UNINDEXED field (`year`)
    unindexed_field_error: str | None = None
    try:
        bad_cursor = await collection.aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": VECTOR_INDEX_NAME,
                        "path": "embedding",
                        "queryVector": query_vec,
                        "numCandidates": 50,
                        "limit": 5,
                        "filter": {"year": {"$gte": 2000}},
                    }
                }
            ]
        )
        await bad_cursor.to_list(length=5)
    except Exception as exc:
        unindexed_field_error = f"{type(exc).__name__}: {exc}"

    # Probe list-size limits on _id.$nin
    nin_size_probes: dict[str, Any] = {}
    for list_size in (50, 100, 250, 500, 1000, 2000, 5000):
        big_exclude = list(range(1, list_size + 1))
        probe_pipeline = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_vec,
                    "numCandidates": 200,
                    "limit": 20,
                    "filter": {
                        "$and": [
                            {"streamable": {"$in": allowed_streamable}},
                            {"_id": {"$nin": big_exclude}},
                        ]
                    },
                }
            },
            {"$project": {"_id": 1}},
        ]
        t0 = time.perf_counter()
        try:
            c = await collection.aggregate(probe_pipeline)
            r = await c.to_list(length=20)
            leaked = [d["_id"] for d in r if d["_id"] in set(big_exclude)]
            nin_size_probes[str(list_size)] = {
                "ok": len(leaked) == 0 and len(r) == 20,
                "returned": len(r),
                "leaked": len(leaked),
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
        except Exception as exc:
            nin_size_probes[str(list_size)] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "combined_filter": {
            "streamable_in": allowed_streamable,
            "runtime_lte": max_runtime,
            "exclude_ids_count": len(exclude_ids),
            "intensity_lte": max_intensity,
            "content_warnings_nin": avoid_warnings,
        },
        "returned_count": len(results),
        "violations_count": len(violations),
        "empty_warnings_docs_returned": empty_warnings_docs,
        "non_empty_disjoint_warnings_docs_returned": non_empty_disjoint_warnings_docs,
        "all_constraints_satisfied": len(results) == 40 and len(violations) == 0,
        "unindexed_field_filter_error": unindexed_field_error,
        "sample_top_3": results[:3],
        "exclude_ids_list_size_probes": nin_size_probes,
    }


async def benchmark_latency(collection: Any, dims: int, runs: int = 50) -> dict[str, Any]:
    rng = random.Random(2026)
    latencies_ms: list[float] = []
    provider_choices = [
        ["ES:8", "ES:119", "ES:337"],
        ["US:8", "US:9", "US:337"],
        ["BO:8", "BO:337"],
    ]

    # 5 warmup queries
    for i in range(5 + runs):
        q_vec = random_unit_vector(rng, dims)
        provs = provider_choices[i % len(provider_choices)]
        excl = rng.sample(range(1, 20_000), k=50)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": q_vec,
                    "numCandidates": 400,
                    "limit": 40,
                    "filter": {
                        "$and": [
                            {"streamable": {"$in": provs}},
                            {"runtime": {"$lte": 135}},
                            {"_id": {"$nin": excl}},
                            {"profile.intensity": {"$lte": 4}},
                            {
                                "profile.content_warnings": {
                                    "$nin": ["sexual_violence", "animal_harm"]
                                }
                            },
                        ]
                    },
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "runtime": 1,
                    "streamable": 1,
                    "profile": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        t0 = time.perf_counter()
        cursor = await collection.aggregate(pipeline)
        docs = await cursor.to_list(length=40)
        dt_ms = (time.perf_counter() - t0) * 1000
        if i >= 5 and docs:
            latencies_ms.append(dt_ms)

    latencies_ms.sort()
    n = len(latencies_ms)
    p50 = latencies_ms[int(0.50 * (n - 1))] if n else 0.0
    p90 = latencies_ms[int(0.90 * (n - 1))] if n else 0.0
    p95 = latencies_ms[int(0.95 * (n - 1))] if n else 0.0
    return {
        "runs": n,
        "numCandidates": 400,
        "limit": 40,
        "min_ms": round(min(latencies_ms), 2) if n else 0.0,
        "p50_ms": round(p50, 2),
        "mean_ms": round(statistics.mean(latencies_ms), 2) if n else 0.0,
        "p90_ms": round(p90, 2),
        "p95_ms": round(p95, 2),
        "max_ms": round(max(latencies_ms), 2) if n else 0.0,
    }


async def probe_target(
    uri: str,
    target_name: str,
    corpus_size: int,
    measure_768d: bool,
    keep_data: bool,
) -> dict[str, Any]:
    parsed = urlsplit(uri)
    safe_host = parsed.hostname or "localhost"
    client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
        uri, compressors="zlib", serverSelectionTimeoutMS=15000
    )
    try:
        warmup_wait_s: float | None = None
        if target_name.startswith("local_"):
            print(f"[{target_name}] Waiting for local mongod + mongot to accept search commands...")
            warmup_wait_s = await wait_for_local_cluster_ready(client)
            print(f"[{target_name}] Local mongod + mongot ready in {warmup_wait_s}s")

        build_info = await client.admin.command("buildInfo")
        db = client[SPIKE_DB_NAME]
        coll = db[SPIKE_COLL_NAME]

        fixture_50_index: dict[str, Any] | None = None
        if target_name.startswith("local_"):
            print(f"[{target_name}] Measuring 50-doc fixture index ready time (384d)...")
            fixture_50_index = await measure_small_fixture_index_ready(db, dims=384)
            print(f"[{target_name}] 50-doc fixture index ready: {fixture_50_index}")

        # Drop any leftover search indexes first
        with contextlib.suppress(Exception):
            existing_cursor = await coll.list_search_indexes()
            for idx in await existing_cursor.to_list(length=20):
                await coll.drop_search_index(idx["name"])
                await asyncio.sleep(2.0)

        # 1. Insert 20k documents at 384d
        print(f"[{target_name}] Inserting {corpus_size} docs at 384d into {safe_host}...")
        insert_384 = await insert_corpus(coll, corpus_size, dims=384)
        stats_384 = await collect_storage_stats(db, SPIKE_COLL_NAME)
        print(f"[{target_name}] 384d stats: {stats_384}")

        # 2. Create vector search index programmatically via SearchIndexModel
        print(f"[{target_name}] Creating vector search index '{VECTOR_INDEX_NAME}' (384d)...")
        model_384 = SearchIndexModel(
            definition=vector_index_definition(384),
            name=VECTOR_INDEX_NAME,
            type="vectorSearch",
        )
        created_name = await coll.create_search_index(model=model_384)
        index_wait_384 = await wait_for_search_index_ready(coll, created_name)
        print(f"[{target_name}] Index ready: {index_wait_384}")

        # 3. Verify combined pre-filters & list-size limits
        print(f"[{target_name}] Running combined pre-filter verification...")
        prefilter_res = await run_prefilter_verification(coll, dims=384)
        print(
            f"[{target_name}] Pre-filter satisfied={prefilter_res['all_constraints_satisfied']} "
            f"(returned={prefilter_res['returned_count']}, "
            f"violations={prefilter_res['violations_count']})"
        )

        # 4. Benchmark latency (50 queries after 5 warmup queries)
        print(f"[{target_name}] Benchmarking filtered $vectorSearch latency (50 queries)...")
        latency_384 = await benchmark_latency(coll, dims=384, runs=50)
        print(
            f"[{target_name}] Latency (384d): "
            f"p50={latency_384['p50_ms']}ms, p95={latency_384['p95_ms']}ms"
        )

        # 5. Test programmatic update_search_index and 768d storage measurement
        stats_768: dict[str, Any] | None = None
        insert_768: dict[str, Any] | None = None
        update_index_ok = False
        if measure_768d:
            print(f"[{target_name}] Measuring {corpus_size} docs at 768d...")
            insert_768 = await insert_corpus(coll, corpus_size, dims=768)
            stats_768 = await collect_storage_stats(db, SPIKE_COLL_NAME)
            print(f"[{target_name}] 768d stats: {stats_768}")
            await coll.update_search_index(VECTOR_INDEX_NAME, vector_index_definition(768))
            update_index_ok = True

        # Clean up temporary spike database unless --keep is passed
        cleaned_up = False
        if not keep_data:
            print(f"[{target_name}] Cleaning up temporary database '{SPIKE_DB_NAME}'...")
            with contextlib.suppress(Exception):
                await coll.drop_search_index(VECTOR_INDEX_NAME)
            await client.drop_database(SPIKE_DB_NAME)
            cleaned_up = True

        return {
            "target": target_name,
            "host_redacted": safe_host,
            "mongodb_version": build_info.get("version"),
            "pymongo_version": pymongo.__version__,
            "async_client_class": f"{AsyncMongoClient.__module__}.{AsyncMongoClient.__name__}",
            "corpus_384d": {
                "insert": insert_384,
                "coll_stats": stats_384,
            },
            "corpus_768d": {
                "insert": insert_768,
                "coll_stats": stats_768,
            }
            if measure_768d
            else None,
            "search_index_lifecycle": {
                "created_via": (
                    "collection.create_search_index(SearchIndexModel(..., type='vectorSearch'))"
                ),
                "updated_via_code": update_index_ok,
                "local_warmup_wait_s": warmup_wait_s,
                "fixture_50_docs_build_384d": fixture_50_index,
                "initial_build_384d": index_wait_384,
            },
            "prefilter_verification": prefilter_res,
            "latency_384d": latency_384,
            "cleaned_up": cleaned_up,
        }
    finally:
        await client.close()


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Probe MongoDB Atlas / atlas-local for feat-009.")
    parser.add_argument(
        "--target",
        choices=["atlas", "local"],
        default="atlas",
        help="Target to probe (atlas reads MONGODB_URI from .env; local uses localhost:27017).",
    )
    parser.add_argument(
        "--local-uri",
        default="mongodb://localhost:27017/?directConnection=true",
        help="Connection URI when --target=local.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=20_000,
        help="Number of synthetic movie documents to insert (default: 20000).",
    )
    parser.add_argument(
        "--skip-768d",
        action="store_true",
        help="Skip the second 20k load at 768 dimensions.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the temporary spike database instead of dropping it at the end.",
    )
    parser.add_argument(
        "--bson-only",
        action="store_true",
        help="Only refresh the local BSON size models in report.json offline.",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {}
    if DEFAULT_REPORT_PATH.is_file():
        try:
            report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        except Exception:
            report = {}

    report["generated_at"] = datetime.now(UTC).isoformat()
    report["bson_size_models"] = measure_bson_document_sizes()

    if args.bson_only:
        DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Updated bson_size_models in {DEFAULT_REPORT_PATH}")
        return

    if args.target == "atlas":
        uri = load_dotenv_var("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI not found in .env")
        report["atlas_m0"] = await probe_target(
            uri=uri,
            target_name="atlas_m0",
            corpus_size=args.count,
            measure_768d=not args.skip_768d,
            keep_data=args.keep,
        )
    else:
        import platform

        platform_key = f"local_{platform.system().lower()}_{platform.machine().lower()}"
        report[platform_key] = await probe_target(
            uri=args.local_uri,
            target_name=platform_key,
            corpus_size=args.count,
            measure_768d=False,
            keep_data=args.keep,
        )

    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved report to {DEFAULT_REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(async_main())
