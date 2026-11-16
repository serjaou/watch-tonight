"""feat-016 spike Q1 follow-up: catalogue churn between two crawls. THROWAWAY.

Compares the committed snapshot catalog_ids_2026-11-16.json.gz with a fresh crawl
(data/catalog.jsonl, re-run catalog.py first, >= 24 h later): how many movies left flat-rate
in every launch country combined (candidates for `streamable: []`), how many arrived, per day.
Note: catalog.py overwrites the committed catalog_stats.json (keep the 2026-11-16 copy).

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/catalog.py
     uv run --no-project --python 3.13 python spikes/16-recommendation/churn.py
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent


def main() -> None:
    old = json.loads(gzip.decompress((SPIKE_DIR / "catalog_ids_2026-11-16.json.gz").read_bytes()))
    text = (SPIKE_DIR / "data" / "catalog.jsonl").read_text("utf-8")
    new = {str(m["id"]) for m in (json.loads(x) for x in text.split("\n") if x)}
    then = datetime.fromisoformat(old["crawled_at"].replace("Z", "+00:00"))
    # Review fix: measure to the new crawl's own timestamp (catalog_stats.json), not to now().
    stats = json.loads((SPIKE_DIR / "catalog_stats.json").read_text("utf-8"))
    crawled = datetime.fromisoformat(stats.get("checked_at", datetime.now(UTC).isoformat()))
    days = max((crawled - then).total_seconds() / 86400, 1e-9)
    gone = set(old["ids"]) - new
    came = new - set(old["ids"])
    out = {
        "days_between_crawls": round(days, 2),
        "old": len(old["ids"]),
        "new": len(new),
        "left_all_launch_countries": len(gone),
        "left_per_day": round(len(gone) / days, 1),
        "arrived": len(came),
        "arrived_per_day": round(len(came) / days, 1),
        "note": "vote_count>=10 crawl; movies crossing the 10-vote line also show up as arrivals",
    }
    (SPIKE_DIR / "churn_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
