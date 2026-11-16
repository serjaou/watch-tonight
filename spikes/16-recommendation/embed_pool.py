"""feat-016 spike Q4: embed the gated corpus (G7) from TMDB data only, for retrieval-depth tests.

THROWAWAY. "Pool A": ~14.5k movies, text = title, year, genres, overview, embedded with the
feat-010 model (fastembed BAAI/bge-small-en-v1.5, 384-d). This is a proxy for the real
profile-based embedding (the 300-movie "Pool B" in enrich.py uses the LLM profile).

Run: uv run --no-project --python 3.13 --with fastembed \
         python spikes/16-recommendation/embed_pool.py [--limit N]
Writes data/pool_a.npy + data/pool_a_meta.jsonl (gitignored).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
DATA = SPIKE_DIR / "data"


def load_g7() -> list[dict[str, Any]]:
    """Recompute G7 exactly as corpus.py does (same C/m from the usable catalogue)."""
    import corpus

    movies = [m for m in corpus.load() if m["year"] and m["year"] <= corpus.THIS_YEAR]
    usable = [m for m in movies if m["has_poster"] and m["overview"].strip()]
    import statistics

    c = statistics.mean(m["vote_average"] for m in usable)
    mm = statistics.median(m["vote_count"] for m in usable)
    kept = []
    for m in usable:
        m["wr_tmdb"] = corpus.wr(m["vote_average"], m["vote_count"], c, mm)
        age = m["age"]
        need = 20 if age <= 1 else 60 if age <= 3 else 120 if age <= 10 else 200
        if m["vote_count"] >= need and m["wr_tmdb"] >= 5.0 and (age <= 25 or m["wr_tmdb"] >= 6.3):
            kept.append(m)
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    import numpy as np
    from fastembed import TextEmbedding

    sys.path.insert(0, str(SPIKE_DIR))
    from tmdb import Tmdb

    genres = {g["id"]: g["name"] for g in Tmdb().get("/genre/movie/list")["genres"]}
    pool = load_g7()
    if args.limit:
        pool = pool[: args.limit]
    texts = [
        f"{m['title']} ({m['year']}). Genres: "
        f"{', '.join(genres.get(g, '') for g in m['genre_ids'])}. {m['overview']}"
        for m in pool
    ]
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    t0 = time.perf_counter()
    vecs = np.array(list(model.embed(texts, batch_size=64)), dtype=np.float32)
    secs = time.perf_counter() - t0
    print(f"embedded {len(texts)} in {secs:.1f}s ({len(texts) / secs:.1f} docs/s)", flush=True)
    if args.limit:
        return
    np.save(DATA / "pool_a.npy", vecs)
    stats = {
        "docs": len(texts),
        "seconds": round(secs, 1),
        "docs_per_s": round(len(texts) / secs, 1),
    }
    (SPIKE_DIR / "pool_a_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    with (DATA / "pool_a_meta.jsonl").open("w", encoding="utf-8") as f:
        for m in pool:
            keep = ("id", "title", "year", "age", "original_language", "vote_average")
            row = {k: m[k] for k in keep}
            row |= {
                "vote_count": m["vote_count"],
                "popularity": m["popularity"],
                "wr_tmdb": round(m["wr_tmdb"], 3),
                "genre_ids": m["genre_ids"],
                "regions": m["regions"],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote pool_a ({len(pool)} movies)")


if __name__ == "__main__":
    main()
