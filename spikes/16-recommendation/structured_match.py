"""feat-016 spike Q3/Q4: does matching intent fields against profile fields help? THROWAWAY.

On Pool B (300 enriched movies), channel-1 filters applied, compare top-5 from:
  - "embedding": cosine(semantic_description, template(profile)) only;
  - "embedding+match": 0.6 * normalised cosine + 0.4 * field match, where field match is the
    mean over the intent fields that are set: tone (Jaccard), pacing, viewing_effort (exact 1,
    neighbour 0.5), ending_feel, humor_style.
One blind judge call per query over the union of both top-5s (gpt-6-luna).

Run: uv run --no-project --python 3.13 --with openai --with fastembed python -W ignore \
       spikes/16-recommendation/structured_match.py   (writes match_report.json)
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
sys.path.insert(0, str(SPIKE_DIR.parents[1] / "spikes" / "11-llm"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from providers import OpenAIBackend, StructuredCaller  # noqa: E402
from rank_eval import judge  # noqa: E402
from schemas_v1 import Profile, QueryIntent, profile_text  # noqa: E402

EFFORT = ["comfort_background", "easy", "engaging", "demanding"]


def field_match(it: QueryIntent, p: Profile) -> float | None:
    parts: list[float] = []
    if it.tone:
        a, b = set(it.tone), set(p.tone)
        parts.append(len(a & b) / len(a | b))
    if it.pacing:
        parts.append(float(it.pacing == p.pacing))
    if it.viewing_effort:
        gap = abs(EFFORT.index(it.viewing_effort) - EFFORT.index(p.viewing_effort))
        parts.append(1.0 if gap == 0 else 0.5 if gap == 1 else 0.0)
    if it.ending_feel:
        parts.append(float(it.ending_feel == p.ending_feel))
    if it.humor_style:
        parts.append(float(it.humor_style == p.humor_style))
    return statistics.mean(parts) if parts else None


def passes(it: QueryIntent, m: dict[str, Any]) -> bool:
    p: Profile = m["profile"]
    if it.max_runtime_minutes and (m["runtime"] or 999) > it.max_runtime_minutes:
        return False
    if it.max_intensity and p.intensity > it.max_intensity:
        return False
    if set(it.avoid) & set(p.content_warnings):
        return False
    if it.year_min and m["year"] < it.year_min:
        return False
    if it.year_max and m["year"] > it.year_max:
        return False
    if it.audience == "kids" and m["certification_us"] not in {"G", "PG"}:
        return False
    if it.audience == "teens" and m["certification_us"] not in {"G", "PG", "PG-13"}:
        return False
    return not (it.original_languages and m["original_language"] not in it.original_languages)


def main() -> None:
    import numpy as np
    from fastembed import TextEmbedding

    data = SPIKE_DIR / "data"
    movies = [
        json.loads(x) for x in (data / "pool_b_movies.jsonl").read_text("utf-8").split("\n") if x
    ]
    prof: dict[int, Profile] = {}
    for x in (SPIKE_DIR / "pool_b_profiles.jsonl").read_text("utf-8").split("\n"):
        if x and (r := json.loads(x))["variant"] == "base" and r["profile"]:
            prof[r["id"]] = Profile(**r["profile"])
    movies = [m | {"profile": prof[m["id"]]} for m in movies if m["id"] in prof]
    emb = TextEmbedding("BAAI/bge-small-en-v1.5")
    mv = np.array(list(emb.embed([profile_text(m["profile"]) for m in movies])), dtype=np.float32)
    mv = mv / np.linalg.norm(mv, axis=1, keepdims=True)
    details = json.loads((SPIKE_DIR / "rank_details.json").read_text("utf-8"))
    luna = StructuredCaller(OpenAIBackend("gpt-6-luna", "none"))
    spend = {"in": 0, "out": 0}

    def track(res: Any) -> Any:
        for a in res.attempts:
            spend["in"] += a.input_tokens
            spend["out"] += a.output_tokens
        return res

    rng = random.Random(16)
    rows: list[dict[str, Any]] = []
    for d in details:
        it = QueryIntent(**d["intent"])
        keep = [i for i, m in enumerate(movies) if passes(it, m)]
        q = np.array(next(iter(emb.query_embed(it.semantic_description))), dtype=np.float32)
        q = q / np.linalg.norm(q)
        sims = {i: float(mv[i] @ q) for i in keep}
        lo, hi = min(sims.values()), max(sims.values())
        emb_top = sorted(keep, key=lambda i: -sims[i])[:5]

        def score(
            i: int, sims: dict[int, float] = sims, lo: float = lo, hi: float = hi,
            it: QueryIntent = it,
        ) -> float:  # fmt: skip
            s = (sims[i] - lo) / (hi - lo) if hi > lo else 1.0
            fm = field_match(it, movies[i]["profile"])
            return s if fm is None else 0.6 * s + 0.4 * fm

        match_top = sorted(keep, key=lambda i: -score(i))[:5]
        shown = [movies[i] for i in dict.fromkeys(emb_top + match_top)]
        rng.shuffle(shown)
        rel = judge(luna, d["query"], shown, track)
        rows.append({
            "query": d["query"][:60],
            "fields_set": [f for f in ("tone", "pacing", "viewing_effort", "ending_feel",
                                       "humor_style") if getattr(it, f)],
            "embedding": [(movies[i]["title"], rel.get(movies[i]["id"])) for i in emb_top],
            "embedding+match": [(movies[i]["title"], rel.get(movies[i]["id"])) for i in match_top],
        })  # fmt: skip

    def mean_rel(key: str) -> float:
        vals = [r for row in rows for _, r in row[key] if r is not None]
        return round(statistics.mean(vals), 3)

    out = {
        "relevance_at5": {k: mean_rel(k) for k in ("embedding", "embedding+match")},
        "queries_with_any_field_set": sum(1 for r in rows if r["fields_set"]),
        "llm_tokens": spend,
        "per_query": rows,
    }
    (SPIKE_DIR / "match_report.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in out.items() if k != "per_query"}, indent=2))
    for r in rows[:3]:
        print(r["query"], "|", r["fields_set"])
        print("   emb  :", r["embedding"])
        print("   match:", r["embedding+match"])


if __name__ == "__main__":
    main()
