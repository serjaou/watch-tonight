"""Fictional films and test doubles for the walking-skeleton acceptance tests (spec 18).

Every title, id, rating and availability here is made up. Each film is built to trigger
one rule; its comment says which. The PR gate protects this file like the tests.

Similarity is set per film: the query vector is the unit vector e0, and each film's
vector has cosine `similarity` to it, so the search order is known in advance.
"""

import asyncio
import math
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any, Final

import httpx
from fastapi import FastAPI

from watch_tonight.api.app import create_app
from watch_tonight.application.search_movies import SearchMovies
from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.movie import Candidate, Movie, Profile
from watch_tonight.domain.output_checks import Pick
from watch_tonight.domain.ports import (
    CandidateQuery,
    CandidateSearch,
    Pitches,
    Understanding,
    Usage,
)
from watch_tonight.domain.vocabulary import ContentWarning, Intensity
from watch_tonight.infra.memory import InMemoryCatalogue, cosine_similarity

AVAILABLE_AT: Final = datetime(2026, 11, 24, 3, 0, tzinfo=UTC)
DIMENSIONS: Final = 384
QUERY_VECTOR: Final = [1.0] + [0.0] * (DIMENSIONS - 1)


def vector_with_similarity(similarity: float) -> list[float]:
    return [similarity, math.sqrt(1 - similarity**2)] + [0.0] * (DIMENSIONS - 2)


def film(
    movie_id: int,
    title: str,
    *,
    similarity: float,
    streamable: list[str],
    year: int = 2015,
    runtime: int = 100,
    language: str = "en",
    collection: int | None = None,
    us: str | None = None,
    es: str | None = None,
    intensity: Intensity = 2,
    warnings: Sequence[ContentWarning] = (),
) -> Movie:
    return Movie(
        id=movie_id,
        title=title,
        year=year,
        runtime=runtime,
        original_language=language,
        collection_id=collection,
        certification_us=us,
        certification_es=es,
        poster_path=f"/fixture-{movie_id}.jpg",
        streamable=streamable,
        availability_updated_at=AVAILABLE_AT,
        profile=Profile(
            tone=["light"],
            pacing="medium",
            intensity=intensity,
            viewing_effort="easy",
            ending_feel="warm_resolved",
            humor_style="warm_gentle",
            content_warnings=list(warnings),
            themes=["friendship"],
            summary=f"{title} is a fictional film made for tests.",
        ),
        embedding=vector_with_similarity(similarity),
    )


