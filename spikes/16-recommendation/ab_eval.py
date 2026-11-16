"""feat-016 spike Q2: do transient TMDB reviews improve the profile? THROWAWAY.

Compares, on the 50 A/B films, gpt-6-luna "base" (TMDB data only) and "reviews" (+ up to 3
review excerpts) against the "reference" (gpt-6.1-terra from data + its own film knowledge).
Enums: exact match. intensity: exact and within 1. Lists (tone, content_warnings): Jaccard.
Also the token cost of adding reviews.

Run: uv run --no-project python spikes/16-recommendation/ab_eval.py   (writes ab_report.json)
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
ENUMS = ("pacing", "viewing_effort", "ending_feel", "humor_style")
LISTS = ("tone", "content_warnings")
Trio = dict[str, Any]


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return 1.0 if not sa and not sb else len(sa & sb) / len(sa | sb)


def agreement(trios: list[Trio], variant: str, fn: Callable[[Any, Any], float]) -> float:
    """Mean of fn(variant profile, reference profile) over the compared films."""
    return round(
        statistics.mean(fn(t[variant]["profile"], t["reference"]["profile"]) for t in trios), 3
    )


def main() -> None:
    text = (SPIKE_DIR / "pool_b_profiles.jsonl").read_text("utf-8")
    rows = [json.loads(x) for x in text.split("\n") if x]
    by: dict[int, Trio] = defaultdict(dict)
    for r in rows:
        by[r["id"]][r["variant"]] = r
    variants = ("base", "reviews", "reference")
    trios = [v for v in by.values() if all(v.get(k, {}).get("profile") for k in variants)]
    out: dict[str, Any] = {"films_compared": len(trios)}
    for variant in ("base", "reviews"):
        res: dict[str, Any] = {}
        for f in ENUMS:
            res[f] = agreement(trios, variant, lambda a, b, f=f: float(a[f] == b[f]))
        res["intensity_exact"] = agreement(
            trios, variant, lambda a, b: float(a["intensity"] == b["intensity"])
        )
        res["intensity_within_1"] = agreement(
            trios, variant, lambda a, b: float(abs(a["intensity"] - b["intensity"]) <= 1)
        )
        for f in LISTS:
            res[f"{f}_jaccard"] = agreement(trios, variant, lambda a, b, f=f: jaccard(a[f], b[f]))
        res["mean_input_tokens"] = round(statistics.mean(t[variant]["input_tokens"] for t in trios))
        res["mean_output_tokens"] = round(
            statistics.mean(t[variant]["output_tokens"] for t in trios)
        )
        out[variant] = res

    def ending(t: Trio, variant: str) -> str:
        return t[variant]["profile"]["ending_feel"]

    # Where do base and reviews disagree on ending_feel, and which one matches the reference?
    diff = [t for t in trios if ending(t, "base") != ending(t, "reviews")]
    out["ending_feel_changed_by_reviews"] = {
        "count": len(diff),
        "reviews_matches_reference": sum(
            ending(t, "reviews") == ending(t, "reference") for t in diff
        ),
        "base_matches_reference": sum(ending(t, "base") == ending(t, "reference") for t in diff),
        "examples": [
            f"{t['base']['title']}: base={ending(t, 'base')}, reviews={ending(t, 'reviews')}, "
            f"ref={ending(t, 'reference')}"
            for t in diff[:6]
        ],
    }
    (SPIKE_DIR / "ab_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
