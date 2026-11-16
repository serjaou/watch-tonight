"""feat-016 spike Q2: critic and award signals from Wikidata (CC0), keyed by IMDb ID. THROWAWAY.

For every catalogue movie with tmdb vote_count >= 20 and a Wikidata IMDb mapping, fetches:
  - Rotten Tomatoes score (P444 review score, qualifier P447 = Q105584), values like "93%";
  - Metacritic score (P444, P447 = Q150248), values like "73/100";
  - awards received (P166) and award nominations (P1411), counted.
Sequential batches of 300 IDs against query.wikidata.org (polite: one request at a time).

Run: uv run --no-project --python 3.13 python spikes/16-recommendation/wikidata_signals.py
Writes data/wikidata_signals.json (gitignored).
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
DATA = SPIKE_DIR / "data"
ENDPOINT = "https://query.wikidata.org/sparql"
UA = "watch-tonight-spike/0.1 (non-commercial portfolio project)"
BATCH = 300

QUERY = """
SELECT ?imdb
  (GROUP_CONCAT(DISTINCT ?rt; separator="|") AS ?rts)
  (GROUP_CONCAT(DISTINCT ?mc; separator="|") AS ?mcs)
  (COUNT(DISTINCT ?award) AS ?awards)
  (COUNT(DISTINCT ?nom) AS ?noms)
WHERE {
  VALUES ?imdb { %s }
  ?item wdt:P345 ?imdb .
  OPTIONAL { ?item p:P444 ?s1 . ?s1 ps:P444 ?rt ; pq:P447 wd:Q105584 . }
  OPTIONAL { ?item p:P444 ?s2 . ?s2 ps:P444 ?mc ; pq:P447 wd:Q150248 . }
  OPTIONAL { ?item wdt:P166 ?award . }
  OPTIONAL { ?item wdt:P1411 ?nom . }
}
GROUP BY ?imdb
"""


def run(ids: list[str]) -> list[dict[str, Any]]:
    values = " ".join(f'"{i}"' for i in ids)
    body = urllib.parse.urlencode({"query": QUERY % values}).encode()
    for attempt in range(4):
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={"Accept": "application/sparql-results+json", "User-Agent": UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))["results"]["bindings"]
        except Exception as exc:  # 429/timeouts: back off and retry
            print(f"  retry {attempt + 1}: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
            time.sleep(10 * (attempt + 1))
    return []


def main() -> None:
    text = (DATA / "catalog.jsonl").read_text("utf-8")
    movies = [json.loads(x) for x in text.split("\n") if x]  # not splitlines(): U+2028 in data
    # Review fix L2: G7 admits recent films from 20 votes, so query from 20 (was 50). Rows
    # already fetched are kept and only missing IDs are queried.
    wanted = {m["id"] for m in movies if (m.get("vote_count") or 0) >= 20}
    ids: list[str] = []
    with (DATA / "wikidata_tmdb_imdb.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["tmdb"].isdigit() and int(row["tmdb"]) in wanted:
                ids.append(row["imdb"])
    out_path = DATA / "wikidata_signals.json"
    out: dict[str, Any] = json.loads(out_path.read_text("utf-8")) if out_path.exists() else {}
    ids = sorted(set(ids) - set(out))
    print(f"{len(ids)} IMDb IDs to query in {-(-len(ids) // BATCH)} batches", flush=True)
    t0 = time.perf_counter()
    for i in range(0, len(ids), BATCH):
        for b in run(ids[i : i + BATCH]):
            out[b["imdb"]["value"]] = {
                "rt": [v for v in b.get("rts", {}).get("value", "").split("|") if v],
                "mc": [v for v in b.get("mcs", {}).get("value", "").split("|") if v],
                "awards": int(b["awards"]["value"]),
                "noms": int(b["noms"]["value"]),
            }
        if (i // BATCH) % 10 == 0:
            print(f"  batch {i // BATCH + 1}: {len(out)} rows, {time.perf_counter() - t0:.0f}s")
        time.sleep(1.0)
    out_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"done: {len(out)} rows in {time.perf_counter() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
