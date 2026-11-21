"""feat-016 spike Q1: crawl the TMDB flat-rate catalogue for ES, US and BO. THROWAWAY.

/discover/movie caps total_results at 20,001 and pages at 500 (10k results), so each region is
sliced by release-year window (and split further while a slice is >= 10k). Only movies with
vote_count >= 10 are crawled: below that is filler for any corpus gate (noted in the spike doc).

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/catalog.py [--dated]
Writes data/catalog.jsonl (gitignored: raw TMDB rows) and catalog_stats.json (committed): the
2026-11-16 crawl that spike 16's tables use. With --dated (feat-017 and later re-crawls), it
writes data/catalog_<UTC date>.jsonl and catalog_stats_<UTC date>.json instead, for churn.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
from tmdb import Tmdb  # noqa: E402

DATA_DIR = SPIKE_DIR / "data"
REGIONS = ("ES", "US", "BO")
MIN_VOTES = 10
PAGE_CAP = 500
BASE = {
    "with_watch_monetization_types": "flatrate",
    "include_adult": "false",
    "include_video": "false",
    "sort_by": "popularity.desc",
    "vote_count.gte": MIN_VOTES,
}


def year_windows() -> list[tuple[str, str]]:
    edges = [(1900, 1959), (1960, 1969), (1970, 1979), (1980, 1989), (1990, 1994), (1995, 1999)]
    edges += [(y, y + 1) for y in range(2000, 2016, 2)]
    edges += [(y, y) for y in range(2016, datetime.now(UTC).year + 1)]  # up to this year
    return [(f"{a}-01-01", f"{b}-12-31") for a, b in edges]


def plan_slices(api: Tmdb, region: str) -> list[dict[str, Any]]:
    """Return slices whose total_results fit under the 10k page cap (split by half-years)."""
    slices: list[dict[str, Any]] = []
    for start, end in year_windows():
        params = BASE | {
            "watch_region": region,
            "primary_release_date.gte": start,
            "primary_release_date.lte": end,
        }
        total = int(api.get("/discover/movie", params).get("total_results", 0))
        if total >= PAGE_CAP * 20:
            year = start[:4]
            for a, b in ((f"{year}-01-01", f"{year}-06-30"), (f"{year}-07-01", end)):
                p = params | {"primary_release_date.gte": a, "primary_release_date.lte": b}
                t = int(api.get("/discover/movie", p).get("total_results", 0))
                slices.append({"params": p, "total": t})
        elif total:
            slices.append({"params": params, "total": total})
    return slices


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dated", action="store_true", help="write dated files (re-crawls)")
    args = ap.parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / ".gitignore").write_text("*\n", encoding="utf-8")
    api = Tmdb()
    t0 = time.perf_counter()
    movies: dict[int, dict[str, Any]] = {}
    started = datetime.now(UTC)
    suffix = f"_{started.date().isoformat()}" if args.dated else ""
    stats: dict[str, Any] = {"checked_at": started.isoformat(), "regions": {}}

    for region in REGIONS:
        slices = plan_slices(api, region)
        over = [s for s in slices if s["total"] >= PAGE_CAP * 20]
        jobs = [
            (s["params"], page)
            for s in slices
            for page in range(1, min(PAGE_CAP, -(-s["total"] // 20)) + 1)
        ]
        with ThreadPoolExecutor(max_workers=8) as pool:
            pages = list(
                pool.map(lambda j: api.get("/discover/movie", j[0] | {"page": j[1]}), jobs)
            )
        seen = 0
        for data in pages:
            for m in data.get("results", []):
                if m.get("softcore") or m.get("adult"):
                    continue
                seen += 1
                row = movies.setdefault(
                    int(m["id"]),
                    {
                        "id": int(m["id"]),
                        "title": m.get("title"),
                        "original_language": m.get("original_language"),
                        "release_date": m.get("release_date") or "",
                        "vote_average": m.get("vote_average"),
                        "vote_count": m.get("vote_count"),
                        "popularity": m.get("popularity"),
                        "genre_ids": m.get("genre_ids", []),
                        "overview": m.get("overview") or "",
                        "has_poster": bool(m.get("poster_path")),
                        "regions": [],
                    },
                )
                if region not in row["regions"]:
                    row["regions"].append(region)
        stats["regions"][region] = {
            "slices": len(slices),
            "slices_over_cap": len(over),
            "sum_slice_totals": sum(s["total"] for s in slices),
            "pages_fetched": len(jobs),
            "rows_seen": seen,
        }
        print(f"[{region}] {len(slices)} slices, {len(jobs)} pages, {seen} rows", flush=True)

    with (DATA_DIR / f"catalog{suffix}.jsonl").open("w", encoding="utf-8") as f:
        for m in movies.values():
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    stats["union_movies"] = len(movies)
    stats["by_region_count"] = {
        r: sum(1 for m in movies.values() if r in m["regions"]) for r in REGIONS
    }
    stats["tmdb_calls"] = api.calls
    stats["tmdb_status"] = api.status
    stats["seconds"] = round(time.perf_counter() - t0, 1)
    stats_path = SPIKE_DIR / f"catalog_stats{suffix}.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
