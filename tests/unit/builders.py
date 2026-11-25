"""Builders for unit tests: a movie and an intent with sensible defaults."""

from datetime import UTC, datetime

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.movie import Movie, Profile
from watch_tonight.domain.vocabulary import ContentWarning, Intensity


def movie(
    movie_id: int = 1,
    *,
    runtime: int = 100,
    year: int = 2015,
    language: str = "en",
    collection: int | None = None,
    us: str | None = None,
    es: str | None = None,
    intensity: Intensity = 2,
    warnings: list[ContentWarning] | None = None,
    streamable: list[str] | None = None,
) -> Movie:
    return Movie(
        id=movie_id,
        title=f"Film {movie_id}",
        year=year,
        runtime=runtime,
        original_language=language,
        collection_id=collection,
        certification_us=us,
        certification_es=es,
        poster_path="/p.jpg",
        streamable=streamable if streamable is not None else ["ES:8"],
        availability_updated_at=datetime(2026, 11, 24, tzinfo=UTC),
        profile=Profile(
            tone=["light"],
            pacing="medium",
            intensity=intensity,
            viewing_effort="easy",
            ending_feel="warm_resolved",
            humor_style="none",
            content_warnings=warnings or [],
            themes=[],
            summary="",
        ),
    )


def intent(**overrides: object) -> QueryIntent:
    base: dict[str, object] = {
        "max_runtime_minutes": None,
        "max_intensity": None,
        "avoid": [],
        "year_min": None,
        "year_max": None,
        "audience": None,
        "original_languages": [],
        "tone": [],
        "pacing": None,
        "viewing_effort": None,
        "ending_feel": None,
        "humor_style": None,
        "themes": [],
        "semantic_description": "x",
        "specificity": "broad",
        "era_mode": "modern_default",
        "acclaim_preference": "any",
        "unmapped_constraints": [],
    }
    return QueryIntent.model_validate({**base, **overrides})
