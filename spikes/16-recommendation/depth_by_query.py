"""feat-016 spike Q4: retrieval depth per query (offline, no LLM). THROWAWAY.

Reuses the intents saved in rank_details.json and the Pool A vectors; recomputes the recall of
the hybrid top-25 within K in {25, 50, 100, 150, 200} vs within K=300, per query, plus the
deepest pure-vector rank the K=300 hybrid top-25 needs.

Run: uv run --no-project --python 3.13 --with openai --with fastembed python -W ignore \
       spikes/16-recommendation/depth_by_query.py   (writes depth_report.json)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
sys.path.insert(0, str(SPIKE_DIR.parents[1] / "spikes" / "11-llm"))

from rank_eval import cos_top, hybrid  # noqa: E402
from schemas_v1 import QueryIntent  # noqa: E402


def main() -> None:
    import numpy as np
    from fastembed import TextEmbedding

    data = SPIKE_DIR / "data"
    a = np.load(data / "pool_a.npy")
    a = a / np.linalg.norm(a, axis=1, keepdims=True)
    text = (data / "pool_a_meta.jsonl").read_text("utf-8")
    meta = [json.loads(x) for x in text.split("\n") if x]
    # Review fix L3: load the critic score like rank_eval.py does, so the "critically
    # acclaimed" query is re-scored with the documented critic blend.
    import corpus
    from critics import metacritic, pct

    sig = json.loads((data / "wikidata_signals.json").read_text("utf-8"))
    imdb_of = {m["id"]: m["imdb_id"] for m in corpus.load() if m["imdb_id"]}
    for m in meta:
        s = sig.get(imdb_of.get(m["id"], ""), {})
        mc, rt = metacritic(s.get("mc", [])), pct(s.get("rt", []))
        m["critic"] = mc if mc is not None else rt
    max_logpop = max(math.log1p(m["popularity"]) for m in meta)
    details = json.loads((SPIKE_DIR / "rank_details.json").read_text("utf-8"))
    emb = TextEmbedding("BAAI/bge-small-en-v1.5")
    rows: list[dict[str, Any]] = []
    for d in details:
        it = QueryIntent(**d["intent"])
        idx = [
            i
            for i, m in enumerate(meta)
            if (it.year_min is None or m["year"] >= it.year_min)
            and (it.year_max is None or m["year"] <= it.year_max)
            and (not it.original_languages or m["original_language"] in it.original_languages)
        ]
        q = np.array(next(iter(emb.query_embed(it.semantic_description))), dtype=np.float32)
        q = q / np.linalg.norm(q)
        deep = cos_top(a, q, idx, 300)
        ref = [i for i, _ in hybrid(deep, meta, it, max_logpop)[:25]]
        rank_of = {i: r for r, (i, _) in enumerate(deep)}
        row: dict[str, Any] = {
            "query": d["query"][:60],
            "specificity": it.specificity,
            "pool": len(idx),
            "deepest_vector_rank_in_hybrid_top25": max(rank_of[i] for i in ref) + 1,
        }
        for k in (25, 50, 100, 150, 200):
            got = [i for i, _ in hybrid(deep[:k], meta, it, max_logpop)[:25]]
            row[f"recall@K{k}"] = round(len(set(got) & set(ref)) / len(ref), 2)
        rows.append(row)
        print(row)
    by_spec: dict[str, Any] = {}
    for spec in ("broad", "medium", "specific"):
        sel = [r for r in rows if r["specificity"] == spec]
        if sel:
            by_spec[spec] = {
                f"K{k}": round(sum(r[f"recall@K{k}"] for r in sel) / len(sel), 3)
                for k in (25, 50, 100, 150, 200)
            } | {"n": len(sel)}
    out = {"per_query": rows, "mean_recall_by_specificity": by_spec}
    (SPIKE_DIR / "depth_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(by_spec, indent=2))


if __name__ == "__main__":
    main()
