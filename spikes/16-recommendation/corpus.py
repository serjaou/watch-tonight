"""feat-016 spike Q1/Q2: corpus gates, IMDb join coverage and Bayesian quality. THROWAWAY.

Inputs (gitignored, see data/): catalog.jsonl (catalog.py), wikidata_tmdb_imdb.csv (Wikidata
P4947 -> P345, CC0), title.ratings.tsv.gz (IMDb non-commercial dataset, measurement only).
Writes corpus_report.json (aggregates + a few titles as examples; no bulk IMDb data).

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/corpus.py
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import statistics
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
DATA = SPIKE_DIR / "data"
THIS_YEAR = 2026

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

Movie = dict[str, Any]


def load() -> list[Movie]:
    # split("\n"), not splitlines(): TMDB overviews contain U+2028/U+2029, which splitlines()
    # treats as line breaks and would cut a JSON row in half.
    text = (DATA / "catalog.jsonl").read_text("utf-8")
    movies = [json.loads(x) for x in text.split("\n") if x]
    tmdb_to_imdb: dict[int, str] = {}
    with (DATA / "wikidata_tmdb_imdb.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["tmdb"].isdigit() and row["imdb"].startswith("tt"):
                tmdb_to_imdb.setdefault(int(row["tmdb"]), row["imdb"])
    ratings: dict[str, tuple[float, int]] = {}
    with gzip.open(DATA / "title.ratings.tsv.gz", "rt", encoding="utf-8") as f:
        next(f)
        for line in f:
            tconst, avg, votes = line.rstrip("\n").split("\t")
            ratings[tconst] = (float(avg), int(votes))
    for m in movies:
        m["year"] = int(m["release_date"][:4]) if m["release_date"][:4].isdigit() else None
        m["age"] = THIS_YEAR - m["year"] if m["year"] else None
        imdb_id = tmdb_to_imdb.get(m["id"])
        m["imdb_id"] = imdb_id
        r = ratings.get(imdb_id) if imdb_id else None
        m["imdb_rating"], m["imdb_votes"] = (r[0], r[1]) if r else (None, None)
    return movies


def wr(rating: float, votes: int, c: float, m: float) -> float:
    """IMDb-style Bayesian weighted rating: shrinks low-vote ratings towards the mean C."""
    return (votes / (votes + m)) * rating + (m / (votes + m)) * c


def decade(m: Movie) -> str:
    y = m["year"]
    if y is None:
        return "unknown"
    return "pre-1970" if y < 1970 else f"{y // 10 * 10}s"


def spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for rank, i in enumerate(order):
            r[i] = float(rank)
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    return cov / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))


def main() -> None:
    movies = [m for m in load() if m["year"] and m["year"] <= THIS_YEAR]
    usable = [m for m in movies if m["has_poster"] and m["overview"].strip()]
    out: dict[str, Any] = {"catalog_movies_vote_count_ge_10": len(movies)}
    out["usable_poster_and_overview"] = len(usable)

    # --- IMDb join coverage (Q2) -------------------------------------------------------------
    mapped = [m for m in usable if m["imdb_id"]]
    rated = [m for m in usable if m["imdb_votes"]]
    out["imdb_join"] = {
        "wikidata_mapped": f"{len(mapped)}/{len(usable)} ({len(mapped) / len(usable):.1%})",
        "with_imdb_rating": f"{len(rated)}/{len(usable)} ({len(rated) / len(usable):.1%})",
        "by_decade_with_rating": {
            d: f"{sum(1 for m in usable if decade(m) == d and m['imdb_votes'])}"
            f"/{sum(1 for m in usable if decade(m) == d)}"
            for d in sorted({decade(m) for m in usable})
        },
    }

    # --- TMDB vs IMDb signal comparison (Q2) ------------------------------------------------
    both = [m for m in rated if m["vote_count"] and m["vote_count"] >= 10]
    ratio = [m["imdb_votes"] / m["vote_count"] for m in both]
    out["tmdb_vs_imdb"] = {
        "n": len(both),
        "median_imdb_to_tmdb_vote_ratio": round(statistics.median(ratio), 1),
        "spearman_rating_all": round(
            spearman([m["vote_average"] for m in both], [m["imdb_rating"] for m in both]), 3
        ),
        "spearman_rating_tmdb_votes_lt_100": round(
            spearman(
                [m["vote_average"] for m in both if m["vote_count"] < 100],
                [m["imdb_rating"] for m in both if m["vote_count"] < 100],
            ),
            3,
        ),
        "spearman_rating_tmdb_votes_ge_1000": round(
            spearman(
                [m["vote_average"] for m in both if m["vote_count"] >= 1000],
                [m["imdb_rating"] for m in both if m["vote_count"] >= 1000],
            ),
            3,
        ),
    }

    # Bayesian WR per source. C = mean rating of the usable catalogue; m = median votes, so a
    # movie at the median gets half its own rating and half the prior.
    c_tmdb = statistics.mean(m["vote_average"] for m in usable)
    m_tmdb = statistics.median(m["vote_count"] for m in usable)
    c_imdb = statistics.mean(m["imdb_rating"] for m in rated)
    m_imdb = statistics.median(m["imdb_votes"] for m in rated)
    for m in usable:
        m["wr_tmdb"] = wr(m["vote_average"], m["vote_count"], c_tmdb, m_tmdb)
        m["wr_imdb"] = (
            wr(m["imdb_rating"], m["imdb_votes"], c_imdb, m_imdb) if m["imdb_votes"] else None
        )
    out["wr_params"] = {
        "tmdb": {"C": round(c_tmdb, 2), "m": m_tmdb},
        "imdb": {"C": round(c_imdb, 2), "m": m_imdb},
    }
    top = sorted(rated, key=lambda m: -m["wr_tmdb"])[: len(rated) // 10]
    top_i = sorted(rated, key=lambda m: -m["wr_imdb"])[: len(rated) // 10]
    out["wr_top10pct_overlap_tmdb_vs_imdb"] = round(
        len({m["id"] for m in top} & {m["id"] for m in top_i}) / len(top), 3
    )
    out["wr_spearman_tmdb_vs_imdb"] = round(
        spearman([m["wr_tmdb"] for m in rated], [m["wr_imdb"] for m in rated]), 3
    )

    # --- Corpus gates (Q1) --------------------------------------------------------------------
    def age_votes(thresholds: list[tuple[int, int]]) -> Callable[[Movie], int]:
        def need(m: Movie) -> int:
            for max_age, votes in thresholds:
                if m["age"] <= max_age:
                    return votes
            return thresholds[-1][1]

        return need

    tmdb_need = age_votes([(1, 20), (3, 60), (10, 150), (25, 300), (999, 600)])
    imdb_need = age_votes([(1, 1_000), (3, 3_000), (10, 8_000), (25, 15_000), (999, 25_000)])
    gates: dict[str, Callable[[Movie], bool]] = {
        "G0 none (vote_count>=10)": lambda m: True,
        "G1 flat tmdb votes>=50": lambda m: m["vote_count"] >= 50,
        "G2 flat tmdb votes>=200": lambda m: m["vote_count"] >= 200,
        "G3 age-aware tmdb votes": lambda m: m["vote_count"] >= tmdb_need(m),
        "G4 age-aware tmdb votes + WR>=6.0 if age>25": lambda m: (
            m["vote_count"] >= tmdb_need(m) and (m["age"] <= 25 or m["wr_tmdb"] >= 6.0)
        ),
        "G5 age-aware imdb votes": lambda m: (
            bool(m["imdb_votes"]) and m["imdb_votes"] >= imdb_need(m)
        ),
        # Looser on old films: fewer votes needed, but a higher quality bar.
        "G6 age-aware tmdb (old>=300) + WR>=6.5 if age>25": lambda m: (
            m["vote_count"] >= age_votes([(1, 20), (3, 60), (10, 150), (999, 300)])(m)
            and (m["age"] <= 25 or m["wr_tmdb"] >= 6.5)
        ),
        "G7 age-aware tmdb (old>=200) + WR>=6.3 if age>25, WR>=5.0 all": lambda m: (
            m["vote_count"] >= age_votes([(1, 20), (3, 60), (10, 120), (999, 200)])(m)
            and m["wr_tmdb"] >= 5.0
            and (m["age"] <= 25 or m["wr_tmdb"] >= 6.3)
        ),
    }
    gate_out: dict[str, Any] = {}
    decades = sorted({decade(m) for m in usable})
    for name, rule in gates.items():
        kept = [m for m in usable if rule(m)]
        old = [m for m in kept if m["year"] < 2000]
        recent = [m for m in kept if m["age"] <= 3]
        gate_out[name] = {
            "kept": len(kept),
            "by_region": {r: sum(1 for m in kept if r in m["regions"]) for r in ("ES", "US", "BO")},
            "by_decade": {d: sum(1 for m in kept if decade(m) == d) for d in decades},
            "pre_2000_share": round(len(old) / len(kept), 3) if kept else None,
            "last_3_years": len(recent),
            "pre_2000_median_tmdb_wr": round(statistics.median(m["wr_tmdb"] for m in old), 2)
            if old
            else None,
            "lowest_wr_pre_2000_examples": [
                f"{m['title']} ({m['year']}) tmdb {m['vote_average']}/{m['vote_count']}"
                for m in sorted(old, key=lambda m: m["wr_tmdb"])[:5]
            ],
            # What the gate loses: best-rated old films and most popular recent films it drops.
            # Review fix L7: no IMDb values in committed output (licence: no republishing).
            "best_excluded_pre_2000": [
                f"{m['title']} ({m['year']}) tmdb {m['vote_average']}/{m['vote_count']}"
                for m in sorted(
                    (x for x in usable if x["year"] < 2000 and not rule(x)),
                    key=lambda x: -(x["wr_imdb"] or 0),
                )[:6]
            ],
            "most_popular_excluded_last_3_years": [
                f"{m['title']} ({m['year']}) tmdb {m['vote_average']}/{m['vote_count']}"
                f" pop {m['popularity']:.0f}"
                for m in sorted(
                    (x for x in usable if x["age"] <= 3 and not rule(x)),
                    key=lambda x: -x["popularity"],
                )[:4]
            ],
        }
    out["gates"] = gate_out

    # What IMDb would add on top of the recommended TMDB-only gate (G7): movies G7 drops that
    # IMDb rates well with many votes. This sizes the cost of skipping IMDb (licence).
    g7 = gates["G7 age-aware tmdb (old>=200) + WR>=6.3 if age>25, WR>=5.0 all"]
    rescued = [
        m
        for m in usable
        if not g7(m) and m["imdb_votes"] and m["imdb_votes"] >= 10_000 and m["wr_imdb"] >= 7.0
    ]
    out["imdb_rescue_over_G7"] = {
        "rule": "excluded by G7, imdb_votes>=10k and IMDb WR>=7.0",
        "count": len(rescued),
        "share_of_G7": round(len(rescued) / sum(1 for m in usable if g7(m)), 3),
        "by_language_top5": Counter(m["original_language"] for m in rescued).most_common(5),
        "pre_2000": sum(1 for m in rescued if m["year"] < 2000),
        "examples": [
            f"{m['title']} ({m['year']}, {m['original_language']}) tmdb {m['vote_count']} votes"
            for m in sorted(rescued, key=lambda m: -m["imdb_votes"])[:6]
        ],
    }
    out["gate_thresholds"] = {
        "G3/G4 tmdb_age_votes": "age<=1:20, <=3:60, <=10:150, <=25:300, else 600",
        "G5 imdb_age_votes": "age<=1:1k, <=3:3k, <=10:8k, <=25:15k, else 25k",
        "G6 tmdb_age_votes": "age<=1:20, <=3:60, <=10:150, else 300; WR>=6.5 if age>25",
        "G7 tmdb_age_votes": "age<=1:20, <=3:60, <=10:120, else 200; WR>=5.0; WR>=6.3 if age>25",
    }
    out["language_top10_usable"] = Counter(m["original_language"] for m in usable).most_common(10)

    (SPIKE_DIR / "corpus_report.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
