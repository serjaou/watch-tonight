"""feat-017: check churn.py's crawl differences against TMDB's per-movie answer. THROWAWAY.

The crawl diff says a movie "left" or "arrived" in a region because it disappeared from or
appeared in /discover. That is only as good as /discover itself, so this script asks
/movie/{id}?append_to_response=watch/providers (the source of `streamable`, docs/architecture.md
section 4) for a seeded sample of each group, per region:
  - left:    does the movie really have no flat-rate offer in the region now?
  - arrived: does it really have one?
  - stayed:  control group; how often does /discover agree with /watch/providers at all?
and for every G7 movie that left all launch regions (the `streamable: []` proposal).

Run after churn.py, with the same dates:
    uv run --no-project --python 3.13 python spikes/16-recommendation/churn_verify.py \
        --old 2026-11-16 --new 2026-11-21
Writes churn_verify_report_<old>_<new>.json (committed; aggregates and a few example ids only).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
from tmdb import Tmdb  # noqa: E402

DATA = SPIKE_DIR / "data"
REGIONS = ("ES", "US", "BO")
SAMPLE = {"left": 150, "arrived": 150, "stayed": 100}
SEED = 17


def offers(detail: dict[str, Any], region: str) -> set[str]:
    """Monetization types TMDB lists for the movie in the region (flatrate, rent, buy, ads...)."""
    res = detail.get("watch/providers", {}).get("results", {}).get(region, {})
    return {k for k, v in res.items() if isinstance(v, list) and v}


def classify(detail: dict[str, Any], region: str) -> str:
    if "_http_error" in detail:
        return f"http_{detail['_http_error']}"
    types = offers(detail, region)
    under_line = (detail.get("vote_count") or 0) < 10  # below the crawl's vote_count.gte=10
    if "flatrate" in types:
        return "flatrate_but_under_10_votes" if under_line else "flatrate"
    if under_line:
        return "no_flatrate_and_under_10_votes"
    if types:
        return "no_flatrate_other_offers_" + "+".join(sorted(types))
    return "no_offers_in_region"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="2026-11-16")
    ap.add_argument("--new", default="2026-11-21")
    args = ap.parse_args()
    window = f"{args.old}_{args.new}"
    sets = json.loads((DATA / f"churn_sets_{window}.json").read_text("utf-8"))
    rng = random.Random(SEED)
    plan: list[tuple[str, str, int]] = []  # (group, region, id)
    sizes: dict[str, dict[str, int]] = {}
    for region in REGIONS:
        for group, n in SAMPLE.items():
            ids = sets[region][group]
            pick = ids if len(ids) <= n else rng.sample(ids, n)
            plan += [(group, region, i) for i in pick]
            sizes[f"{region}.{group}"] = {"population": len(ids), "checked": len(pick)}
    for i in sets["g7"]["left"]:  # every G7 movie that left all launch regions
        plan += [("g7_left_all", r, i) for r in REGIONS]
    n_g7 = len(sets["g7"]["left"])
    sizes["g7_left_all"] = {"population": n_g7, "checked": n_g7}

    api = Tmdb()
    ids = sorted({i for _, _, i in plan})
    with ThreadPoolExecutor(max_workers=8) as pool:
        details = dict(
            zip(
                ids,
                pool.map(
                    lambda i: api.get(f"/movie/{i}", {"append_to_response": "watch/providers"}), ids
                ),
                strict=True,
            )
        )

    out: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sample_sizes": sizes,
        "seed": SEED,
        "results": {},
    }
    disagree: list[dict[str, Any]] = []  # /discover and /watch/providers disagree
    for region in REGIONS:
        for group in SAMPLE:
            members = [i for g, r, i in plan if g == group and r == region]
            got = Counter(classify(details[i], region) for i in members)
            out["results"][f"{region}.{group}"] = dict(got.most_common())
            for i in members:
                flat = "flatrate" in offers(details[i], region)
                if flat == (group == "left"):
                    res = details[i].get("watch/providers", {}).get("results", {}).get(region, {})
                    disagree.append(
                        {
                            "group": f"{region}.{group}",
                            "id": i,
                            "title": details[i].get("title"),
                            "vote_count": details[i].get("vote_count"),
                            "flatrate_providers": [
                                p.get("provider_name") for p in res.get("flatrate", [])
                            ],
                            "offer_types": sorted(offers(details[i], region)),
                        }
                    )
    out["discover_vs_watch_providers_disagreements"] = disagree
    g7_any = Counter()
    g7_examples: list[dict[str, Any]] = []
    for i in sets["g7"]["left"]:
        flat = [r for r in REGIONS if "flatrate" in offers(details[i], r)]
        g7_any["still_flatrate_somewhere" if flat else "no_flatrate_in_any_launch_region"] += 1
        if flat and len(g7_examples) < 10:
            g7_examples.append({"id": i, "title": details[i].get("title"), "flatrate_in": flat})
    out["results"]["g7_left_all"] = dict(g7_any.most_common())
    out["g7_left_all_but_still_flatrate_examples"] = g7_examples
    out["tmdb_calls"] = api.calls
    out["tmdb_status"] = api.status

    report = SPIKE_DIR / f"churn_verify_report_{window}.json"
    report.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
