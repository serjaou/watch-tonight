"""Seed local Atlas with spike 16's 300 films (walking skeleton, part 2, feat-030).

    uv run poe db-up     # start local Atlas (compose.yaml)
    uv run poe seed      # this script

It fetches each film's TMDB bundle (about 300 calls; raw TMDB data is never written to
disk), joins it with the local spike-16 profile (a gitignored file), gives it a fake
vector (the real embedder is part 3, feat-028), and upserts it. It refuses any database
that isn't on this machine unless given `--allow-remote` (owner, 2026-11-25). It never
prints the URI.
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import httpx

from watch_tonight.domain.movie import Movie, Profile
from watch_tonight.infra.fakes import HashEmbedder
from watch_tonight.infra.mongodb import (
    MOVIES,
    MongoCatalogue,
    connect,
    ensure_catalogue,
    wait_until_searchable,
)
from watch_tonight.infra.settings import Settings, is_local_mongodb
from watch_tonight.infra.tmdb_mapping import movie_from_bundle

PROFILES: Final = Path("spikes/16-recommendation/pool_b_profiles.jsonl")
TMDB_URL: Final = "https://api.themoviedb.org/3/movie/{id}"
APPEND: Final = "release_dates,watch/providers,keywords,credits"
CONCURRENCY: Final = 8  # well under TMDB's measured ~25 requests a second (spike 08)
EMBEDDING_MODEL: Final = "hash-embedder-384 (fake, until feat-028)"


def read_profiles(limit: int | None) -> dict[int, Profile]:
    profiles: dict[int, Profile] = {}
    # Split on "\n" only: TMDB text can hold U+2028, which splitlines() treats as a break.
    for line in PROFILES.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        row: dict[str, Any] = json.loads(line)
        if row["variant"] == "base" and not row["error"]:
            profiles[int(row["id"])] = Profile.model_validate(row["profile"])
    ids = sorted(profiles)[:limit] if limit else sorted(profiles)
    return {i: profiles[i] for i in ids}


async def fetch_bundles(ids: list[int], key: str) -> dict[int, dict[str, Any]]:
    # A v4 read token goes in the Authorization header; a v3 key is a query parameter.
    is_token = key.startswith("eyJ")
    headers = {"Authorization": f"Bearer {key}"} if is_token else {}
    params = {"append_to_response": APPEND, "language": "en-US"}
    if not is_token:
        params["api_key"] = key
    gate = asyncio.Semaphore(CONCURRENCY)
    bundles: dict[int, dict[str, Any]] = {}

    async with httpx.AsyncClient(headers=headers, timeout=20) as client:

        async def fetch(movie_id: int) -> None:
            try:
                async with gate:
                    response = await client.get(TMDB_URL.format(id=movie_id), params=params)
            except httpx.HTTPError as error:  # one failed call skips one film, not the run
                print(f"  TMDB {movie_id}: {type(error).__name__}", file=sys.stderr)
                return
            if response.status_code == 200:
                bundles[movie_id] = response.json()
            else:
                print(f"  TMDB {movie_id}: HTTP {response.status_code}", file=sys.stderr)

        await asyncio.gather(*(fetch(i) for i in ids))
    return bundles


async def seed(settings: Settings, limit: int | None) -> None:
    key = settings.tmdb_api_key.get_secret_value() if settings.tmdb_api_key else ""
    if not key:
        raise SystemExit("TMDB_API_KEY is not set (environment or .env).")
    # Open the database first, so a database that is down fails before ~300 TMDB calls.
    client = connect(settings.mongodb_uri.get_secret_value(), timeout_ms=10_000)
    try:
        database = client[settings.mongodb_database]
        await ensure_catalogue(database)

        profiles = read_profiles(limit)
        print(f"Profiles: {len(profiles)} (spike 16, variant base)")
        bundles = await fetch_bundles(list(profiles), key)
        print(f"TMDB bundles: {len(bundles)} of {len(profiles)}")

        refreshed_at = datetime.now(UTC)
        embedder = HashEmbedder()
        movies: list[Movie] = []
        for movie_id, bundle in sorted(bundles.items()):
            profile = profiles[movie_id]
            try:
                movies.append(
                    movie_from_bundle(
                        bundle,
                        profile=profile,
                        embedding=embedder.embed(f"{bundle.get('title')}. {profile.summary}"),
                        refreshed_at=refreshed_at,
                        embedding_model=EMBEDDING_MODEL,
                        prompt_version="spike16-base",
                        model="gpt-6-luna",
                    )
                )
            except ValueError as problem:
                print(f"  skipped: {problem}")

        await MongoCatalogue(database).upsert_many(movies)
        searchable = await wait_until_searchable(database)
        total = await database[MOVIES].count_documents({})
        print(f"Stored: {len(movies)} upserted; {total} in '{MOVIES}'; {searchable} searchable")
        sample = await database[MOVIES].find_one(
            {}, projection={"title": 1, "year": 1, "streamable": 1, "certification_us": 1,
                            "certification_es": 1, "availability_updated_at": 1},
            sort=[("_id", 1)],
        )  # fmt: skip
        print(f"Sample: {sample}")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local Atlas with spike 16's 300 films.")
    parser.add_argument("--allow-remote", action="store_true", help="allow a non-local database")
    parser.add_argument("--limit", type=int, help="seed only the first N films (a quick try)")
    args = parser.parse_args()
    if not PROFILES.exists():
        raise SystemExit(
            f"{PROFILES} not found. It's a local spike output (gitignored): copy it from the "
            "machine that ran spike 16, or re-run spikes/16-recommendation/enrich.py."
        )
    settings = Settings()
    if not is_local_mongodb(settings.mongodb_uri.get_secret_value()) and not args.allow_remote:
        raise SystemExit(
            "WATCH_TONIGHT_MONGODB_URI is not a database on this machine. Refusing to seed; "
            "pass --allow-remote if you really mean it."
        )
    asyncio.run(seed(settings, args.limit))


if __name__ == "__main__":
    main()
