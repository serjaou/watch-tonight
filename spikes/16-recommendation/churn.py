"""feat-016 spike Q1 follow-up, measured in feat-017: catalogue churn between two crawls. THROWAWAY.

Compares two complete flat-rate crawls (catalog.py) of ES, US and BO, named by crawl date:
  - old: the local ids snapshot catalog_ids_<old>.json.gz (id -> region letters B/E/U).
    G7 membership comes from its `g7_ids` when present; otherwise from the raw rows of that
    crawl, data/catalog_<old>.jsonl (gitignored; for 2026-11-16 it is a copy of data/catalog.jsonl);
  - new: data/catalog_<new>.jsonl and catalog_stats_<new>.json, from `catalog.py --dated`.
Counts, per region and for the three combined, the movies that left and arrived, per day; the
same for the G7 corpus gate (pinned C = 6.08, m = 50, docs/architecture.md section 4); and
splits arrivals and admissions by release year. Two snapshots show net change only: a film that
left and came back, or arrived and left, in between is invisible.

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/catalog.py --dated
     uv run --no-project --python 3.13 python spikes/16-recommendation/churn.py \
         --old 2026-11-16 --new <date of the new crawl>
Writes churn_report_<old>_<new>.json (committed), catalog_ids_<new>.json.gz (gitignored), and
data/churn_sets_<old>_<new>.json (ids, for churn_verify.py). Outputs are named by window, so a
later run never overwrites an earlier measurement.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
DATA = SPIKE_DIR / "data"
REGIONS = {"B": "BO", "E": "ES", "U": "US"}
C_PINNED, M_PINNED = 6.08, 50  # G7 WR constants pinned in docs/architecture.md section 4
RECENT_DAYS = 90  # "recent release": released at most this many days before the new crawl
NEAR_VOTE_LINE = 20  # union arrivals below this many votes may only have crossed the 10-vote line

Movie = dict[str, Any]


def load_jsonl(path: Path) -> dict[int, Movie]:
    # split("\n"), not splitlines(): overviews contain U+2028/U+2029 (see corpus.py).
    text = path.read_text("utf-8")
    return {int(m["id"]): m for m in (json.loads(x) for x in text.split("\n") if x)}


def passes_g7(m: Movie, this_year: int) -> bool:
    """G7 as in corpus.py, with the pinned C and m instead of the per-crawl mean and median.

    `this_year` is the crawl's year (corpus.py used 2026 for the 2026-11-16 crawl).
    """
    year = int(m["release_date"][:4]) if m.get("release_date", "")[:4].isdigit() else None
    if year is None or year > this_year or not m.get("has_poster") or not m["overview"].strip():
        return False
    age = this_year - year
    votes = m["vote_count"] or 0
    wr = (votes / (votes + M_PINNED)) * (m["vote_average"] or 0) + (
        M_PINNED / (votes + M_PINNED)
    ) * C_PINNED
    need = 20 if age <= 1 else 60 if age <= 3 else 120 if age <= 10 else 200
    return votes >= need and wr >= 5.0 and (age <= 25 or wr >= 6.3)


def per_day(n: int, days: float) -> float:
    return round(n / days, 1)


def poisson_range_per_day(k: int, days: float) -> list[float]:
    """Exact 95% Poisson interval for a count, per day: the counting noise of one window."""

    def cdf(n: int, mu: float) -> float:
        return sum(math.exp(-mu + i * math.log(mu) - math.lgamma(i + 1)) for i in range(n + 1))

    def solve(too_high: Any) -> float:
        lo, hi = 1e-9, 10.0 * k + 10
        for _ in range(200):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if too_high(mid) else (mid, hi)
        return (lo + hi) / 2

    low = 0.0 if k == 0 else solve(lambda mu: 1 - cdf(k - 1, mu) >= 0.025)
    high = solve(lambda mu: cdf(k, mu) <= 0.025)
    return [round(low / days, 1), round(high / days, 1)]


def check_complete(stats: dict[str, Any]) -> None:
    """A lost page shows up as false "left" movies, so refuse an incomplete crawl."""
    bad = {k: v for k, v in stats["tmdb_status"].items() if k != "200"}
    # rows_seen counts duplicate rows too; by_region_count (unique ids) also catches page drift
    # under the popularity.desc sort (a duplicate on one page, a miss on another).
    short = {
        r: s
        for r, s in stats["regions"].items()
        if s["slices_over_cap"]
        or s["rows_seen"] < s["sum_slice_totals"]
        or stats["by_region_count"][r] < s["sum_slice_totals"]
    }
    if bad or short:
        raise SystemExit(f"incomplete crawl: statuses {bad}, regions {short}; re-run catalog.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="2026-11-16", help="date of the committed ids snapshot")
    ap.add_argument("--new", default="2026-11-21", help="date of the dated new crawl")
    args = ap.parse_args()

    snap = json.loads(gzip.decompress((SPIKE_DIR / f"catalog_ids_{args.old}.json.gz").read_bytes()))
    old_regions = {int(k): {REGIONS[c] for c in v} for k, v in snap["ids"].items()}
    new_rows = load_jsonl(DATA / f"catalog_{args.new}.jsonl")
    new_regions = {i: set(m["regions"]) for i, m in new_rows.items()}
    stats = json.loads((SPIKE_DIR / f"catalog_stats_{args.new}.json").read_text("utf-8"))
    check_complete(stats)
    then = datetime.fromisoformat(snap["crawled_at"].replace("Z", "+00:00"))
    crawled = datetime.fromisoformat(stats["checked_at"])
    if "g7_ids" in snap:
        g7_old = set(snap["g7_ids"])
    else:
        old_rows = load_jsonl(DATA / f"catalog_{args.old}.jsonl")
        if set(old_rows) != set(old_regions):
            raise SystemExit(f"data/catalog_{args.old}.jsonl does not match the ids snapshot")
        g7_old = {i for i, m in old_rows.items() if passes_g7(m, then.year)}
    days = (crawled - then).total_seconds() / 86400

    out: dict[str, Any] = {
        "old_crawl": snap["crawled_at"],
        "new_crawl": stats["checked_at"],
        "days_between_crawls": round(days, 2),
        "method": "two complete /discover flat-rate crawls (vote_count>=10), net change only",
        "regions": {},
    }
    sets: dict[str, dict[str, list[int]]] = {}
    for region in REGIONS.values():
        old = {i for i, r in old_regions.items() if region in r}
        new = {i for i, r in new_regions.items() if region in r}
        left, came = old - new, new - old
        out["regions"][region] = {
            "old": len(old),
            "new": len(new),
            "left": len(left),
            "left_per_day": per_day(len(left), days),
            "left_pct_of_old": round(100 * len(left) / len(old), 2),
            "arrived": len(came),
            "arrived_per_day": per_day(len(came), days),
            "arrived_still_in_other_region_or_new_to_all": {
                "in_old_crawl_elsewhere": sum(1 for i in came if i in old_regions),
                "new_to_all_regions": sum(1 for i in came if i not in old_regions),
            },
        }
        sets[region] = {"left": sorted(left), "arrived": sorted(came), "stayed": sorted(old & new)}

    # Combined: movies in no launch region any more (they would get `streamable: []`).
    old_all, new_all = set(old_regions), set(new_regions)
    gone, came = old_all - new_all, new_all - old_all
    cutoff = (crawled - timedelta(days=RECENT_DAYS)).date()

    def released(m: Movie) -> date | None:
        try:
            return date.fromisoformat(m["release_date"])
        except ValueError:
            return None

    recent = {i for i in came if (d := released(new_rows[i])) and d >= cutoff}
    near_line = {i for i in came - recent if (new_rows[i]["vote_count"] or 0) < NEAR_VOTE_LINE}
    out["combined"] = {
        "old": len(old_all),
        "new": len(new_all),
        "left_all_launch_regions": len(gone),
        "left_per_day": per_day(len(gone), days),
        "left_pct_of_old": round(100 * len(gone) / len(old_all), 2),
        "arrived_new_to_all_regions": len(came),
        "arrived_per_day": per_day(len(came), days),
        "arrived_split": {
            f"released_in_last_{RECENT_DAYS}_days": len(recent),
            f"older_and_under_{NEAR_VOTE_LINE}_votes (may only have crossed the 10-vote line)": len(
                near_line
            ),
            "older_and_established (entered flat-rate)": len(came - recent - near_line),
        },
    }
    sets["combined"] = {"left": sorted(gone), "arrived": sorted(came)}

    # The corpus: G7 at admission. Leavers are judged on the old crawl's data, arrivals now.
    g7_new = {i for i, m in new_rows.items() if passes_g7(m, crawled.year)}
    g7_gone = g7_old - new_all
    admitted = g7_new - g7_old
    g7_lost_some = sum(1 for i in g7_old & new_all if old_regions[i] - new_regions[i])
    out["g7_corpus"] = {
        "gate": "G7, pinned C=6.08 m=50; poster and overview required",
        "old": len(g7_old),
        "new": len(g7_new),
        "left_all_launch_regions": len(g7_gone),
        "left_per_day": per_day(len(g7_gone), days),
        "left_per_day_95pct_counting_noise": poisson_range_per_day(len(g7_gone), days),
        "left_pct_of_old": round(100 * len(g7_gone) / len(g7_old), 2),
        "left_some_but_not_all_regions": g7_lost_some,
        "lost_flat_rate_in_at_least_one_region_per_day": per_day(len(g7_gone) + g7_lost_some, days),
        "admissions_new_to_g7": len(admitted),
        "admissions_per_day": per_day(len(admitted), days),
        "admissions_per_day_95pct_counting_noise": poisson_range_per_day(len(admitted), days),
    }

    # Admissions by release year and by whether the film was already crawled (i.e. on
    # flat-rate with >= 10 votes) on the old date: not crawled = it newly reached flat-rate
    # (or, rarely, 10 votes); crawled = it only crossed a G7 vote or WR line.
    def bucket(i: int) -> str:
        y = new_rows[i]["release_date"][:4]
        return y if y in {"2024", "2025", "2026"} else "2023_or_older"

    table: dict[str, Any] = {}
    for b in ("2026", "2025", "2024", "2023_or_older"):
        ids = [i for i in admitted if bucket(i) == b]
        table[b] = {
            "not_in_old_crawl": sum(1 for i in ids if i not in old_all),
            "in_old_crawl_below_g7": sum(1 for i in ids if i in old_all),
            "median_vote_count": statistics.median(new_rows[i]["vote_count"] for i in ids)
            if ids
            else None,
        }
    out["g7_corpus"]["admissions_by_release_year"] = table
    out["g7_corpus"]["admissions_median_vote_count_all"] = statistics.median(
        new_rows[i]["vote_count"] for i in admitted
    )
    sets["g7"] = {"left": sorted(g7_gone), "admitted": sorted(admitted)}

    window = f"{args.old}_{args.new}"
    report = SPIKE_DIR / f"churn_report_{window}.json"
    report.write_text(json.dumps(out, indent=2), encoding="utf-8")
    (DATA / f"churn_sets_{window}.json").write_text(json.dumps(sets), encoding="utf-8")
    # Ids-only snapshot of the new crawl (same format as the old one, plus the G7 ids at the
    # pinned constants), committed so a later crawl can measure a longer window, G7 included,
    # without the gitignored raw rows.
    letters = {v: k for k, v in REGIONS.items()}
    new_snap = {
        "crawled_at": crawled.strftime("%Y-%m-%dT%H:%MZ"),
        "min_vote_count": snap["min_vote_count"],
        "ids": {str(i): "".join(sorted(letters[r] for r in new_regions[i])) for i in new_rows},
        "g7_ids": sorted(g7_new),
    }
    payload = json.dumps(new_snap, separators=(",", ":")).encode("utf-8")
    (SPIKE_DIR / f"catalog_ids_{args.new}.json.gz").write_bytes(gzip.compress(payload, mtime=0))
    print(json.dumps(out, indent=2))
    print(f"(written {datetime.now(UTC).isoformat(timespec='seconds')})")


if __name__ == "__main__":
    main()
