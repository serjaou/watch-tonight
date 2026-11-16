"""feat-011 spike: summarise runs/*.jsonl into report.json (+ a console table).

Run: uv run --no-project python spikes/11-llm/summarize.py
Prices come from prices.json (USD per 1M tokens; sources and dates in the spike doc).
Billing note: OpenAI's completion_tokens already include reasoning tokens; Gemini's
candidates_token_count excludes thoughts, which are billed as output, so they are added.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
RUNS_DIR = SPIKE_DIR / "runs"
PRICES_PATH = SPIKE_DIR / "prices.json"
REPORT_PATH = SPIKE_DIR / "report.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    # Nearest-rank percentile: rank = ceil(q * n). (Review fix: the first version used round(),
    # which rounds half to even and picked one rank too high, e.g. the max as p95 for n = 20.)
    idx = max(0, min(len(s) - 1, math.ceil(q * len(s)) - 1))
    return round(s[idx], 1)


def raised(att: dict[str, Any]) -> bool:
    return bool(att.get("raised")) or att["latency_ms"] == 0


def billed_output(provider: str, att: dict[str, Any]) -> int:
    out = int(att["output_tokens"])
    return out + int(att["reasoning_tokens"]) if provider == "gemini" else out


def summarise_kind(calls: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(calls)
    first_ok = sum(1 for c in calls if c["attempts"] and c["attempts"][0]["ok"])
    final_ok = sum(1 for c in calls if c["parsed"] is not None)
    lat_first = [c["attempts"][0]["latency_ms"] for c in calls if c["attempts"][0]["ok"]]
    lat_total = [sum(a["latency_ms"] for a in c["attempts"]) for c in calls if c["parsed"]]
    atts = [a for c in calls for a in c["attempts"] if not raised(a)]
    provider = calls[0]["provider"] if calls else ""
    errors = [a["error"][:160] for c in calls for a in c["attempts"] if a["error"]]
    return {
        "calls": n,
        "valid_first_try": f"{first_ok}/{n}",
        "valid_after_retry": f"{final_ok}/{n}",
        "attempts_total": sum(len(c["attempts"]) for c in calls),
        "attempts_raised_api_error": sum(raised(a) for c in calls for a in c["attempts"]),
        "attempts_failed_checks": sum(
            (not raised(a)) and bool(a["error"]) for c in calls for a in c["attempts"]
        ),
        "rate_limited_waits": sum(c.get("rate_limited", 0) for c in calls),
        "latency_ms_first_ok": {
            "n": len(lat_first),
            "p50": pct(lat_first, 0.5),
            "p95": pct(lat_first, 0.95),
        },
        # bench1 logged raised attempts as 0 ms, so for those runs this excludes failed round trips
        "latency_ms_incl_retries": {
            "n": len(lat_total),
            "p50": pct(lat_total, 0.5),
            "p95": pct(lat_total, 0.95),
        },
        "avg_input_tokens_per_attempt": round(statistics.mean(a["input_tokens"] for a in atts))
        if atts
        else None,
        "avg_billed_output_tokens_per_attempt": round(
            statistics.mean(billed_output(provider, a) for a in atts)
        )
        if atts
        else None,
        "avg_reasoning_tokens_per_attempt": round(
            statistics.mean(a["reasoning_tokens"] for a in atts)
        )
        if atts
        else None,
        "attempts_per_call": round(len(atts) / n, 2) if n else None,
        "errors": errors[:8],
    }


def cost_usd(provider: str, calls: list[dict[str, Any]], price: dict[str, float]) -> float:
    total = 0.0
    for c in calls:
        for a in c["attempts"]:
            total += a["input_tokens"] * price["input"] / 1e6
            total += billed_output(provider, a) * price["output"] / 1e6
    return total


def mean_cost_per_call(
    provider: str, calls: list[dict[str, Any]], price: dict[str, float]
) -> float | None:
    """Mean cost of the calls that got a response (retries included in their call).

    Review fix: dividing by every call (incl. ones that never reached the model, or queries
    whose understand step failed so no re-rank ran) understated Gemini's cost.
    """
    billed = [c for c in calls if any(not raised(a) for a in c["attempts"])]
    if not billed:
        return None
    return cost_usd(provider, billed, price) / len(billed)


def main() -> None:
    prices: dict[str, dict[str, float]] = {}
    if PRICES_PATH.exists():
        prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))["per_1m_tokens_usd"]

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    metas: dict[str, dict[str, Any]] = {}
    for path in sorted(RUNS_DIR.glob("*.jsonl")):
        if "__smoke" in path.name:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec["record"] == "meta":
                key = f"{rec['provider']}:{rec['model']}:{rec['reasoning']}"
                metas[key] = rec
                continue
            if rec["record"] != "call":
                metas.setdefault(key, {})["stopped"] = rec.get("error", "")[:500]
                continue
            groups[key].append(rec)

    report: dict[str, Any] = {}
    for key, recs in groups.items():
        provider, model = key.split(":")[0], key.split(":")[1]
        by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in recs:
            by_kind[r["kind"]].append(r)
        entry: dict[str, Any] = {k: summarise_kind(v) for k, v in by_kind.items()}

        und = [r for r in by_kind.get("understand", []) if r.get("extraction")]
        if und:
            ext = [r["extraction"] for r in und]
            non_en = [r["extraction"] for r in und if r["query_id"].split("-")[1] != "en"]
            scored = [r["extraction"] for r in und if r["extraction"]["intensity_ok"] is not None]

            def ratio(rows: list[dict[str, Any]], ok: Any) -> str:
                return f"{sum(bool(ok(e)) for e in rows)}/{len(rows)}"

            def exact(e: dict[str, Any]) -> bool:
                return e["runtime_ok"] and e["avoid_ok"] and not e["avoid_extra"]

            entry["extraction"] = {
                "runtime_ok": ratio(ext, lambda e: e["runtime_ok"]),
                "avoid_includes_expected": ratio(ext, lambda e: e["avoid_ok"]),
                "avoid_exact_no_extras": ratio(
                    ext, lambda e: e["avoid_ok"] and not e["avoid_extra"]
                ),
                # q01/q04 expect a low cap, q05 ("anything") expects null
                "intensity_ok": ratio(scored, lambda e: e["intensity_ok"]),
                "intensity_scored_on": sorted(
                    {r["query_id"] for r in und if r["extraction"]["intensity_ok"] is not None}
                ),
                "non_english_runtime_and_avoid_ok": ratio(
                    non_en, lambda e: e["runtime_ok"] and e["avoid_ok"]
                ),
                "non_english_exact_no_extras": ratio(non_en, exact),
                "avoid_extras_seen": sorted({x for e in ext for x in e["avoid_extra"]}),
            }

        rr = [r for r in by_kind.get("rerank", []) if r.get("pitches")]
        if rr:
            pitches = [p for r in rr for p in r["pitches"]]
            entry["pitches"] = {
                "count": len(pitches),
                "chars_mean": round(statistics.mean(p["chars"] for p in pitches)),
                "chars_max": max(p["chars"] for p in pitches),
                "over_350": sum(p["chars"] > 350 for p in pitches),
                "p2_flagged": sum(bool(p["p2_flags"]) for p in pitches),
                "p2_flag_words": sorted({w for p in pitches for w in p["p2_flags"]}),
            }

        # End-to-end LLM time per query = understand + rerank (incl. retries), same round/query.
        pairs: dict[tuple[int, str], float] = defaultdict(float)
        complete: dict[tuple[int, str], int] = defaultdict(int)
        for r in by_kind.get("understand", []) + by_kind.get("rerank", []):
            if r["parsed"] is not None:
                k = (r["round"], r["query_id"])
                pairs[k] += sum(a["latency_ms"] for a in r["attempts"])
                complete[k] += 1
        e2e = [v for k, v in pairs.items() if complete[k] == 2]
        entry["llm_time_per_query_ms"] = {
            "n": len(e2e),
            "p50": pct(e2e, 0.5),
            "p95": pct(e2e, 0.95),
        }

        price = prices.get(model)
        if price:
            und_cost = mean_cost_per_call(provider, by_kind.get("understand", []), price)
            rr_cost = mean_cost_per_call(provider, by_kind.get("rerank", []), price)
            prof_cost = mean_cost_per_call(provider, by_kind.get("profile", []), price)
            per_query = und_cost + rr_cost if und_cost and rr_cost else None
            entry["cost_usd"] = {
                "price_per_1m": price,
                "per_query": round(per_query, 6) if per_query else None,
                "per_1000_queries": round(per_query * 1000, 3) if per_query else None,
                "per_1000_profiles": round(prof_cost * 1000, 4) if prof_cost else None,
                "spent_in_this_run": round(cost_usd(provider, recs, price), 4),
            }
        entry["meta"] = metas.get(key, {})
        report[key] = entry

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for key, entry in report.items():
        print(f"\n=== {key}")
        for kind in ("understand", "rerank", "profile"):
            if kind in entry:
                e = entry[kind]
                lat = e["latency_ms_first_ok"]
                tokens_in = e["avg_input_tokens_per_attempt"]
                tokens_out = e["avg_billed_output_tokens_per_attempt"]
                print(
                    f"  {kind:10} valid {e['valid_first_try']} -> {e['valid_after_retry']}"
                    f"  p50/p95 {lat['p50']}/{lat['p95']} ms"
                    f"  in/out {tokens_in}/{tokens_out}"
                    f"  429-waits {e['rate_limited_waits']}"
                )
        for extra in ("extraction", "pitches", "llm_time_per_query_ms", "cost_usd"):
            if extra in entry:
                print(f"  {extra}: {json.dumps(entry[extra], ensure_ascii=False)}")
    print(f"\nwrote {REPORT_PATH.name}")


if __name__ == "__main__":
    main()
