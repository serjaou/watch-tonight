"""feat-016 spike, review round 1 follow-ups (TMDB only, no LLM). THROWAWAY.

M1  franchise duplicates in the Pool A top-25 lists (baseline and hybrid): how many slots a
    "one film per `belongs_to_collection`" rule would free (dedupe itself not re-run);
M4  age-certification coverage on Pool B (US, ES, either) and how many films a kids filter
    keeps under three rules: US only, US else ES, US else ES else profile fallback;
L5  value distribution of the 300 base profiles.

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/followups.py
Writes followups_report.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from tmdb import Tmdb  # noqa: E402

US_KIDS = {"G", "PG"}
ES_KIDS = {"A", "Ai", "7", "7i"}  # from TMDB /certification/movie/list (ES), see report
ADULT_WARNINGS = {
    "violence", "gore", "sexual_content", "nudity", "sexual_violence", "horror_scares",
    "drug_use", "strong_language",
}  # fmt: skip


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text("utf-8").split("\n") if x]


def cert(bundle: dict[str, Any], country: str) -> str:
    for r in bundle.get("release_dates", {}).get("results", []):
        if r.get("iso_3166_1") == country:
            for d in r.get("release_dates", []):
                c = (d.get("certification") or "").strip()
                if c and c.upper() != "NR":
                    return c
    return ""


def main() -> None:
    api = Tmdb()
    out: dict[str, Any] = {}
    es_list = api.get("/certification/movie/list").get("certifications", {}).get("ES", [])
    out["tmdb_es_certifications"] = [f"{c['certification']}: {c['meaning'][:60]}" for c in es_list]

    # --- M1: franchise duplicates -------------------------------------------------------------
    details = json.loads((SPIKE_DIR / "rank_details.json").read_text("utf-8"))
    ids = sorted({i for d in details for k in ("A_base", "A_hybrid") for i in d[k]})
    with ThreadPoolExecutor(max_workers=8) as pool:
        bundles = list(pool.map(lambda i: api.get(f"/movie/{i}"), ids))
    coll = {
        i: (b.get("belongs_to_collection") or {}).get("id")
        for i, b in zip(ids, bundles, strict=True)
    }

    def dupes(lst: list[int]) -> int:
        c = Counter(coll[i] for i in lst if coll[i])
        return sum(n - 1 for n in c.values() if n > 1)

    m1: dict[str, Any] = {
        "movies_checked": len(ids),
        "with_collection": sum(1 for v in coll.values() if v),
    }
    for key in ("A_base", "A_hybrid"):
        m1[key] = {
            "duplicate_slots_top25": sum(dupes(d[key][:25]) for d in details),
            "duplicate_slots_top5": sum(dupes(d[key][:5]) for d in details),
            "queries_with_dupes_top25": sum(1 for d in details if dupes(d[key][:25])),
        }
    m1["examples"] = []
    for d in details:
        c = Counter(coll[i] for i in d["A_hybrid"][:25] if coll[i])
        for cid, n in c.items():
            if n > 1:
                names = [b.get("title") for i, b in zip(ids, bundles, strict=True)
                         if coll[i] == cid and i in d["A_hybrid"][:25]]  # fmt: skip
                m1["examples"].append(f"{d['query'][:40]}: {names}")
    out["M1_franchise_duplicates"] = m1

    # --- M4: certification coverage on Pool B ---------------------------------------------------
    movies = lines(SPIKE_DIR / "data" / "pool_b_movies.jsonl")
    with ThreadPoolExecutor(max_workers=8) as pool:
        rd = list(pool.map(lambda m: api.get(f"/movie/{m['id']}/release_dates"), movies))
    prof = {
        r["id"]: r["profile"]
        for r in lines(SPIKE_DIR / "pool_b_profiles.jsonl")
        if r["variant"] == "base" and r["profile"]
    }
    rows = []
    for m, b in zip(movies, rd, strict=True):
        us = cert({"release_dates": b}, "US")
        es = cert({"release_dates": b}, "ES")
        p = prof.get(m["id"], {})
        gentle = p.get("intensity", 5) <= 2 and not ADULT_WARNINGS & set(
            p.get("content_warnings", [])
        )
        rows.append({"us": us, "es": es, "en": m["original_language"] == "en", "gentle": gentle})
    n = len(rows)

    def share(f: Any) -> str:
        k = sum(1 for r in rows if f(r))
        return f"{k}/{n} ({k / n:.0%})"

    out["M4_certification"] = {
        "us_usable (not empty, not NR)": share(lambda r: r["us"]),
        "es_usable": share(lambda r: r["es"]),
        "us_or_es": share(lambda r: r["us"] or r["es"]),
        "neither": share(lambda r: not (r["us"] or r["es"])),
        "us_usable_non_english": share(lambda r: r["us"] and not r["en"]),
        "non_english_total": share(lambda r: not r["en"]),
        "kids_kept_us_only": share(lambda r: r["us"] in US_KIDS),
        "kids_kept_us_else_es": share(
            lambda r: r["us"] in US_KIDS or (not r["us"] and r["es"] in ES_KIDS)
        ),
        "kids_kept_us_else_es_else_gentle_profile": share(
            lambda r: (
                r["us"] in US_KIDS
                or (not r["us"] and r["es"] in ES_KIDS)
                or (not r["us"] and not r["es"] and r["gentle"])
            )
        ),
    }

    # --- L5: profile value distribution ---------------------------------------------------------
    dist: dict[str, Any] = {}
    for f in ("pacing", "viewing_effort", "ending_feel", "humor_style", "intensity"):
        dist[f] = dict(Counter(str(p[f]) for p in prof.values()).most_common())
    dist["tone"] = dict(Counter(t for p in prof.values() for t in p["tone"]).most_common())
    dist["content_warnings"] = dict(
        Counter(w for p in prof.values() for w in p["content_warnings"]).most_common()
    )
    out["L5_profile_distribution"] = dist
    out["tmdb_calls"] = api.calls
    (SPIKE_DIR / "followups_report.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
