"""feat-011 spike: run the two online calls + the offline profile call against one provider/model.

THROWAWAY. Mirrors docs/architecture.md §3 with real data:
  understand (LLM) -> embed summary_en (fastembed bge-small, feat-010) -> top-K of the 200 real
  TMDB sample movies (spikes/10-embedding) -> step-4 stand-in (none) -> re-rank + pitch (LLM)
  -> step-6 deterministic checks (schemas.check_rerank), 1 retry.
Then profiles ~20 movies (offline call) for tokens-per-movie.

Run (PowerShell or Git Bash), one provider/model per run:
  uv run --no-project --python 3.13 --with openai --with google-genai --with fastembed \
      python spikes/11-llm/probe_llm.py --provider gemini --model gemini-3.5-flash-lite \
      --reasoning level:minimal --rounds 1 --min-interval 6
Writes spikes/11-llm/runs/<provider>__<model>__<tag>.jsonl (one JSON line per call).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

# Windows: the console defaults to cp1252, which can't print Japanese; files below are always
# opened with an explicit encoding for the same reason (Python's default is the locale's).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

import prompts  # noqa: E402
import schemas  # noqa: E402
from providers import DailyQuotaExceeded, StructuredCaller, make_backend  # noqa: E402

REPO_ROOT = SPIKE_DIR.parents[1]
MOVIES_PATH = REPO_ROOT / "spikes" / "10-embedding" / "sample_movies_200.json"
QUERIES_PATH = SPIKE_DIR / "queries.json"
RUNS_DIR = SPIKE_DIR / "runs"


class Retriever:
    """In-memory stand-in for `$vectorSearch` (no pre-filter: the sample has no availability)."""

    def __init__(self, movies: list[dict[str, Any]]) -> None:
        import numpy as np
        from fastembed import TextEmbedding

        self.np = np
        self.movies = movies
        self.model = TextEmbedding("BAAI/bge-small-en-v1.5")
        cache = (
            SPIKE_DIR / "cache" / "movie_vectors_bge_small.npy"
        )  # gitignored via cache/.gitignore
        if cache.exists():
            vecs = np.load(cache)
        else:
            vecs = np.array(list(self.model.embed([m["profile_text"] for m in movies])))
            cache.parent.mkdir(exist_ok=True)
            (cache.parent / ".gitignore").write_text("*\n", encoding="utf-8")
            np.save(cache, vecs)
        self.matrix = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def top_k(self, text: str, k: int) -> list[dict[str, Any]]:
        q = self.np.array(next(iter(self.model.query_embed(text))))
        q = q / self.np.linalg.norm(q)
        scores = self.matrix @ q
        order = self.np.argsort(-scores)[:k]
        return [self.movies[int(i)] for i in order]


def score_extraction(intent: schemas.Intent, expect: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out["runtime_ok"] = intent.max_runtime_minutes == expect["max_runtime_minutes"]
    want_avoid = set(expect["avoid_includes"])
    out["avoid_ok"] = want_avoid.issubset(set(intent.avoid))
    out["avoid_extra"] = sorted(set(intent.avoid) - want_avoid)
    mi = expect["max_intensity"]
    if mi == "any":
        out["intensity_ok"] = None
    elif mi == "low":
        out["intensity_ok"] = intent.max_intensity is not None and intent.max_intensity <= 3
    else:
        out["intensity_ok"] = intent.max_intensity == mi
    return out


def run_calls(
    args: argparse.Namespace,
    movies: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    caller: StructuredCaller,
    emit: Any,
) -> None:
    if not args.skip_online:
        t0 = time.perf_counter()
        retriever = Retriever(movies)
        print(f"[retriever] ready ({len(movies)} movies) in {time.perf_counter() - t0:.1f}s")
        for rnd in range(1, args.rounds + 1):
            for q in queries:
                und = caller.call(
                    "understand",
                    prompts.UNDERSTAND_SYSTEM,
                    prompts.understand_user(q["text"]),
                    schemas.Intent,
                    checks=schemas.check_intent,
                )
                rec: dict[str, Any] = {"record": "call", "round": rnd, "query_id": q["id"]}
                rec |= und.to_json()
                if und.ok:
                    rec["extraction"] = score_extraction(und.parsed, q["expect"])
                emit(rec)
                status = "ok" if und.ok else "FAIL"
                print(f"[r{rnd}] {q['id']} understand {status} ({len(und.attempts)} att)")
                if not und.ok:
                    continue

                intent: schemas.Intent = und.parsed
                candidates = retriever.top_k(intent.summary_en, args.top_k)
                cand_ids = {int(m["tmdb_id"]) for m in candidates}
                rr = caller.call(
                    "rerank",
                    prompts.RERANK_SYSTEM,
                    prompts.rerank_user(intent, candidates),
                    schemas.Rerank,
                    checks=lambda r, ids=cand_ids: schemas.check_rerank(r, ids),
                )
                rec = {"record": "call", "round": rnd, "query_id": q["id"]}
                rec |= rr.to_json()
                rec["candidate_count"] = len(candidates)
                if rr.ok:
                    titles = {int(m["tmdb_id"]): m["title"] for m in candidates}
                    rec["pitches"] = [
                        {
                            "tmdb_id": p.tmdb_id,
                            "title": titles.get(p.tmdb_id),
                            "chars": len(p.pitch),
                            "p2_flags": schemas.p2_flags(p.pitch),
                            "pitch": p.pitch,
                        }
                        for p in rr.parsed.picks
                    ]
                emit(rec)
                status = "ok" if rr.ok else "FAIL"
                print(f"[r{rnd}] {q['id']} rerank {status} ({len(rr.attempts)} att)")

    rng = random.Random(11)
    sample = rng.sample(movies, k=min(args.profiles, len(movies)))
    for m in sample:
        pr = caller.call(
            "profile",
            prompts.PROFILE_SYSTEM,
            prompts.profile_user(m),
            schemas.Profile,
            checks=schemas.check_profile,
        )
        rec = {"record": "call", "tmdb_id": m["tmdb_id"], "title": m["title"]}
        rec |= pr.to_json()
        emit(rec)
        print(f"[profile] {m['title']} {'ok' if pr.ok else 'FAIL'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=["openai", "gemini"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--reasoning", default=None, help="openai effort or gemini level:x/budget:n")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--queries", default="", help="comma-separated query ids (default all)")
    ap.add_argument("--profiles", type=int, default=20)
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--min-interval", type=float, default=0.0, help="seconds between calls")
    ap.add_argument("--skip-online", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    movies: list[dict[str, Any]] = json.loads(MOVIES_PATH.read_text(encoding="utf-8"))
    queries: list[dict[str, Any]] = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    if args.queries:
        wanted = set(args.queries.split(","))
        queries = [q for q in queries if q["id"] in wanted]

    backend = make_backend(args.provider, args.model, args.reasoning)
    caller = StructuredCaller(backend, min_interval_s=args.min_interval)

    RUNS_DIR.mkdir(exist_ok=True)
    tag = args.tag or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = RUNS_DIR / f"{args.provider}__{args.model}__{tag}.jsonl"
    meta = {
        "record": "meta",
        "started_at": datetime.now(UTC).isoformat(),
        "provider": args.provider,
        "model": args.model,
        "reasoning": args.reasoning,
        "prompt_version": prompts.PROMPT_VERSION,
        "top_k": args.top_k,
        "rounds": args.rounds,
        "platform": sys.platform,
    }

    with out_path.open("w", encoding="utf-8") as out:

        def emit(rec: dict[str, Any]) -> None:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()

        emit(meta)
        try:
            run_calls(args, movies, queries, caller, emit)
        except DailyQuotaExceeded as exc:
            emit({"record": "stopped", "reason": "daily_quota", "error": str(exc)})
            print(f"[stopped] daily quota exhausted: {str(exc)[:300]}")

    print(f"wrote {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