# The base request is Spain (ES) with Netflix (8) and Disney Plus (337).
FILMS: Final[list[Movie]] = [
    # Plain films, streamable on a selected service; best similarity first.
    # 9001 streams on both selected services, so it lists two.
    film(9001, "The Lantern Keeper", similarity=0.99, streamable=["ES:8", "ES:337", "US:8"],
         runtime=104, us="PG", es="7"),
    film(9002, "Paper Comets", similarity=0.98, streamable=["ES:337"], year=2019, runtime=95,
         us="PG-13", es="12", intensity=3, warnings=["strong_language"]),
    film(9003, "Midnight Orchard", similarity=0.97, streamable=["ES:8"], year=2011,
         runtime=118, language="fr", us="R", es="16", intensity=4, warnings=["violence"]),
    # No rating at all, gentle profile: suits kids by the profile fallback.
    film(9004, "A Quiet Harbour", similarity=0.96, streamable=["ES:8", "BO:8"], year=2021,
         runtime=88, intensity=1),
    film(9005, "Saltwater Detectives", similarity=0.95, streamable=["ES:337", "US:337"],
         year=2008, runtime=132, us="PG-13", es="12", intensity=3, warnings=["violence"]),
    # Spanish rating only: 7 suits kids; 16 suits nobody.
    film(9006, "The Glass Orchard Hotel", similarity=0.94, streamable=["ES:8"], year=1998,
         runtime=101, language="es", es="7"),
    film(9007, "Static Bloom", similarity=0.93, streamable=["ES:8"], year=2023, runtime=79,
         language="ko", es="16", intensity=4, warnings=["gore"]),
    # No rating, harsh profile: fails kids and teens by the profile fallback. With only
    # violence as a warning, intensity 4 is the one limit it breaks in the limits test.
    film(9008, "Grey Tide", similarity=0.92, streamable=["ES:337"], year=2017, runtime=97,
         intensity=4, warnings=["violence"]),
    # One collection (777): only its best-scoring film, Star Pilot II, may be kept.
    film(9009, "Star Pilot", similarity=0.87, streamable=["ES:8"], year=2001, runtime=110,
         collection=777, us="PG", es="7", intensity=3, warnings=["violence"]),
    film(9010, "Star Pilot II", similarity=0.91, streamable=["ES:8"], year=2004, runtime=115,
         collection=777, us="PG", es="7", intensity=3, warnings=["violence"]),
    film(9011, "Star Pilot III", similarity=0.89, streamable=["ES:337"], year=2007,
         runtime=120, collection=777, us="PG-13", es="12", intensity=3, warnings=["violence"]),
    # Availability traps (P1): the best similarities, but not on a selected service in ES.
    film(9012, "Elsewhere Only", similarity=0.995, streamable=["US:8"], us="PG", es="A",
         intensity=1),
    film(9013, "Wrong Service", similarity=0.985, streamable=["ES:119"], year=2018,
         runtime=90, us="PG", es="A", intensity=1),
    # Limit traps: runtime, year, intensity and content.
    film(9014, "The Long Night Shift", similarity=0.90, streamable=["ES:8"], year=2012,
         runtime=165, us="R", es="18", intensity=3, warnings=["strong_language"]),
    film(9015, "Old Reel", similarity=0.88, streamable=["ES:8"], year=1974, runtime=99,
         us="PG", es="7"),
    film(9016, "Blood Orchard", similarity=0.86, streamable=["ES:337"], year=2020, runtime=92,
         us="R", es="18", intensity=5, warnings=["gore", "violence"]),
    # No rating, intensity 3 with violence: fails kids, suits teens.
    film(9017, "Harbour Lights", similarity=0.85, streamable=["ES:8"], year=2014, runtime=96,
         intensity=3, warnings=["violence"]),
    # Spanish 12 only: fails kids, suits teens.
    film(9018, "Twelve Bells", similarity=0.84, streamable=["ES:337"], year=2016,
         runtime=103, es="12"),
    # US R wins over Spanish 7: the US rating comes first.
    film(9019, "Mixed Signals", similarity=0.83, streamable=["ES:8"], year=2010, runtime=94,
         us="R", es="7", intensity=1),
    # From 2023 and otherwise clean: the latest-year limit (2022) is the one it breaks.
    # Rated R, so it suits neither audience.
    film(9020, "Brand New Morning", similarity=0.82, streamable=["ES:8"], year=2023,
         runtime=90, us="R", es="18", intensity=1),
]  # fmt: skip

CATALOGUE: Final[dict[int, Movie]] = {m.id: m for m in FILMS}

BASE_REQUEST: Final[dict[str, Any]] = {
    "text": "Something light and funny for tonight",
    "country": "ES",
    "providers": [8, 337],
}

_BASE_INTENT: Final[dict[str, Any]] = {
    "max_runtime_minutes": None,
    "max_intensity": None,
    "avoid": [],
    "year_min": None,
    "year_max": None,
    "audience": None,
    "original_languages": [],
    "tone": ["light", "funny"],
    "pacing": None,
    "viewing_effort": None,
    "ending_feel": None,
    "humor_style": None,
    "themes": [],
    "semantic_description": "A light, funny film with low stakes.",
    "specificity": "broad",
    "era_mode": "modern_default",
    "acclaim_preference": "any",
    "unmapped_constraints": [],
}


def make_intent(**overrides: Any) -> QueryIntent:
    """A `QueryIntent` with no limits, changed only where a test says so."""
    return QueryIntent.model_validate({**_BASE_INTENT, **overrides})


PickScript = Callable[[Sequence[Candidate]], list[Pick]]


