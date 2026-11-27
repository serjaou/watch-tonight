"""feat-016 spike: the source downloads, as run inline on 2026-11-16 (review fix L6). THROWAWAY.

  1. Wikidata SPARQL: TMDB movie ID (P4947) -> IMDb ID (P345), CC0. One query, ~15 s,
     285,796 pairs on 2026-11-16 -> data/wikidata_tmdb_imdb.csv
  2. IMDb non-commercial dataset title.ratings.tsv.gz (measurement only; not committed, not for
     the product: see the licence finding in the spike doc) -> data/title.ratings.tsv.gz
     Git Bash curl failed on Windows (schannel CRYPT_E_NO_REVOCATION_CHECK), so Python is used.
  3. Snapshot of the crawled catalogue IDs for the churn follow-up (gitignored):
     catalog_ids_<date>.json.gz with {id: region letters} (B=BO, E=ES, U=US).

Run (needs data/catalog.jsonl from catalog.py for step 3):
  uv run --no-project --python 3.13 python spikes/16-recommendation/fetch_sources.py
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
DATA = SPIKE_DIR / "data"
UA = "watch-tonight-spike/0.1 (non-commercial portfolio project)"


def wikidata_mapping() -> None:
    q = "SELECT ?tmdb ?imdb WHERE { ?item wdt:P4947 ?tmdb ; wdt:P345 ?imdb . }"
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": q})
    req = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": UA})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"))))
    (DATA / "wikidata_tmdb_imdb.csv").write_bytes(body)
    print(f"wikidata: {len(rows) - 1} pairs in {time.perf_counter() - t:.1f}s")


def imdb_ratings() -> None:
    req = urllib.request.Request(
        "https://datasets.imdbws.com/title.ratings.tsv.gz", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
        modified = r.headers.get("Last-Modified")
    (DATA / "title.ratings.tsv.gz").write_bytes(data)
    rows = gzip.decompress(data).decode("utf-8").count("\n") - 1
    print(f"imdb: {rows} titles, {len(data)} bytes, Last-Modified {modified}")


def snapshot() -> None:
    text = (DATA / "catalog.jsonl").read_text("utf-8")
    rows = [json.loads(x) for x in text.split("\n") if x]
    now = datetime.now(UTC)
    snap = {
        "crawled_at": now.strftime("%Y-%m-%dT%H:%MZ"),
        "min_vote_count": 10,
        "ids": {str(m["id"]): "".join(sorted(r[0] for r in m["regions"])) for m in rows},
    }
    path = SPIKE_DIR / f"catalog_ids_{now:%Y-%m-%d}.json.gz"
    path.write_bytes(gzip.compress(json.dumps(snap, separators=(",", ":")).encode()))
    print(f"snapshot: {len(snap['ids'])} ids -> {path.name}")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    wikidata_mapping()
    imdb_ratings()
    snapshot()
