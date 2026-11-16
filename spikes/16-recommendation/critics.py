"""feat-016 spike Q2: does a critics signal (Wikidata RT / Metacritic / awards) add anything?

THROWAWAY. On the G7 corpus: coverage of each signal, how it correlates with the audience
quality score (TMDB WR), and examples where critics and audiences disagree — the cases
`acclaim_preference` ("critically_acclaimed" vs "crowd_pleaser") would need to separate.

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/critics.py
Writes critics_report.json.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from corpus import spearman  # noqa: E402
from embed_pool import load_g7  # noqa: E402


def pct(values: list[str]) -> float | None:
    """RT Tomatometer as 0-100 from strings like '93%' (ignore '8.1/10' averages)."""
    nums = [float(v[:-1]) for v in values if re.fullmatch(r"\d{1,3}%", v)]
    return max(nums) if nums else None


def metacritic(values: list[str]) -> float | None:
    nums = [float(v.split("/")[0]) for v in values if re.fullmatch(r"\d{1,3}/100", v)]
    return max(nums) if nums else None


def main() -> None:
    g7 = load_g7()
    sig: dict[str, Any] = json.loads(
        (SPIKE_DIR / "data" / "wikidata_signals.json").read_text("utf-8")
    )
    for m in g7:
        s = sig.get(m["imdb_id"] or "", {})
        m["rt"] = pct(s.get("rt", []))
        m["mc"] = metacritic(s.get("mc", []))
        m["awards"] = s.get("awards", 0)
        m["noms"] = s.get("noms", 0)
    n = len(g7)

    def cov(key: str, cond: Any = None) -> str:
        k = sum(1 for m in g7 if (m[key] if cond is None else cond(m)))
        return f"{k}/{n} ({k / n:.1%})"

    out: dict[str, Any] = {"g7_movies": n}
    out["coverage"] = {
        "rotten_tomatoes_pct": cov("rt"),
        "metacritic": cov("mc"),
        "any_award_received": cov("awards"),
        "any_nomination": cov("noms"),
        "rt_or_mc": cov("rt", lambda m: m["rt"] is not None or m["mc"] is not None),
    }
    by_era: dict[str, str] = {}
    for lo, hi, label in ((0, 1999, "pre-2000"), (2000, 2019, "2000-2019"), (2020, 2100, "2020+")):
        era = [m for m in g7 if lo <= m["year"] <= hi]
        k = sum(1 for m in era if m["rt"] is not None or m["mc"] is not None)
        by_era[label] = f"{k}/{len(era)} ({k / len(era):.1%})"
    out["rt_or_mc_coverage_by_era"] = by_era

    with_mc = [m for m in g7 if m["mc"] is not None]
    with_rt = [m for m in g7 if m["rt"] is not None]
    out["spearman_vs_tmdb_wr"] = {
        "metacritic": round(
            spearman([m["mc"] for m in with_mc], [m["wr_tmdb"] for m in with_mc]), 3
        ),
        "rotten_tomatoes": round(
            spearman([m["rt"] for m in with_rt], [m["wr_tmdb"] for m in with_rt]), 3
        ),
        "imdb_rating (for comparison)": round(
            spearman(
                [m["imdb_rating"] for m in g7 if m["imdb_rating"]],
                [m["wr_tmdb"] for m in g7 if m["imdb_rating"]],
            ),
            3,
        ),
    }
    # Disagreement: critics love it, audiences lukewarm (and the reverse).
    mc_hi = statistics.quantiles([m["mc"] for m in with_mc], n=10)[8]
    wr_med = statistics.median(m["wr_tmdb"] for m in with_mc)
    out["critic_darlings_audience_lukewarm"] = {
        "rule": f"metacritic >= p90 ({mc_hi:.0f}) and TMDB WR < median ({wr_med:.2f})",
        "count": sum(1 for m in with_mc if m["mc"] >= mc_hi and m["wr_tmdb"] < wr_med),
        "examples": [
            f"{m['title']} ({m['year']}) MC {m['mc']:.0f}, TMDB {m['vote_average']}"
            for m in sorted(
                (m for m in with_mc if m["mc"] >= mc_hi and m["wr_tmdb"] < wr_med),
                key=lambda m: -m["popularity"],
            )[:5]
        ],
    }
    mc_lo = statistics.quantiles([m["mc"] for m in with_mc], n=10)[1]
    wr_hi = statistics.quantiles([m["wr_tmdb"] for m in with_mc], n=10)[7]
    out["crowd_pleasers_critics_rated_low"] = {
        "rule": f"metacritic <= p20 ({mc_lo:.0f}) and TMDB WR >= p80 ({wr_hi:.2f})",
        "count": sum(1 for m in with_mc if m["mc"] <= mc_lo and m["wr_tmdb"] >= wr_hi),
        "examples": [
            f"{m['title']} ({m['year']}) MC {m['mc']:.0f}, TMDB {m['vote_average']}"
            for m in sorted(
                (m for m in with_mc if m["mc"] <= mc_lo and m["wr_tmdb"] >= wr_hi),
                key=lambda m: -m["popularity"],
            )[:5]
        ],
    }
    (SPIKE_DIR / "critics_report.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
