"""Throwaway spike script for feat-010: query-time embedding runtime.

Answers Q1-Q6 in docs/spikes/10-embedding-runtime.md:
- Q1: Quality of BAAI/bge-small-en-v1.5 (384-d) on ~200 real TMDB movies across 10 mood queries.
- Q2: Runtime options:
      (a) sentence-transformers (PyTorch CPU)
      (b) fastembed (ONNX Runtime CPU)
      (c) Hosted Gemini Embedding API (gemini-embedding-001, MRL 384-d) & Atlas autoEmbed
      measuring disk footprint (site-packages + model weights), RAM (RSS at import, load, peak),
      cold start (model init from disk cache), single-query latency (p50/p95), and cosine parity.
- Q3: Free hosting tiers (Cloud Run, Azure Container Apps, Render, Fly.io) vs runtime footprints.
- Q4: Batch cost on laptop CPU for 20,000 profiles.
- Q5: Model migration strategy with embedding_model per document.
- Q6: Small multilingual models (paraphrase-multilingual-MiniLM-L12-v2 & multilingual-e5-small)
      on English + non-English raw queries (ES, FR, PT) vs bge-small-en-v1.5.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SPIKE_DIR.parents[1]
SAMPLE_MOVIES_PATH = SPIKE_DIR / "sample_movies_200.json"
REPORT_PATH = SPIKE_DIR / "report.json"
SNAPSHOT_1_PATH = REPO_ROOT / "spikes" / "08-tmdb" / "snapshot_1.json"

ENGLISH_MOOD_QUERIES: list[dict[str, str]] = [
    {
        "id": "Q01_cozy_animation",
        "label": "Cozy / Warm Family Animation",
        "query": (
            "warm, comforting animated family adventure with heart, humor, "
            "and low stress after a long week"
        ),
    },
    {
        "id": "Q02_cerebral_scifi",
        "label": "Cerebral Space / Time Sci-Fi",
        "query": (
            "mind-bending sci-fi mystery about space exploration, time dilation, "
            "and existential survival"
        ),
    },
    {
        "id": "Q03_gritty_crime",
        "label": "Gritty Mafia / Crime Thriller",
        "query": (
            "dark, tense crime drama about mafia loyalty, organized crime corruption, "
            "and moral decay"
        ),
    },
    {
        "id": "Q04_atmospheric_horror",
        "label": "Atmospheric / Supernatural Horror",
        "query": (
            "scary supernatural horror or monster thriller with unsettling dread, "
            "claustrophobia, and survival terror"
        ),
    },
    {
        "id": "Q05_high_octane_action",
        "label": "Relentless Revenge / Martial Arts Action",
        "query": (
            "relentless high-adrenaline action thriller with martial arts, gunplay, "
            "or a one-man-army revenge mission"
        ),
    },
    {
        "id": "Q06_romantic_drama",
        "label": "Bittersweet Romantic Drama",
        "query": (
            "intimate, emotional romantic drama about love, longing, heartbreak, "
            "and unforgettable chemistry"
        ),
    },
    {
        "id": "Q07_epic_fantasy",
        "label": "Epic Mythological / Medieval Fantasy",
        "query": (
            "epic mythological fantasy quest with ancient magic, fellowship, "
            "and massive battles between good and evil"
        ),
    },
    {
        "id": "Q08_dark_satire",
        "label": "Sharp Dark Comedy / Social Satire",
        "query": (
            "sharp, chaotic dark comedy or social satire about wealth, greed, "
            "absurdity, and things spiralling out of control"
        ),
    },
    {
        "id": "Q09_psych_suspense",
        "label": "Twisty Psychological Suspense",
        "query": (
            "twisty psychological thriller with paranoia, hidden identities, "
            "mind games, and a dark obsession"
        ),
    },
    {
        "id": "Q10_feelgood_comedy",
        "label": "Lighthearted Feel-Good / Nostalgic Adventure",
        "query": (
            "fun, lighthearted laugh-out-loud comedy or nostalgic adventure "
            "that doesn't take itself seriously"
        ),
    },
]

MULTILINGUAL_RAW_QUERIES: list[dict[str, str]] = [
    {
        "id": "ML01_es_scifi",
        "lang": "es",
        "paired_en_id": "Q02_cerebral_scifi",
        "query": (
            "una película de ciencia ficción espacial que te vuele la cabeza "
            "sobre viajes en el tiempo, agujeros negros y supervivencia"
        ),
    },
    {
        "id": "ML02_es_cozy",
        "lang": "es",
        "paired_en_id": "Q01_cozy_animation",
        "query": (
            "algo cálido, tierno y divertido de animación familiar con humor "
            "para relajarse sin nada de estrés"
        ),
    },
    {
        "id": "ML03_fr_crime",
        "lang": "fr",
        "paired_en_id": "Q03_gritty_crime",
        "query": (
            "un drame criminel sombre et tendu sur la mafia, la loyauté, "
            "le crime organisé et la corruption morale"
        ),
    },
    {
        "id": "ML04_pt_fantasy",
        "lang": "pt",
        "paired_en_id": "Q07_epic_fantasy",
        "query": (
            "uma aventura épica de fantasia medieval com magia antiga, "
            "irmandade e grandes batalhas entre o bem e o mal"
        ),
    },
]


def load_dotenv_file() -> dict[str, str]:
    env_path = REPO_ROOT / ".env"
    env_vars: dict[str, str] = {}
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'").strip('"')
    return env_vars


def percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = (len(sorted_vals) - 1) * pct
    low = math.floor(idx)
    high = math.ceil(idx)
    if low == high:
        return round(sorted_vals[low], 2)
    weight = idx - low
    return round(sorted_vals[low] * (1.0 - weight) + sorted_vals[high] * weight, 2)


def dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    seen_inodes: set[tuple[int, int]] = set()
    for root, _dirs, files in os.walk(path, followlinks=True):
        for fname in files:
            fpath = Path(root) / fname
            try:
                st = fpath.stat()
                inode_key = (st.st_dev, st.st_ino)
                if inode_key not in seen_inodes:
                    seen_inodes.add(inode_key)
                    total += st.st_size
            except OSError:
                pass
    return round(total / (1024 * 1024), 2)


def measure_archive_site_packages_mb() -> float:
    archive_dirs = [Path(p) for p in sys.path if "archive-v0" in p and "site-packages" in p]
    return round(sum(dir_size_mb(d) for d in archive_dirs), 2)


def cosine_sim(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_movies(
    query_vec: list[float],
    movie_vecs: list[list[float]],
    movies: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for vec, movie in zip(movie_vecs, movies, strict=True):
        sim = cosine_sim(query_vec, vec)
        scored.append((sim, movie))
    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for sim, movie in scored[:top_k]:
        results.append(
            {
                "tmdb_id": movie["tmdb_id"],
                "title": movie["title"],
                "year": movie["year"],
                "genres": movie["genres"],
                "score": round(sim, 4),
            }
        )
    return results


def fetch_200_tmdb_movies(api_key: str) -> list[dict[str, Any]]:
    if SAMPLE_MOVIES_PATH.exists():
        cached = json.loads(SAMPLE_MOVIES_PATH.read_text(encoding="utf-8"))
        if isinstance(cached, list) and len(cached) >= 200:
            print(f"[dataset] Loaded {len(cached)} cached movies from {SAMPLE_MOVIES_PATH.name}")
            return cached[:200]

    snap = json.loads(SNAPSHOT_1_PATH.read_text(encoding="utf-8"))
    movie_ids: list[int] = [int(k) for k in snap["popular_500_streamable"]][:215]

    headers: dict[str, str] = {"Accept": "application/json"}
    params_base: dict[str, str] = {"language": "en-US", "append_to_response": "keywords"}
    if api_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        params_base["api_key"] = api_key

    query_str = urllib.parse.urlencode(params_base)

    def fetch_one(mid: int) -> dict[str, Any] | None:
        url = f"https://api.themoviedb.org/3/movie/{mid}?{query_str}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None
        overview = (data.get("overview") or "").strip()
        if not overview:
            return None
        title = data.get("title") or data.get("original_title") or f"Movie {mid}"
        rel = data.get("release_date") or ""
        year = int(rel[:4]) if len(rel) >= 4 and rel[:4].isdigit() else 0
        genres = [g["name"] for g in (data.get("genres") or []) if g.get("name")]
        tagline = (data.get("tagline") or "").strip()
        kw_obj = data.get("keywords") or {}
        kw_list = kw_obj.get("keywords") or []
        keywords = [k["name"] for k in kw_list if k.get("name")][:15]
        profile_text = (
            f"{title} ({year}). "
            f"Genres: {', '.join(genres)}. "
            f"Tagline: {tagline} "
            f"Overview: {overview} "
            f"Keywords: {', '.join(keywords)}."
        )
        return {
            "tmdb_id": mid,
            "title": title,
            "year": year,
            "genres": genres,
            "tagline": tagline,
            "overview": overview,
            "keywords": keywords,
            "profile_text": profile_text,
        }

    fetched: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        for item in pool.map(fetch_one, movie_ids):
            if item is not None:
                fetched.append(item)
            if len(fetched) == 200:
                break

    if len(fetched) < 200:
        raise RuntimeError(
            f"Only fetched {len(fetched)} movies from TMDB (need 200; check network)"
        )
    SAMPLE_MOVIES_PATH.write_text(json.dumps(fetched, indent=2), encoding="utf-8")
    print(f"[dataset] Fetched and cached {len(fetched)} movies to {SAMPLE_MOVIES_PATH.name}")
    return fetched


def get_rss_mb() -> float:
    import psutil

    proc = psutil.Process(os.getpid())
    return round(proc.memory_info().rss / (1024 * 1024), 2)


def run_worker_fastembed(model_name: str, is_e5: bool = False) -> dict[str, Any]:
    rss_before_import = get_rss_mb()
    t_import_0 = time.perf_counter()
    from fastembed import TextEmbedding

    import_time_s = round(time.perf_counter() - t_import_0, 3)
    rss_after_import = get_rss_mb()

    movies = json.loads(SAMPLE_MOVIES_PATH.read_text(encoding="utf-8"))
    doc_texts = [f"passage: {m['profile_text']}" if is_e5 else m["profile_text"] for m in movies]
    en_queries = [f"query: {q['query']}" if is_e5 else q["query"] for q in ENGLISH_MOOD_QUERIES]
    ml_queries = [f"query: {q['query']}" if is_e5 else q["query"] for q in MULTILINGUAL_RAW_QUERIES]

    cache_dir = SPIKE_DIR / ".model_cache" / "fastembed"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_slug = model_name.split("/")[-1]
    existing_dirs = [p for p in cache_dir.iterdir() if model_slug.lower() in p.name.lower()]
    if existing_dirs:
        os.environ["HF_HUB_OFFLINE"] = "1"
    else:
        _warmup_model = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir))
        _ = list(_warmup_model.embed([doc_texts[0]]))
        del _warmup_model

    t_load_0 = time.perf_counter()
    model = TextEmbedding(
        model_name=model_name,
        cache_dir=str(cache_dir),
        local_files_only=bool(existing_dirs),
    )
    # Trigger ONNX session load with 1 short text
    _ = list(model.embed(["warmup query"]))
    cold_start_s = round(time.perf_counter() - t_load_0, 3)
    rss_after_load = get_rss_mb()

    # Single-query latency across 50 warm iterations
    query_latencies_ms: list[float] = []
    for i in range(50):
        q_text = en_queries[i % len(en_queries)]
        t0 = time.perf_counter()
        _ = list(model.embed([q_text]))
        query_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    query_latencies_ms.sort()

    # Embed 200 movies (batch_size=64)
    t_batch200_0 = time.perf_counter()
    movie_vecs_np = list(model.embed(doc_texts, batch_size=64))
    batch_200_s = time.perf_counter() - t_batch200_0
    movie_vecs = [[float(x) for x in v] for v in movie_vecs_np]
    rss_peak_after_batch = get_rss_mb()

    # Also measure a 1,000-profile batch to get a rock-solid sustained CPU rate for 20k
    docs_1000 = doc_texts * 5
    t_batch1000_0 = time.perf_counter()
    _ = list(model.embed(docs_1000, batch_size=64))
    batch_1000_s = time.perf_counter() - t_batch1000_0
    docs_per_sec = round(1000.0 / batch_1000_s, 2)
    est_20k_seconds = round(20000.0 / docs_per_sec, 1)
    est_20k_minutes = round(est_20k_seconds / 60.0, 2)

    # Embed English and Multilingual queries
    en_q_vecs = [[float(x) for x in v] for v in model.embed(en_queries)]
    ml_q_vecs = [[float(x) for x in v] for v in model.embed(ml_queries)]

    en_results: dict[str, Any] = {}
    for q_meta, q_vec in zip(ENGLISH_MOOD_QUERIES, en_q_vecs, strict=True):
        en_results[q_meta["id"]] = {
            "label": q_meta["label"],
            "query": q_meta["query"],
            "top_5": rank_movies(q_vec, movie_vecs, movies, top_k=5),
        }

    ml_results: dict[str, Any] = {}
    for q_meta, q_vec in zip(MULTILINGUAL_RAW_QUERIES, ml_q_vecs, strict=True):
        top5 = rank_movies(q_vec, movie_vecs, movies, top_k=5)
        paired_en_top5 = en_results[q_meta["paired_en_id"]]["top_5"]
        en_ids = {item["tmdb_id"] for item in paired_en_top5}
        ml_ids = {item["tmdb_id"] for item in top5}
        overlap_at_5 = len(en_ids & ml_ids)
        ml_results[q_meta["id"]] = {
            "lang": q_meta["lang"],
            "paired_en_id": q_meta["paired_en_id"],
            "query": q_meta["query"],
            "overlap_at_5_with_en": overlap_at_5,
            "top_5": top5,
        }

    # Measure site-packages and model cache size
    site_packages_mb = measure_archive_site_packages_mb()
    model_dirs = [p for p in cache_dir.iterdir() if model_slug.lower() in p.name.lower()]
    model_disk_mb = (
        sum(dir_size_mb(p) for p in model_dirs) if model_dirs else dir_size_mb(cache_dir)
    )

    return {
        "runtime": "fastembed (ONNX Runtime CPU)",
        "model_name": model_name,
        "dimensions": len(movie_vecs[0]),
        "site_packages_mb": site_packages_mb,
        "model_weights_disk_mb": round(model_disk_mb, 2),
        "estimated_added_image_mb": round(site_packages_mb + model_disk_mb, 1),
        "rss_before_import_mb": rss_before_import,
        "rss_after_import_mb": rss_after_import,
        "rss_after_model_load_mb": rss_after_load,
        "rss_peak_batch_mb": max(rss_after_load, rss_peak_after_batch),
        "import_time_s": import_time_s,
        "cold_start_from_disk_s": cold_start_s,
        "single_query_latency_ms": {
            "p50": percentile(query_latencies_ms, 0.50),
            "p95": percentile(query_latencies_ms, 0.95),
            "mean": round(sum(query_latencies_ms) / len(query_latencies_ms), 2),
            "min": round(query_latencies_ms[0], 2),
            "max": round(query_latencies_ms[-1], 2),
        },
        "batch_200_movies_s": round(batch_200_s, 2),
        "batch_1000_movies_s": round(batch_1000_s, 2),
        "throughput_docs_per_sec": docs_per_sec,
        "estimated_20k_profiles_s": est_20k_seconds,
        "estimated_20k_profiles_min": est_20k_minutes,
        "english_queries": en_results,
        "multilingual_queries": ml_results,
        "sample_vectors_first_20": movie_vecs[:20]
        if model_name == "BAAI/bge-small-en-v1.5"
        else [],
    }


def run_worker_sentence_transformers(model_name: str) -> dict[str, Any]:
    rss_before_import = get_rss_mb()
    t_import_0 = time.perf_counter()
    import torch
    from sentence_transformers import SentenceTransformer

    # Force CPU to measure realistic container / laptop CPU behavior
    torch.set_num_threads(os.cpu_count() or 4)
    import_time_s = round(time.perf_counter() - t_import_0, 3)
    rss_after_import = get_rss_mb()

    movies = json.loads(SAMPLE_MOVIES_PATH.read_text(encoding="utf-8"))
    doc_texts = [m["profile_text"] for m in movies]
    en_queries = [q["query"] for q in ENGLISH_MOOD_QUERIES]

    cache_dir = SPIKE_DIR / ".model_cache" / "sentence_transformers"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_slug = model_name.split("/")[-1]
    existing_dirs = [p for p in cache_dir.iterdir() if model_slug.lower() in p.name.lower()]
    if existing_dirs:
        os.environ["HF_HUB_OFFLINE"] = "1"
    else:
        _warmup = SentenceTransformer(model_name, device="cpu", cache_folder=str(cache_dir))
        _ = _warmup.encode([doc_texts[0]], normalize_embeddings=True)
        del _warmup

    t_load_0 = time.perf_counter()
    model = SentenceTransformer(
        model_name,
        device="cpu",
        cache_folder=str(cache_dir),
        local_files_only=bool(existing_dirs),
    )
    _ = model.encode(["warmup query"], normalize_embeddings=True)
    cold_start_s = round(time.perf_counter() - t_load_0, 3)
    rss_after_load = get_rss_mb()

    query_latencies_ms: list[float] = []
    for i in range(50):
        q_text = en_queries[i % len(en_queries)]
        t0 = time.perf_counter()
        _ = model.encode([q_text], normalize_embeddings=True, show_progress_bar=False)
        query_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    query_latencies_ms.sort()

    t_batch200_0 = time.perf_counter()
    movie_vecs_np = model.encode(
        doc_texts,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    batch_200_s = time.perf_counter() - t_batch200_0
    movie_vecs = [[float(x) for x in v] for v in movie_vecs_np]
    rss_peak_after_batch = get_rss_mb()

    docs_1000 = doc_texts * 5
    t_batch1000_0 = time.perf_counter()
    _ = model.encode(
        docs_1000,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    batch_1000_s = time.perf_counter() - t_batch1000_0
    docs_per_sec = round(1000.0 / batch_1000_s, 2)
    est_20k_seconds = round(20000.0 / docs_per_sec, 1)
    est_20k_minutes = round(est_20k_seconds / 60.0, 2)

    en_q_vecs_np = model.encode(
        en_queries,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    en_q_vecs = [[float(x) for x in v] for v in en_q_vecs_np]

    en_results: dict[str, Any] = {}
    for q_meta, q_vec in zip(ENGLISH_MOOD_QUERIES, en_q_vecs, strict=True):
        en_results[q_meta["id"]] = {
            "label": q_meta["label"],
            "query": q_meta["query"],
            "top_5": rank_movies(q_vec, movie_vecs, movies, top_k=5),
        }

    site_packages_mb = measure_archive_site_packages_mb()
    model_dirs = [p for p in cache_dir.iterdir() if model_slug.lower() in p.name.lower()]
    model_disk_mb = (
        sum(dir_size_mb(p) for p in model_dirs) if model_dirs else dir_size_mb(cache_dir)
    )

    return {
        "runtime": "sentence-transformers (PyTorch CPU)",
        "model_name": model_name,
        "dimensions": len(movie_vecs[0]),
        "site_packages_mb": site_packages_mb,
        "model_weights_disk_mb": round(model_disk_mb, 2),
        "estimated_added_image_mb": round(site_packages_mb + model_disk_mb, 1),
        "rss_before_import_mb": rss_before_import,
        "rss_after_import_mb": rss_after_import,
        "rss_after_model_load_mb": rss_after_load,
        "rss_peak_batch_mb": max(rss_after_load, rss_peak_after_batch),
        "import_time_s": import_time_s,
        "cold_start_from_disk_s": cold_start_s,
        "single_query_latency_ms": {
            "p50": percentile(query_latencies_ms, 0.50),
            "p95": percentile(query_latencies_ms, 0.95),
            "mean": round(sum(query_latencies_ms) / len(query_latencies_ms), 2),
            "min": round(query_latencies_ms[0], 2),
            "max": round(query_latencies_ms[-1], 2),
        },
        "batch_200_movies_s": round(batch_200_s, 2),
        "batch_1000_movies_s": round(batch_1000_s, 2),
        "throughput_docs_per_sec": docs_per_sec,
        "estimated_20k_profiles_s": est_20k_seconds,
        "estimated_20k_profiles_min": est_20k_minutes,
        "english_queries": en_results,
        "sample_vectors_first_20": movie_vecs[:20],
    }


def run_worker_gemini_api(output_dim: int = 384) -> dict[str, Any]:
    env_vars = load_dotenv_file()
    api_key = os.environ.get("GEMINI_API_KEY") or env_vars.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in .env")

    movies = json.loads(SAMPLE_MOVIES_PATH.read_text(encoding="utf-8"))
    doc_texts = [m["profile_text"] for m in movies]
    en_queries = [q["query"] for q in ENGLISH_MOOD_QUERIES]
    ml_queries = [q["query"] for q in MULTILINGUAL_RAW_QUERIES]

    model_id = "models/gemini-embedding-001"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    def normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec

    def post_json(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{base_url}/{endpoint}?key={urllib.parse.quote(api_key)}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Warmup call
    t_cold_0 = time.perf_counter()
    _ = post_json(
        f"{model_id}:embedContent",
        {
            "model": model_id,
            "content": {"parts": [{"text": "warmup query"}]},
            "taskType": "RETRIEVAL_QUERY",
            "outputDimensionality": output_dim,
        },
    )
    cold_start_s = round(time.perf_counter() - t_cold_0, 3)

    # Batch embed 200 movies in 2 batches of 100
    movie_vecs: list[list[float]] = []
    t_batch200_0 = time.perf_counter()
    for start in range(0, len(doc_texts), 100):
        chunk = doc_texts[start : start + 100]
        reqs = [
            {
                "model": model_id,
                "content": {"parts": [{"text": text}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": output_dim,
            }
            for text in chunk
        ]
        data = post_json(f"{model_id}:batchEmbedContents", {"requests": reqs})
        for emb in data["embeddings"]:
            movie_vecs.append(normalize(emb["values"]))
    batch_200_s = round(time.perf_counter() - t_batch200_0, 2)

    # Single-query latency across 14 queries (10 EN + 4 ML)
    query_latencies_ms: list[float] = []
    en_q_vecs: list[list[float]] = []
    for q_text in en_queries:
        t0 = time.perf_counter()
        data = post_json(
            f"{model_id}:embedContent",
            {
                "model": model_id,
                "content": {"parts": [{"text": q_text}]},
                "taskType": "RETRIEVAL_QUERY",
                "outputDimensionality": output_dim,
            },
        )
        query_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        en_q_vecs.append(normalize(data["embedding"]["values"]))

    ml_q_vecs: list[list[float]] = []
    for q_text in ml_queries:
        t0 = time.perf_counter()
        data = post_json(
            f"{model_id}:embedContent",
            {
                "model": model_id,
                "content": {"parts": [{"text": q_text}]},
                "taskType": "RETRIEVAL_QUERY",
                "outputDimensionality": output_dim,
            },
        )
        query_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        ml_q_vecs.append(normalize(data["embedding"]["values"]))

    query_latencies_ms.sort()

    en_results: dict[str, Any] = {}
    for q_meta, q_vec in zip(ENGLISH_MOOD_QUERIES, en_q_vecs, strict=True):
        en_results[q_meta["id"]] = {
            "label": q_meta["label"],
            "query": q_meta["query"],
            "top_5": rank_movies(q_vec, movie_vecs, movies, top_k=5),
        }

    ml_results: dict[str, Any] = {}
    for q_meta, q_vec in zip(MULTILINGUAL_RAW_QUERIES, ml_q_vecs, strict=True):
        top5 = rank_movies(q_vec, movie_vecs, movies, top_k=5)
        paired_en_top5 = en_results[q_meta["paired_en_id"]]["top_5"]
        en_ids = {item["tmdb_id"] for item in paired_en_top5}
        ml_ids = {item["tmdb_id"] for item in top5}
        ml_results[q_meta["id"]] = {
            "lang": q_meta["lang"],
            "paired_en_id": q_meta["paired_en_id"],
            "query": q_meta["query"],
            "overlap_at_5_with_en": len(en_ids & ml_ids),
            "top_5": top5,
        }

    return {
        "runtime": "Hosted Gemini Embedding API (REST)",
        "model_name": f"gemini-embedding-001 (MRL {output_dim}-d)",
        "dimensions": output_dim,
        "site_packages_mb": 0.0,
        "model_weights_disk_mb": 0.0,
        "estimated_added_image_mb": 0.0,
        "added_rss_mb": 0.0,
        "cold_start_tls_handshake_s": cold_start_s,
        "single_query_latency_ms": {
            "p50": percentile(query_latencies_ms, 0.50),
            "p95": percentile(query_latencies_ms, 0.95),
            "mean": round(sum(query_latencies_ms) / len(query_latencies_ms), 2),
            "min": round(query_latencies_ms[0], 2),
            "max": round(query_latencies_ms[-1], 2),
        },
        "batch_200_movies_2_calls_s": batch_200_s,
        "free_tier_limits": {
            "rpm": 100,
            "tpm": 30000,
            "rpd": 1000,
            "paid_tier_usd_per_1m_tokens": 0.15,
        },
        "english_queries": en_results,
        "multilingual_queries": ml_results,
    }


def invoke_subprocess_worker(with_pkgs: list[str], worker_arg: str) -> dict[str, Any]:
    cmd = ["uv", "run", "--no-project", "--offline"]
    for pkg in with_pkgs:
        cmd.extend(["--with", pkg])
    cmd.extend(["python", str(Path(__file__).resolve()), "--worker", worker_arg])
    print(f"[orchestrator] Running worker '{worker_arg}' via: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Worker '{worker_arg}' failed (exit {proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def run_all() -> None:
    env_vars = load_dotenv_file()
    tmdb_key = os.environ.get("TMDB_API_KEY") or env_vars.get("TMDB_API_KEY", "")
    if not tmdb_key:
        raise RuntimeError("TMDB_API_KEY not found in .env")

    movies = fetch_200_tmdb_movies(tmdb_key)

    # 1. Run fastembed BAAI/bge-small-en-v1.5 (384-d)
    fe_bge = invoke_subprocess_worker(["fastembed", "psutil"], "fastembed-bge-small")

    # 2. Run sentence-transformers BAAI/bge-small-en-v1.5 (384-d)
    st_bge = invoke_subprocess_worker(["sentence-transformers", "psutil"], "st-bge-small")

    # Compare cosine similarity between fastembed (ONNX) and sentence-transformers (PyTorch)
    fe_vecs = fe_bge.pop("sample_vectors_first_20", [])
    st_vecs = st_bge.pop("sample_vectors_first_20", [])
    cos_sims = [cosine_sim(v1, v2) for v1, v2 in zip(fe_vecs, st_vecs, strict=True)]
    top5_overlaps: list[int] = []
    for q_meta in ENGLISH_MOOD_QUERIES:
        qid = q_meta["id"]
        fe_ids = {m["tmdb_id"] for m in fe_bge["english_queries"][qid]["top_5"]}
        st_ids = {m["tmdb_id"] for m in st_bge["english_queries"][qid]["top_5"]}
        top5_overlaps.append(len(fe_ids & st_ids))

    onnx_vs_pytorch_parity = {
        "cosine_similarity_first_20_movies": {
            "min": round(min(cos_sims), 6),
            "mean": round(sum(cos_sims) / len(cos_sims), 6),
            "max": round(max(cos_sims), 6),
        },
        "top_5_overlap_across_10_queries": {
            "mean_overlap_out_of_5": round(sum(top5_overlaps) / len(top5_overlaps), 2),
            "per_query_overlap": dict(
                zip([q["id"] for q in ENGLISH_MOOD_QUERIES], top5_overlaps, strict=True)
            ),
        },
    }

    # 3. Run multilingual small model via fastembed (ONNX)
    fe_minilm_ml = invoke_subprocess_worker(
        ["fastembed", "psutil"], "fastembed-multilingual-minilm"
    )
    fe_minilm_ml.pop("sample_vectors_first_20", None)

    # 4. Hosted Embedding Options (c): Gemini Embedding API & Atlas autoEmbed
    env_gemini_key = os.environ.get("GEMINI_API_KEY") or env_vars.get("GEMINI_API_KEY", "")
    if env_gemini_key:
        print("[orchestrator] Running worker 'gemini-api'...")
        hosted_res = run_worker_gemini_api(output_dim=384)
    else:
        print("[orchestrator] GEMINI_API_KEY is empty in .env; recording documented specs for (c).")
        hosted_res = {
            "gemini_embedding_001": {
                "runtime": "Hosted Gemini Embedding API (REST / google-genai)",
                "model_name": "gemini-embedding-001 (Matryoshka MRL 384-d / 768-d / 3072-d)",
                "dimensions_supported": [384, 768, 1536, 3072],
                "context_window_tokens": 2048,
                "added_container_image_mb": 0.0,
                "added_rss_mb": 0.0,
                "cold_start_s": 0.0,
                "documented_free_tier_limits": {
                    "rpm": 100,
                    "tpm": 30000,
                    "rpd": 1000,
                    "batch_20k_feasibility_on_free_tier": (
                        "1,000 RPD free limit means 20,000 profiles require either batching "
                        "(batchEmbedContents up to 100 texts/call, still subject to 30,000 TPM "
                        "~= 150 profiles/min -> ~133 min) or Paid Tier 1 ($0.15 / 1M tokens "
                        "~= $0.60 for 20k profiles at ~200 tokens/profile)."
                    ),
                },
                "paid_pricing_usd_per_1m_tokens": 0.15,
                "docs_url": "https://ai.google.dev/gemini-api/docs/embeddings",
                "pricing_url": "https://ai.google.dev/gemini-api/docs/pricing",
                "checked_date": "2026-11-15",
            },
            "atlas_automated_embedding": {
                "runtime": "MongoDB Atlas Automated Embedding (Voyage AI autoEmbed)",
                "models_supported": ["voyage-3", "voyage-3-lite", "voyage-3-large"],
                "m0_free_tier_supported": True,
                "added_container_image_mb": 0.0,
                "added_rss_mb": 0.0,
                "docs_url": "https://www.mongodb.com/docs/atlas/atlas-vector-search/automated-embedding/",
                "checked_date": "2026-11-15",
            },
        }

    report = {
        "spike": "feat-010",
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "dataset": {
            "movie_count": len(movies),
            "avg_profile_chars": round(
                sum(len(m["profile_text"]) for m in movies) / len(movies), 1
            ),
            "sample_profile_text": movies[0]["profile_text"],
        },
        "runtimes": {
            "fastembed_bge_small_en_v1_5": fe_bge,
            "sentence_transformers_bge_small_en_v1_5": st_bge,
            "onnx_vs_pytorch_parity": onnx_vs_pytorch_parity,
            "fastembed_paraphrase_multilingual_minilm_l12_v2": fe_minilm_ml,
            "hosted_options_c": hosted_res,
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[orchestrator] Saved full report to {REPORT_PATH.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=str, default=None)
    args = parser.parse_args()

    if args.worker == "fastembed-bge-small":
        res = run_worker_fastembed("BAAI/bge-small-en-v1.5", is_e5=False)
        print(json.dumps(res))
    elif args.worker == "st-bge-small":
        res = run_worker_sentence_transformers("BAAI/bge-small-en-v1.5")
        print(json.dumps(res))
    elif args.worker == "fastembed-multilingual-minilm":
        res = run_worker_fastembed(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", is_e5=False
        )
        print(json.dumps(res))
    else:
        run_all()


if __name__ == "__main__":
    main()
