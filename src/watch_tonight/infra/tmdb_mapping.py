"""A TMDB movie bundle as a `Movie` (architecture §5). No network: the caller fetches.

A bundle is `/movie/{id}?append_to_response=release_dates,watch/providers,keywords,credits`.
The seed of the walking skeleton uses it now; the ingest feature (feat-020) reuses it.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

from watch_tonight.domain.movie import Credits, Movie, Profile

LAUNCH_COUNTRIES: Final[tuple[str, ...]] = ("ES", "US", "BO")
CAST_SIZE: Final[int] = 5

Bundle = Mapping[str, Any]


def first_certification(bundle: Bundle, country: str) -> str | None:
    """The first non-empty, non-`NR` rating for a country (architecture Q16), or None."""
    for result in bundle.get("release_dates", {}).get("results", []):
        if result.get("iso_3166_1") != country:
            continue
        for release in result.get("release_dates", []):
            rating = str(release.get("certification") or "").strip()
            if rating and rating != "NR":
                return rating
    return None


def flat_rate_keys(bundle: Bundle) -> list[str]:
    """`"country:provider"` for flat-rate offers only, in the launch countries (P1)."""
    by_country: Mapping[str, Any] = bundle.get("watch/providers", {}).get("results", {})
    keys: list[str] = []
    for country in LAUNCH_COUNTRIES:
        offers: Mapping[str, Any] = by_country.get(country) or {}
        flat_rate: list[Mapping[str, Any]] = offers.get("flatrate") or []
        keys += [f"{country}:{offer['provider_id']}" for offer in flat_rate]
    return list(dict.fromkeys(keys))


def admission_problems(bundle: Bundle) -> list[str]:
    """The admission data checks (architecture §4) this bundle fails."""
    problems: list[str] = []
    if len(str(bundle.get("release_date") or "")) < 4:
        problems.append("no release year")
    if not bundle.get("overview"):
        problems.append("no overview")
    if not bundle.get("poster_path"):
        problems.append("no poster")
    if not (bundle.get("runtime") or 0) > 0:
        problems.append("runtime is 0 or missing")
    if not bundle.get("genres"):
        problems.append("no genre")
    return problems


def movie_from_bundle(
    bundle: Bundle,
    *,
    profile: Profile,
    embedding: list[float],
    refreshed_at: datetime,
    embedding_model: str,
    prompt_version: str | None = None,
    model: str | None = None,
) -> Movie:
    """Raises `ValueError` when the bundle fails an admission data check.

    `unstreamable_since` is the refresh time when the film streams nowhere. That is right
    for a first insert (the seed); a daily refresh (feat-020) must keep the earliest date,
    or eviction by age (Q17) never triggers.
    """
    problems = admission_problems(bundle)
    if problems:
        raise ValueError(f"TMDB movie {bundle.get('id')}: {', '.join(problems)}")
    credits: Mapping[str, Any] = bundle.get("credits", {})
    cast = sorted(credits.get("cast", []), key=lambda person: person.get("order", 0))
    collection: Mapping[str, Any] = bundle.get("belongs_to_collection") or {}
    streamable = flat_rate_keys(bundle)
    return Movie(
        id=int(bundle["id"]),
        title=str(bundle["title"]),
        original_title=bundle.get("original_title"),
        original_language=str(bundle["original_language"]),
        year=int(str(bundle["release_date"])[:4]),
        runtime=int(bundle["runtime"]),
        genres=[str(g["name"]) for g in bundle.get("genres", [])],
        keywords=[
            str(k["name"])
            for k in bundle.get("keywords", {}).get("keywords", [])
            if not str(k["name"]).endswith("stinger")  # credit-scene tags, not content
        ],
        overview=bundle.get("overview"),
        tagline=bundle.get("tagline") or None,
        credits=Credits(
            directors=[
                str(c["name"]) for c in credits.get("crew", []) if c.get("job") == "Director"
            ],
            cast=[str(c["name"]) for c in cast[:CAST_SIZE]],
        ),
        collection_id=collection.get("id"),
        certification_us=first_certification(bundle, "US"),
        certification_es=first_certification(bundle, "ES"),
        poster_path=str(bundle["poster_path"]),
        tmdb_vote_average=bundle.get("vote_average"),
        tmdb_vote_count=bundle.get("vote_count"),
        tmdb_popularity=bundle.get("popularity"),
        streamable=streamable,
        availability_updated_at=refreshed_at,
        unstreamable_since=None if streamable else refreshed_at,  # Q17
        profile=profile,
        embedding=embedding,
        embedding_model=embedding_model,
        prompt_version=prompt_version,
        model=model,
        updated_at=refreshed_at,
    )