def first_five_picks(candidates: Sequence[Candidate]) -> list[Pick]:
    return [
        Pick(movie_id=c.movie.id, pitch=f"{c.movie.title} is gentle, warm and quietly funny.")
        for c in candidates[:5]
    ]


class ScriptedLanguageModel:
    """The LLM port, scripted per test; records how it was called."""

    def __init__(
        self,
        intent: QueryIntent | None = None,
        *,
        picks: PickScript = first_five_picks,
        understand_error: Exception | None = None,
        pick_error: Exception | None = None,
    ) -> None:
        self.intent = intent or make_intent()
        self._picks = picks
        self._understand_error = understand_error
        self._pick_error = pick_error
        self.understand_calls = 0
        self.pick_calls = 0
        self.received: list[Candidate] = []

    @property
    def received_ids(self) -> list[int]:
        return [c.movie.id for c in self.received]

    async def understand(self, text: str) -> Understanding:
        self.understand_calls += 1
        if self._understand_error is not None:
            raise self._understand_error
        usage = Usage(input_tokens=120, output_tokens=80, cost_usd=0.0001)
        return Understanding(intent=self.intent, usage=usage)

    async def pick_and_pitch(self, intent: QueryIntent, candidates: Sequence[Candidate]) -> Pitches:
        self.pick_calls += 1
        self.received = list(candidates)
        if self._pick_error is not None:
            raise self._pick_error
        usage = Usage(input_tokens=900, output_tokens=200, cost_usd=0.0005)
        return Pitches(picks=self._picks(candidates), usage=usage)


class FixedEmbedder:
    """Every query embeds to e0, so a film's score is its fixture similarity."""

    def __init__(self) -> None:
        self.calls = 0

    async def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        return list(QUERY_VECTOR)


class RecordingSearch:
    """The in-memory search over the fixture films, recording each query."""

    def __init__(self) -> None:
        self._catalogue = InMemoryCatalogue(FILMS)
        self.queries: list[CandidateQuery] = []

    async def search(self, query: CandidateQuery) -> list[Candidate]:
        self.queries.append(query)
        return await self._catalogue.search(query)


class UnfilteredSearch:
    """A search port that ignores every filter and returns all films in id order.

    It proves that step 4 re-checks each rule by value and ranks by score itself.
    """

    def __init__(self) -> None:
        self.queries: list[CandidateQuery] = []

    async def search(self, query: CandidateQuery) -> list[Candidate]:
        self.queries.append(query)
        return [
            Candidate(movie=m, score=cosine_similarity(query.vector, m.embedding)) for m in FILMS
        ]


class FailingSearch:
    """A search port whose database is down."""

    async def search(self, query: CandidateQuery) -> list[Candidate]:
        raise ConnectionError("database unreachable")


class ApiClient:
    """Calls the FastAPI app in memory through httpx's ASGI transport: no server, no port.

    Like `WebApplicationFactory` in ASP.NET Core integration tests.
    """

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def post(self, path: str, json: Any) -> httpx.Response:
        async def call() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(path, json=json)

        return asyncio.run(call())


def client_for(
    language_model: ScriptedLanguageModel,
    search: CandidateSearch | None = None,
    embedder: FixedEmbedder | None = None,
) -> ApiClient:
    use_case = SearchMovies(
        language_model,
        embedder or FixedEmbedder(),
        search or RecordingSearch(),
        InMemoryCatalogue(FILMS),  # the repository: the catalogue's last refresh (P6)
    )
    return ApiClient(create_app(use_case))


def result_for(movie: Movie, pitch: str | None = "A fictional pitch.") -> dict[str, Any]:
    """A result entry as the API would return it for `movie` (for planting violations)."""
    return {
        "id": movie.id,
        "title": movie.title,
        "year": movie.year,
        "runtime": movie.runtime,
        "poster_url": f"https://image.tmdb.org/t/p/w342{movie.poster_path}",
        "services": [{"id": 8, "name": "Netflix"}],
        "pitch": pitch,
        "tmdb_url": f"https://www.themoviedb.org/movie/{movie.id}",
        "availability_updated_at": movie.availability_updated_at.isoformat(),
    }
