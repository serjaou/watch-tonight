"""feat-016 spike Q2/Q3: enrich "Pool B" (300 stratified G7 movies) with the v1 profile.

THROWAWAY. Steps:
  1. sample 300 movies from G7: 5 eras x 3 quality terciles x 20 (seeded);
  2. fetch the TMDB bundle per movie (keywords, credits, release_dates, reviews);
  3. profile all 300 with gpt-6-luna from TMDB data only (variant "base");
  4. A/B on 50 well-known films: variant "reviews" adds up to 3 review excerpts (transient);
     a stronger model (gpt-6.1-terra) labels the same 50 from data + its own film knowledge as
     the reference.
TMDB terms: raw review text is used in memory only; only counts/lengths are written to disk.
Budget guard: stops when the estimated spend passes MAX_USD.

Run: uv run --no-project --python 3.13 --with openai python spikes/16-recommendation/enrich.py
Writes data/pool_b_movies.jsonl (gitignored TMDB rows), pool_b_profiles.jsonl (gitignored).
"""

from __future__ import annotations

import json
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
REPO = SPIKE_DIR.parents[1]
sys.path.insert(0, str(SPIKE_DIR))
sys.path.insert(0, str(REPO / "spikes" / "11-llm"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from embed_pool import load_g7  # noqa: E402
from providers import OpenAIBackend, StructuredCaller  # noqa: E402
from schemas_v1 import Profile  # noqa: E402
from tmdb import Tmdb  # noqa: E402

DATA = SPIKE_DIR / "data"
OUT = SPIKE_DIR / "pool_b_profiles.jsonl"
MAX_USD = 0.40
PRICES = {"gpt-6-luna": (0.10, 0.50), "gpt-6.1-terra": (1.00, 5.00)}  # USD per 1M in/out
ERAS = [(0, 1979), (1980, 1999), (2000, 2009), (2010, 2019), (2020, 2100)]

SYSTEM = """\
You write the emotional profile of a movie for a mood-based recommender.
Use the movie data given. You may use well-established knowledge about well-known films, but
never invent specifics you are unsure about, and never spoil the plot.

Fields:
- tone: 1 to 3 values from the allowed list.
- pacing: slow, medium or fast.
- intensity: 1 (very gentle) to 5 (very intense), emotional and visceral.
- viewing_effort: comfort_background (easy to half-watch), easy, engaging (needs attention),
  demanding (slow, complex or challenging).
- ending_feel: how the ending leaves viewers feeling, without revealing it.
- humor_style: none if humor is not a real part of the film.
- content_warnings: only values the data or the age certification clearly support.
- themes: 1 to 5 short English phrases.
- summary: at most 400 characters in English on what watching it feels like (atmosphere,
  emotional arc, pace). Not a plot summary, no spoilers."""

REFERENCE_SYSTEM = SYSTEM.replace(
    "You may use well-established knowledge about well-known films, but\n"
    "never invent specifics you are unsure about",
    "You are an experienced film critic: use your own knowledge of this film as the main\n"
    "source and the data only to identify it",
)

_lock = threading.Lock()
spent = {"usd": 0.0}


def cost(model: str, att: Any) -> float:
    pin, pout = PRICES[model]
    return att.input_tokens * pin / 1e6 + att.output_tokens * pout / 1e6


def us_certification(bundle: dict[str, Any]) -> str:
    for r in bundle.get("release_dates", {}).get("results", []):
        if r.get("iso_3166_1") == "US":
            certs = [d.get("certification") for d in r.get("release_dates", [])]
            certs = [c for c in certs if c]
            if certs:
                return certs[0]
    return ""


def fetch(api: Tmdb, mid: int) -> dict[str, Any]:
    b = api.get(
        f"/movie/{mid}",
        {"language": "en-US", "append_to_response": "keywords,credits,release_dates,reviews"},
    )
    reviews = [r.get("content", "") for r in b.get("reviews", {}).get("results", [])]
    crew = b.get("credits", {}).get("crew", [])
    return {
        "id": mid,
        "title": b.get("title"),
        "year": int((b.get("release_date") or "0")[:4] or 0),
        "runtime": b.get("runtime"),
        "genres": [g["name"] for g in b.get("genres", [])],
        "tagline": b.get("tagline") or "",
        "overview": b.get("overview") or "",
        "keywords": [
            k["name"]
            for k in b.get("keywords", {}).get("keywords", [])
            if "stinger" not in k["name"]
        ][:15],
        "directors": [c["name"] for c in crew if c.get("job") == "Director"][:2],
        "cast": [c["name"] for c in b.get("credits", {}).get("cast", [])[:5]],
        "collection_id": (b.get("belongs_to_collection") or {}).get("id"),
        "collection": (b.get("belongs_to_collection") or {}).get("name"),
        "certification_us": us_certification(b),
        "original_language": b.get("original_language"),
        "vote_average": b.get("vote_average"),
        "vote_count": b.get("vote_count"),
        "popularity": b.get("popularity"),
        "_reviews": reviews,  # in memory only; stripped before writing
    }


def movie_text(m: dict[str, Any], with_reviews: bool) -> str:
    lines = [
        f"Title: {m['title']} ({m['year']})",
        f"Runtime: {m['runtime']} min. Genres: {', '.join(m['genres'])}. "
        f"US certification: {m['certification_us'] or 'unknown'}.",
        f"Director: {', '.join(m['directors'])}. Cast: {', '.join(m['cast'])}.",
        f"Tagline: {m['tagline']}" if m["tagline"] else "",
        f"Overview: {m['overview']}",
        f"Keywords: {', '.join(m['keywords'])}",
    ]
    if with_reviews and m["_reviews"]:
        lines.append("Audience review excerpts (opinions; use for tone, pacing and ending feel):")
        for r in m["_reviews"][:3]:
            clean = re.sub(r"\s+", " ", r)[:500]
            lines.append(f"- {clean}")
    return "\n".join(x for x in lines if x)


def profile(caller: StructuredCaller, model: str, system: str, text: str) -> dict[str, Any]:
    with _lock:
        if spent["usd"] > MAX_USD:
            return {"error": "budget guard"}
    res = caller.call("profile", system, text, Profile)
    with _lock:
        for a in res.attempts:
            spent["usd"] += cost(model, a)
    att = res.attempts[-1] if res.attempts else None
    return {
        "profile": res.parsed.model_dump() if res.parsed else None,
        "input_tokens": sum(a.input_tokens for a in res.attempts),
        "output_tokens": sum(a.output_tokens for a in res.attempts),
        "error": "" if res.parsed else (att.error if att else "no attempt"),
    }


def sample_pool_b(g7: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(16)
    picked: list[dict[str, Any]] = []
    for lo, hi in ERAS:
        era = sorted((m for m in g7 if lo <= m["year"] <= hi), key=lambda m: m["wr_tmdb"])
        third = len(era) // 3
        for t in range(3):
            tier = era[t * third : (t + 1) * third if t < 2 else len(era)]
            picked += rng.sample(tier, k=min(20, len(tier)))
    return picked


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="smoke test: first N sampled movies")
    args = ap.parse_args()
    global OUT
    g7 = load_g7()
    sample = sample_pool_b(g7)
    if args.limit:
        sample = sample[-args.limit :]  # recent, well-voted end of the sample
        OUT = SPIKE_DIR / "data" / "smoke_profiles.jsonl"
    api = Tmdb()
    with ThreadPoolExecutor(max_workers=8) as pool:
        movies = list(pool.map(lambda m: fetch(api, m["id"]), sample))
    wr = {m["id"]: m["wr_tmdb"] for m in g7}
    for m in movies:
        m["wr_tmdb"] = wr[m["id"]]
    movies_path = DATA / ("smoke_movies.jsonl" if args.limit else "pool_b_movies.jsonl")
    with movies_path.open("w", encoding="utf-8") as f:
        for m in movies:
            row = {k: v for k, v in m.items() if k != "_reviews"}
            row["review_count"] = len(m["_reviews"])
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"fetched {len(movies)} bundles ({api.calls} TMDB calls)", flush=True)

    luna = StructuredCaller(OpenAIBackend("gpt-6-luna", "none"))
    terra = StructuredCaller(OpenAIBackend("gpt-6.1-terra", "none"))
    ab = sorted((m for m in movies if len(m["_reviews"]) >= 2), key=lambda m: -m["vote_count"])
    ab_ids = {m["id"] for m in ab[:50]}

    jobs: list[tuple[str, dict[str, Any]]] = [("base", m) for m in movies]
    jobs += [("reviews", m) for m in movies if m["id"] in ab_ids]
    jobs += [("reference", m) for m in movies if m["id"] in ab_ids]

    def run(job: tuple[str, dict[str, Any]]) -> dict[str, Any]:
        variant, m = job
        if variant == "reference":
            r = profile(terra, "gpt-6.1-terra", REFERENCE_SYSTEM, movie_text(m, False))
            model = "gpt-6.1-terra"
        else:
            r = profile(luna, "gpt-6-luna", SYSTEM, movie_text(m, variant == "reviews"))
            model = "gpt-6-luna"
        return {"id": m["id"], "title": m["title"], "year": m["year"], "variant": variant,
                "model": model, "review_count": len(m["_reviews"])} | r  # fmt: skip

    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(run, jobs))
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    errors = [r for r in rows if r["error"]]
    print(f"profiles: {len(rows)} rows, {len(errors)} errors, est. spend ${spent['usd']:.4f}")
    for r in errors[:5]:
        print("  error:", r["variant"], r["title"], r["error"][:200])


if __name__ == "__main__":
    main()
