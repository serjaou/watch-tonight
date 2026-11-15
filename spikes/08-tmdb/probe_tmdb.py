"""Throwaway spike script for feat-008: TMDB terms, rate limits, and watch providers.

Usage:
    uv run python spikes/08-tmdb/probe_tmdb.py
    uv run python spikes/08-tmdb/probe_tmdb.py --snapshot-out spikes/08-tmdb/snapshot_2.json
    uv run python spikes/08-tmdb/probe_tmdb.py --compare \
        spikes/08-tmdb/snapshot_1.json spikes/08-tmdb/snapshot_2.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASE_URL = "https://api.themoviedb.org/3"
COUNTRIES = ("ES", "US", "BO")
SAMPLE_SIZE = 500
SPIKE_DIR = Path(__file__).resolve().parent


def load_api_key() -> str:
    env_val = os.environ.get("TMDB_API_KEY", "").strip()
    if env_val:
        return env_val
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("TMDB_API_KEY="):
                val = stripped.split("=", 1)[1].strip().strip("'\"")
                if val:
                    return val
    raise RuntimeError("TMDB_API_KEY not found in environment or .env")


class TmdbProber:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self.latencies_ms: list[float] = []
        self.status_counts: dict[int, int] = {}
        self.rate_headers_seen: dict[str, str] = {}
        self.retries = 0

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": "watch-tonight-spike-08/0.1"}
        if len(self._api_key) <= 40 and not self._api_key.startswith("eyJ"):
            query["api_key"] = self._api_key
        else:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{BASE_URL}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        for attempt in range(4):
            t0 = time.perf_counter()
            req = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    self.latencies_ms.append(elapsed_ms)
                    status = resp.status
                    self.status_counts[status] = self.status_counts.get(status, 0) + 1
                    for k, v in resp.headers.items():
                        kl = k.lower()
                        if "ratelimit" in kl or "retry" in kl or kl in ("x-memc", "cache-control"):
                            self.rate_headers_seen[kl] = v
                    raw = resp.read().decode("utf-8")
                    data: dict[str, Any] = json.loads(raw)
                    return data
            except urllib.error.HTTPError as exc:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                self.latencies_ms.append(elapsed_ms)
                self.status_counts[exc.code] = self.status_counts.get(exc.code, 0) + 1
                for k, v in exc.headers.items():
                    kl = k.lower()
                    if "ratelimit" in kl or "retry" in kl:
                        self.rate_headers_seen[kl] = v
                if exc.code == 429 and attempt < 3:
                    self.retries += 1
                    retry_after = float(exc.headers.get("Retry-After", "1.5"))
                    time.sleep(retry_after)
                    continue
                err_body = exc.read().decode("utf-8", errors="replace")
                return {"_http_error": exc.code, "_error_body": err_body}
            except urllib.error.URLError:
                if attempt < 3:
                    self.retries += 1
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(f"Unreachable after retries for {path}")


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100.0) * (len(ordered) - 1))))
    return round(ordered[idx], 1)


def probe_configuration(prober: TmdbProber) -> dict[str, Any]:
    cfg = prober.get("/configuration")
    images = cfg.get("images", {})
    return {
        "base_url": images.get("base_url"),
        "secure_base_url": images.get("secure_base_url"),
        "poster_sizes": images.get("poster_sizes", []),
        "logo_sizes": images.get("logo_sizes", []),
        "backdrop_sizes": images.get("backdrop_sizes", []),
    }


def probe_regions_and_providers(prober: TmdbProber) -> dict[str, Any]:
    regions_resp = prober.get("/watch/providers/regions", {"language": "en-US"})
    regions_by_code = {
        r["iso_3166_1"]: r
        for r in regions_resp.get("results", [])
        if r.get("iso_3166_1") in COUNTRIES
    }

    country_reports: dict[str, Any] = {}
    for cc in COUNTRIES:
        prov_resp = prober.get(
            "/watch/providers/movie",
            {"language": "en-US", "watch_region": cc},
        )
        raw_providers = prov_resp.get("results", [])

        # Also query country-level totals by monetization type
        monetization_totals: dict[str, int] = {}
        for mtype in ("flatrate", "rent", "buy", "free", "ads"):
            disc = prober.get(
                "/discover/movie",
                {
                    "watch_region": cc,
                    "with_watch_monetization_types": mtype,
                    "page": 1,
                },
            )
            monetization_totals[mtype] = int(disc.get("total_results", 0))

        # Probe each provider's flatrate movie count via /discover/movie concurrently
        def fetch_provider_count(p: dict[str, Any], country: str = cc) -> dict[str, Any]:
            pid = p["provider_id"]
            disc = prober.get(
                "/discover/movie",
                {
                    "watch_region": country,
                    "with_watch_providers": str(pid),
                    "with_watch_monetization_types": "flatrate",
                    "page": 1,
                },
            )
            return {
                "provider_id": pid,
                "provider_name": p.get("provider_name"),
                "logo_path": p.get("logo_path"),
                "display_priority": p.get("display_priorities", {}).get(
                    country, p.get("display_priority", 999)
                ),
                "flatrate_movies": int(disc.get("total_results", 0)),
                "flatrate_pages": int(disc.get("total_pages", 0)),
            }

        with ThreadPoolExecutor(max_workers=10) as pool:
            prov_counts = list(pool.map(fetch_provider_count, raw_providers))

        prov_counts.sort(key=lambda x: x["flatrate_movies"], reverse=True)
        non_zero = [p for p in prov_counts if p["flatrate_movies"] > 0]

        country_reports[cc] = {
            "region_info": regions_by_code.get(cc),
            "catalog_providers_listed": len(raw_providers),
            "providers_with_flatrate_movies": len(non_zero),
            "monetization_totals": monetization_totals,
            "sum_of_per_provider_flatrate_pages": sum(p["flatrate_pages"] for p in non_zero),
            "providers": non_zero,
        }

    # Test discover page cap (page=500 vs page=501)
    page_500 = prober.get(
        "/discover/movie",
        {"watch_region": "US", "with_watch_monetization_types": "flatrate", "page": 500},
    )
    page_501 = prober.get(
        "/discover/movie",
        {"watch_region": "US", "with_watch_monetization_types": "flatrate", "page": 501},
    )

    return {
        "countries": country_reports,
        "discover_pagination_check": {
            "page_500_results_len": len(page_500.get("results", [])),
            "page_501_response": page_501,
        },
    }


def probe_popular_500(
    prober: TmdbProber, baseline_ids: list[int] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    movie_ids: list[int] = []
    seen: set[int] = set()
    page = 1
    while len(movie_ids) < SAMPLE_SIZE and page <= 40:
        resp = prober.get("/movie/popular", {"language": "en-US", "page": page})
        for item in resp.get("results", []):
            mid = int(item["id"])
            if mid not in seen:
                seen.add(mid)
                movie_ids.append(mid)
                if len(movie_ids) >= SAMPLE_SIZE:
                    break
        page += 1

    popular_today_ids = list(movie_ids)
    for bid in baseline_ids or []:
        if bid not in seen:
            seen.add(bid)
            movie_ids.append(bid)

    t_batch_start = time.perf_counter()

    def fetch_movie_bundle(mid: int) -> dict[str, Any]:
        return prober.get(
            f"/movie/{mid}",
            {
                "language": "en-US",
                "append_to_response": "keywords,reviews,watch/providers,credits",
            },
        )

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(fetch_movie_bundle, mid) for mid in movie_ids]
        bundles = [f.result() for f in as_completed(futures)]

    batch_elapsed_s = time.perf_counter() - t_batch_start
    batch_rps = len(movie_ids) / batch_elapsed_s if batch_elapsed_s > 0 else 0.0

    # Analyze English data completeness & provider breakdown
    has_overview = 0
    overview_lengths: list[int] = []
    has_keywords_1 = 0
    has_keywords_3 = 0
    keyword_counts: list[int] = []
    has_reviews_1 = 0
    has_reviews_3 = 0
    review_counts: list[int] = []
    has_poster = 0
    missing_poster_movies: list[dict[str, Any]] = []
    has_runtime = 0
    has_genres = 0
    has_director_and_cast = 0
    has_overview_and_keywords = 0
    has_overview_keywords_reviews = 0

    country_Breakdown: dict[str, dict[str, int]] = {
        cc: {"any_entry": 0, "flatrate": 0, "rent": 0, "buy": 0, "free_or_ads": 0}
        for cc in COUNTRIES
    }
    sample_provider_structure: dict[str, Any] = {}
    snapshot_movies: dict[str, dict[str, Any]] = {}

    for b in bundles:
        mid = b.get("id")
        title = b.get("title", "")
        overview = (b.get("overview") or "").strip()
        poster_path = b.get("poster_path")
        runtime = b.get("runtime") or 0
        genres = b.get("genres") or []
        kws = (b.get("keywords") or {}).get("keywords") or []
        revs = (b.get("reviews") or {}).get("results") or []
        credits_obj = b.get("credits") or {}
        crew = credits_obj.get("crew") or []
        cast = credits_obj.get("cast") or []
        directors = [c for c in crew if c.get("job") == "Director"]

        if overview:
            has_overview += 1
            overview_lengths.append(len(overview))
        kw_len = len(kws)
        keyword_counts.append(kw_len)
        if kw_len >= 1:
            has_keywords_1 += 1
        if kw_len >= 3:
            has_keywords_3 += 1

        rev_len = len(revs)
        review_counts.append(rev_len)
        if rev_len >= 1:
            has_reviews_1 += 1
        if rev_len >= 3:
            has_reviews_3 += 1

        if poster_path:
            has_poster += 1
        else:
            missing_poster_movies.append({"id": mid, "title": title})

        if runtime > 0:
            has_runtime += 1
        if len(genres) > 0:
            has_genres += 1
        if len(directors) > 0 and len(cast) > 0:
            has_director_and_cast += 1
        if overview and kw_len >= 1:
            has_overview_and_keywords += 1
        if overview and kw_len >= 1 and rev_len >= 1:
            has_overview_keywords_reviews += 1

        wp_results = (b.get("watch/providers") or {}).get("results") or {}
        streamable_tags: list[str] = []
        for cc in COUNTRIES:
            c_entry = wp_results.get(cc)
            if not c_entry:
                continue
            country_Breakdown[cc]["any_entry"] += 1
            flat = c_entry.get("flatrate") or []
            rent = c_entry.get("rent") or []
            buy = c_entry.get("buy") or []
            free = (c_entry.get("free") or []) + (c_entry.get("ads") or [])
            if flat:
                country_Breakdown[cc]["flatrate"] += 1
                for p in flat:
                    streamable_tags.append(f"{cc}:{p['provider_id']}")
            if rent:
                country_Breakdown[cc]["rent"] += 1
            if buy:
                country_Breakdown[cc]["buy"] += 1
            if free:
                country_Breakdown[cc]["free_or_ads"] += 1

            if not sample_provider_structure and flat and rent and buy and cc == "US":
                sample_provider_structure = {
                    "movie_id": mid,
                    "title": title,
                    "country": cc,
                    "keys_present": sorted(c_entry.keys()),
                    "link": c_entry.get("link"),
                    "flatrate_sample": flat[:2],
                    "rent_sample": rent[:1],
                    "buy_sample": buy[:1],
                }

        snapshot_movies[str(mid)] = {
            "title": title,
            "streamable": sorted(set(streamable_tags)),
        }

    # Also sample deeper flat-rate discover pages across popularity tiers (for Q13 poster check)
    deep_pages = (1, 10, 50, 100, 200, 300, 400, 500)
    deep_stats: dict[str, dict[str, int]] = {}
    for cc in COUNTRIES:
        total_checked = 0
        missing_poster = 0
        missing_overview = 0
        for pnum in deep_pages:
            disc = prober.get(
                "/discover/movie",
                {
                    "watch_region": cc,
                    "with_watch_monetization_types": "flatrate",
                    "sort_by": "popularity.desc",
                    "language": "en-US",
                    "page": pnum,
                },
            )
            for item in disc.get("results", []):
                total_checked += 1
                if not item.get("poster_path"):
                    missing_poster += 1
                if not (item.get("overview") or "").strip():
                    missing_overview += 1
        deep_stats[cc] = {
            "sampled_movies_across_pages_1_to_500": total_checked,
            "missing_poster_path": missing_poster,
            "missing_overview": missing_overview,
        }

    # Also check /movie/changes (24h window default) to see global daily change volume
    changes_p1 = prober.get("/movie/changes", {"page": 1})
    changes_info = {
        "total_results_24h": changes_p1.get("total_results"),
        "total_pages_24h": changes_p1.get("total_pages"),
    }

    # Also capture top-100 flat-rate movie IDs per country (pages 1..5) for snapshot comparison
    country_top_flatrate_ids: dict[str, list[int]] = {}
    country_newest_flatrate_ids: dict[str, list[int]] = {}
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    for cc in COUNTRIES:
        pop_ids: list[int] = []
        new_ids: list[int] = []
        for pnum in range(1, 6):
            d_pop = prober.get(
                "/discover/movie",
                {
                    "watch_region": cc,
                    "with_watch_monetization_types": "flatrate",
                    "sort_by": "popularity.desc",
                    "page": pnum,
                },
            )
            pop_ids.extend(int(m["id"]) for m in d_pop.get("results", []))
            d_new = prober.get(
                "/discover/movie",
                {
                    "watch_region": cc,
                    "with_watch_monetization_types": "flatrate",
                    "sort_by": "primary_release_date.desc",
                    "primary_release_date.lte": today_str,
                    "page": pnum,
                },
            )
            new_ids.extend(int(m["id"]) for m in d_new.get("results", []))
        country_top_flatrate_ids[cc] = pop_ids
        country_newest_flatrate_ids[cc] = new_ids

    n = len(bundles)
    summary = {
        "sample_size": n,
        "batch_500_elapsed_s": round(batch_elapsed_s, 2),
        "batch_500_achieved_rps": round(batch_rps, 2),
        "english_data_completeness": {
            "has_overview": has_overview,
            "has_overview_pct": round(100.0 * has_overview / n, 2),
            "overview_chars_median": round(statistics.median(overview_lengths), 1)
            if overview_lengths
            else 0,
            "has_at_least_1_keyword": has_keywords_1,
            "has_at_least_1_keyword_pct": round(100.0 * has_keywords_1 / n, 2),
            "has_at_least_3_keywords": has_keywords_3,
            "has_at_least_3_keywords_pct": round(100.0 * has_keywords_3 / n, 2),
            "keywords_median": round(statistics.median(keyword_counts), 1),
            "has_at_least_1_review": has_reviews_1,
            "has_at_least_1_review_pct": round(100.0 * has_reviews_1 / n, 2),
            "has_at_least_3_reviews": has_reviews_3,
            "has_at_least_3_reviews_pct": round(100.0 * has_reviews_3 / n, 2),
            "reviews_median": round(statistics.median(review_counts), 1),
            "has_poster_path": has_poster,
            "has_poster_path_pct": round(100.0 * has_poster / n, 2),
            "missing_poster_path_count": n - has_poster,
            "missing_poster_path_pct": round(100.0 * (n - has_poster) / n, 2),
            "missing_poster_movies": missing_poster_movies,
            "has_runtime_gt_0": has_runtime,
            "has_genres": has_genres,
            "has_director_and_cast": has_director_and_cast,
            "has_overview_and_keywords": has_overview_and_keywords,
            "has_overview_and_keywords_pct": round(100.0 * has_overview_and_keywords / n, 2),
            "has_overview_keywords_and_reviews": has_overview_keywords_reviews,
            "has_overview_keywords_and_reviews_pct": round(
                100.0 * has_overview_keywords_reviews / n, 2
            ),
        },
        "deep_flatrate_catalog_sample": deep_stats,
        "watch_providers_in_popular_500": country_Breakdown,
        "sample_provider_structure": sample_provider_structure,
        "tmdb_movie_changes_24h": changes_info,
    }

    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "popular_500_ids": popular_today_ids,
        "popular_500_streamable": snapshot_movies,
        "country_top_100_flatrate_ids": country_top_flatrate_ids,
        "country_newest_100_flatrate_ids": country_newest_flatrate_ids,
    }
    return summary, snapshot


def compare_snapshots(path1: Path, path2: Path) -> dict[str, Any]:
    s1 = json.loads(path1.read_text(encoding="utf-8"))
    s2 = json.loads(path2.read_text(encoding="utf-8"))

    m1: dict[str, dict[str, Any]] = s1["popular_500_streamable"]
    m2: dict[str, dict[str, Any]] = s2["popular_500_streamable"]
    common_ids = set(m1.keys()) & set(m2.keys())
    pop1_ids = set(str(x) for x in s1.get("popular_500_ids", list(m1.keys())))
    pop2_ids = set(str(x) for x in s2.get("popular_500_ids", list(m2.keys())))
    new_in_popular_500 = pop2_ids - pop1_ids

    per_country_popular_churn: dict[str, dict[str, int]] = {
        cc: {
            "added_movie_provider_pairs": 0,
            "removed_movie_provider_pairs": 0,
            "movies_changed": 0,
        }
        for cc in COUNTRIES
    }
    changed_examples: list[dict[str, Any]] = []
    for mid in sorted(common_ids, key=int):
        tags1 = set(m1[mid]["streamable"])
        tags2 = set(m2[mid]["streamable"])
        if tags1 != tags2 and len(changed_examples) < 15:
            changed_examples.append(
                {
                    "movie_id": int(mid),
                    "title": m2[mid].get("title") or m1[mid].get("title"),
                    "added": sorted(tags2 - tags1),
                    "removed": sorted(tags1 - tags2),
                }
            )
        for cc in COUNTRIES:
            c1 = {t for t in tags1 if t.startswith(f"{cc}:")}
            c2 = {t for t in tags2 if t.startswith(f"{cc}:")}
            added = c2 - c1
            removed = c1 - c2
            if added or removed:
                per_country_popular_churn[cc]["movies_changed"] += 1
                per_country_popular_churn[cc]["added_movie_provider_pairs"] += len(added)
                per_country_popular_churn[cc]["removed_movie_provider_pairs"] += len(removed)

    top_100_churn: dict[str, Any] = {}
    newest_100_churn: dict[str, Any] = {}
    for cc in COUNTRIES:
        ids1 = set(s1.get("country_top_100_flatrate_ids", {}).get(cc, []))
        ids2 = set(s2.get("country_top_100_flatrate_ids", {}).get(cc, []))
        added_top = ids2 - ids1
        removed_top = ids1 - ids2
        top_100_churn[cc] = {
            "top_100_added": len(added_top),
            "top_100_removed": len(removed_top),
            "added_not_in_snapshot1_popular_500": len(added_top - {int(k) for k in m1}),
        }
        n1 = set(s1.get("country_newest_100_flatrate_ids", {}).get(cc, []))
        n2 = set(s2.get("country_newest_100_flatrate_ids", {}).get(cc, []))
        added_new = n2 - n1
        removed_new = n1 - n2
        newest_100_churn[cc] = {
            "newest_100_added": len(added_new),
            "newest_100_removed": len(removed_new),
            "added_not_in_snapshot1_popular_500": len(added_new - {int(k) for k in m1}),
        }

    # Provider total_results delta if present
    prov_totals_delta: dict[str, Any] = {}
    if "provider_totals" in s1 and "provider_totals" in s2:
        for cc in COUNTRIES:
            p1 = s1["provider_totals"].get(cc, {})
            p2 = s2["provider_totals"].get(cc, {})
            prov_totals_delta[cc] = {
                "flatrate_total_s1": p1.get("flatrate_total"),
                "flatrate_total_s2": p2.get("flatrate_total"),
                "flatrate_total_delta": (p2.get("flatrate_total") or 0)
                - (p1.get("flatrate_total") or 0),
            }

    return {
        "snapshot_1_captured_at": s1.get("captured_at"),
        "snapshot_2_captured_at": s2.get("captured_at"),
        "common_popular_movies_compared": len(common_ids),
        "popular_500_id_turnover": len(new_in_popular_500),
        "per_country_popular_500_churn": per_country_popular_churn,
        "changed_movie_examples": changed_examples,
        "per_country_top_100_flatrate_churn": top_100_churn,
        "per_country_newest_100_flatrate_churn": newest_100_churn,
        "provider_totals_delta": prov_totals_delta,
    }


def verify_discover_vs_movie_providers(prober: TmdbProber) -> dict[str, Any]:
    """Check whether /discover/movie couples with_watch_providers to with_watch_monetization_types
    or evaluates them independently at the movie level."""
    disc = prober.get(
        "/discover/movie",
        {
            "watch_region": "US",
            "with_watch_providers": "2",  # Apple TV Store (rent/buy store)
            "with_watch_monetization_types": "flatrate",
            "page": 1,
        },
    )
    sample_ids = [int(m["id"]) for m in disc.get("results", [])[:5]]
    inspected: list[dict[str, Any]] = []
    for mid in sample_ids:
        wp = prober.get(f"/movie/{mid}/watch/providers")
        us_data = (wp.get("results") or {}).get("US") or {}
        flat_ids = [p["provider_id"] for p in (us_data.get("flatrate") or [])]
        rent_ids = [p["provider_id"] for p in (us_data.get("rent") or [])]
        buy_ids = [p["provider_id"] for p in (us_data.get("buy") or [])]
        inspected.append(
            {
                "movie_id": mid,
                "provider_2_in_flatrate": 2 in flat_ids,
                "provider_2_in_rent": 2 in rent_ids,
                "provider_2_in_buy": 2 in buy_ids,
                "actual_flatrate_provider_ids": flat_ids,
            }
        )

    # Also test a subscription provider (Netflix = 8 in US) with flatrate
    disc_nf = prober.get(
        "/discover/movie",
        {
            "watch_region": "US",
            "with_watch_providers": "8",
            "with_watch_monetization_types": "flatrate",
            "page": 1,
        },
    )
    nf_ids = [int(m["id"]) for m in disc_nf.get("results", [])[:5]]
    nf_inspected: list[dict[str, Any]] = []
    for mid in nf_ids:
        wp = prober.get(f"/movie/{mid}/watch/providers")
        us_data = (wp.get("results") or {}).get("US") or {}
        flat_ids = [p["provider_id"] for p in (us_data.get("flatrate") or [])]
        nf_inspected.append(
            {
                "movie_id": mid,
                "provider_8_in_flatrate": 8 in flat_ids,
                "actual_flatrate_provider_ids": flat_ids,
            }
        )

    return {
        "apple_tv_store_id_2_with_flatrate_filter": inspected,
        "netflix_id_8_with_flatrate_filter": nf_inspected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="TMDB spike probe")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("SNAP1", "SNAP2"),
        help="Compare two saved snapshot JSON files",
    )
    parser.add_argument(
        "--verify-discover",
        action="store_true",
        help="Run quick verification of /discover/movie vs /movie/{id}/watch/providers",
    )
    parser.add_argument(
        "--snapshot-out",
        default=str(SPIKE_DIR / "snapshot_1.json"),
        help="Path to save provider snapshot JSON",
    )
    args = parser.parse_args()

    if args.compare:
        diff = compare_snapshots(Path(args.compare[0]), Path(args.compare[1]))
        report_path = SPIKE_DIR / "report.json"
        if report_path.exists():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            existing["snapshot_comparison"] = diff
            report_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(diff, indent=2))
        return

    api_key = load_api_key()
    prober = TmdbProber(api_key)

    if args.verify_discover:
        v = verify_discover_vs_movie_providers(prober)
        report_path = SPIKE_DIR / "report.json"
        if report_path.exists():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            existing["discover_vs_movie_providers_verification"] = v
            report_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(v, indent=2))
        return
    t0 = time.perf_counter()

    baseline_ids: list[int] = []
    snap1_default = SPIKE_DIR / "snapshot_1.json"
    snap_path = Path(args.snapshot_out)
    if snap1_default.exists() and snap_path.resolve() != snap1_default.resolve():
        s1_data = json.loads(snap1_default.read_text(encoding="utf-8"))
        baseline_ids = [int(k) for k in s1_data.get("popular_500_streamable", {})]

    cfg_report = probe_configuration(prober)
    prov_report = probe_regions_and_providers(prober)
    pop_report, snapshot = probe_popular_500(prober, baseline_ids=baseline_ids)
    verify_report = verify_discover_vs_movie_providers(prober)

    total_elapsed_s = time.perf_counter() - t0
    total_reqs = len(prober.latencies_ms)

    # Attach provider totals to snapshot for day-over-day comparison
    snapshot["provider_totals"] = {
        cc: {
            "flatrate_total": prov_report["countries"][cc]["monetization_totals"]["flatrate"],
            "top_providers": {
                str(p["provider_id"]): p["flatrate_movies"]
                for p in prov_report["countries"][cc]["providers"][:15]
            },
        }
        for cc in COUNTRIES
    }

    snap_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    full_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "request_telemetry": {
            "total_requests": total_reqs,
            "total_elapsed_s": round(total_elapsed_s, 2),
            "overall_rps": round(total_reqs / total_elapsed_s, 2) if total_elapsed_s > 0 else 0.0,
            "latency_p50_ms": percentile(prober.latencies_ms, 50),
            "latency_p95_ms": percentile(prober.latencies_ms, 95),
            "status_counts": prober.status_counts,
            "retries_429_or_network": prober.retries,
            "rate_or_cache_headers_seen": prober.rate_headers_seen,
        },
        "configuration": cfg_report,
        "watch_providers": prov_report,
        "popular_500_probe": pop_report,
        "discover_vs_movie_providers_verification": verify_report,
        "snapshot_saved_to": str(snap_path.resolve().relative_to(SPIKE_DIR.parents[1])),
    }

    report_path = SPIKE_DIR / "report.json"
    if not report_path.exists() or snap_path.resolve() == snap1_default.resolve():
        report_path.write_text(json.dumps(full_report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved snapshot to {snap_path}")
    print(json.dumps(full_report["request_telemetry"], indent=2))
    print(json.dumps(full_report["popular_500_probe"]["english_data_completeness"], indent=2))


if __name__ == "__main__":
    main()
