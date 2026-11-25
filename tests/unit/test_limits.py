"""Unit tests for the step-4 checks (domain/limits.py)."""

from datetime import UTC, datetime

import pytest

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.limits import (
    AppliedLimits,
    broken_limits,
    check_and_rank,
    merge_limits,
    one_per_collection,
    suits_audience,
)
from watch_tonight.domain.movie import Candidate, Movie, Profile
from watch_tonight.domain.search import SearchRequest
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


def request(**fields: object) -> SearchRequest:
    return SearchRequest.model_validate({"text": "x", "country": "ES", "providers": [8], **fields})


def test_merge_takes_the_stricter_limit_and_combines_avoid() -> None:
    limits = merge_limits(
        request(max_runtime=120, max_intensity=2, avoid=["gore"]),
        intent(max_runtime_minutes=90, max_intensity=4, avoid=["violence"]),
    )
    assert (limits.max_runtime, limits.max_intensity) == (90, 2)
    assert limits.avoid == {"gore", "violence"}


def test_merge_keeps_a_limit_set_on_one_side_only() -> None:
    assert merge_limits(request(max_runtime=120), intent()).max_runtime == 120
    assert merge_limits(request(), intent(max_runtime_minutes=90)).max_runtime == 90
    assert merge_limits(request(), intent()) == AppliedLimits()


def test_no_limits_breaks_nothing() -> None:
    assert broken_limits(movie(runtime=400, intensity=5, warnings=["gore"]), AppliedLimits()) == []


@pytest.mark.parametrize(
    ("film", "limits", "broken"),
    [
        (movie(runtime=91), AppliedLimits(max_runtime=90), ["runtime"]),
        (movie(runtime=90), AppliedLimits(max_runtime=90), []),
        (movie(intensity=4), AppliedLimits(max_intensity=3), ["intensity"]),
        (movie(warnings=["gore"]), AppliedLimits(avoid=frozenset({"gore"})), ["avoid"]),
        (movie(year=1999), AppliedLimits(year_min=2000), ["year"]),
        (movie(year=2023), AppliedLimits(year_max=2022), ["year"]),
        (
            movie(language="ko"),
            AppliedLimits(original_languages=frozenset({"en"})),
            ["original_language"],
        ),
        (movie(us="R"), AppliedLimits(audience="kids"), ["audience"]),
    ],
)
def test_each_limit_is_checked_by_value(
    film: Movie, limits: AppliedLimits, broken: list[str]
) -> None:
    assert broken_limits(film, limits) == broken


@pytest.mark.parametrize(
    ("film", "kids", "teens"),
    [
        (movie(us="G"), True, True),
        (movie(us="PG"), True, True),
        (movie(us="PG-13"), False, True),
        (movie(us="R", es="A"), False, False),  # the US rating wins
        (movie(us="PG", es="18"), True, True),
        (movie(es="Ai"), True, True),
        (movie(es="7i"), True, True),
        (movie(es="12"), False, True),
        (movie(es="16"), False, False),
        (movie(intensity=2), True, True),  # no rating: the profile decides
        (movie(intensity=3), False, True),
        (movie(intensity=4), False, False),
        (movie(intensity=1, warnings=["strong_language"]), False, True),
        (movie(intensity=1, warnings=["gore"]), False, False),
        (movie(intensity=1, warnings=["flashing_lights"]), True, True),
    ],
)
def test_audience_rule(film: Movie, kids: bool, teens: bool) -> None:
    assert suits_audience(film, "kids") is kids
    assert suits_audience(film, "teens") is teens


def test_one_per_collection_keeps_the_first_and_never_dedupes_films_without_one() -> None:
    films = [movie(1, collection=7), movie(2), movie(3, collection=7), movie(4)]
    kept = one_per_collection(Candidate(movie=m, score=0.5) for m in films)
    assert [c.movie.id for c in kept] == [1, 2, 4]


def test_check_and_rank_drops_orders_dedupes_and_keeps() -> None:
    candidates = [
        Candidate(movie=movie(1, streamable=["US:8"]), score=0.99),  # not streamable in ES
        Candidate(movie=movie(2), score=0.5),
        Candidate(movie=movie(3, collection=7), score=0.7),
        Candidate(movie=movie(4, collection=7), score=0.9),
        Candidate(movie=movie(5), score=0.8),  # excluded
        Candidate(movie=movie(6, runtime=200), score=0.95),  # too long
        Candidate(movie=movie(7), score=0.5),  # ties with 2: lower id first
    ]
    ranked = check_and_rank(
        candidates,
        streamable_keys={"ES:8"},
        exclude_ids={5},
        limits=AppliedLimits(max_runtime=120),
        keep=2,
    )
    assert [c.movie.id for c in ranked] == [4, 2]
