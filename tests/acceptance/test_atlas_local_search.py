"""Acceptance tests for feat-030, walking skeleton part 2 (docs/specs/30-atlas-local-search.md).

The search on `mongodb-atlas-local`, started by testcontainers from the pinned image. They
need Docker (`uv run poe test-all`). Part 1's fictional films and doubles are reused.
Test names match the spec.
"""

import time
from collections.abc import AsyncIterator, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import OperationFailure
from testcontainers.community.mongodb import MongoDBAtlasLocalContainer
from tests.acceptance.walking_skeleton_fixtures import (
    AVAILABLE_AT,
    BASE_REQUEST,
    CATALOGUE,
    FILMS,
    QUERY_VECTOR,
    FixedEmbedder,
    ScriptedLanguageModel,
    film,
    make_intent,
)

from watch_tonight.api.app import create_app
from watch_tonight.application.search_movies import SearchMovies
from watch_tonight.domain.limits import AppliedLimits, broken_limits, passes_checks
from watch_tonight.domain.movie import Movie, Profile
from watch_tonight.domain.ports import CandidateQuery
from watch_tonight.domain.search import JUSTWATCH_NOTICE, TMDB_NOTICE
from watch_tonight.infra.mongodb import (
    ATLAS_LOCAL_IMAGE,
    MOVIES,
    Document,
    MongoCatalogue,
    connect,
    create_vector_index,
    drop_vector_index,
    ensure_catalogue,
    search_index_info,
    update_vector_index,
    vector_index_definition,
    wait_until_searchable,
)
from watch_tonight.infra.tmdb_mapping import movie_from_bundle

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]

SELECTED: Final = ["ES:8", "ES:337"]
KIDS: Final = {9001, 9004, 9006, 9010, 9015}
TEENS: Final = {9001, 9002, 9004, 9005, 9006, 9010, 9015, 9017, 9018}


@pytest.fixture(scope="module")
def atlas_uri() -> Iterator[str]:
    with MongoDBAtlasLocalContainer(ATLAS_LOCAL_IMAGE) as container:
        yield container.get_connection_url()


async def seeded(atlas_uri: str, name: str, films: Sequence[Movie]) -> AsyncDatabase[Document]:
    """A database with these films, the vector index built and in sync."""
    database = connect(atlas_uri, timeout_ms=10_000)[name]
    await ensure_catalogue(database)
    await MongoCatalogue(database).upsert_many(films)
    assert await wait_until_searchable(database) == len(films)
    return database


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def database(atlas_uri: str) -> AsyncIterator[AsyncDatabase[Document]]:
    """Part 1's fixture films in local Atlas."""
    database = await seeded(atlas_uri, "walking_skeleton", FILMS)
    yield database
    await database.client.close()


async def post(app: FastAPI, body: dict[str, Any]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/search", json=body)


def app_on(catalogue: MongoCatalogue, llm: ScriptedLanguageModel) -> FastAPI:
    return create_app(SearchMovies(llm, FixedEmbedder(), catalogue, catalogue))


async def test_vector_index_create_update_drop_from_code(
    database: AsyncDatabase[Document],
) -> None:
    lifecycle = database["index_lifecycle"]
    await lifecycle.insert_many(
        [
            {"_id": i, "runtime": 90 + i, "year": 2000 + i, "embedding": QUERY_VECTOR}
            for i in range(3)
        ]
    )
    name = "lifecycle_vector"
    with_runtime = vector_index_definition(["runtime"])
    with_year = vector_index_definition(["runtime", "year"])

    async def ids(filter_: Document) -> set[int]:
        stage = {"index": name, "path": "embedding", "queryVector": QUERY_VECTOR}
        stage |= {"numCandidates": 10, "limit": 10, "filter": filter_}
        cursor = await lifecycle.aggregate([{"$vectorSearch": stage}])
        return {int(d["_id"]) async for d in cursor}

    await create_vector_index(lifecycle, with_runtime, name=name)
    assert await ids({"runtime": {"$lte": 91}}) == {0, 1}
    # The same name with a different definition is an error, and it is raised, never
    # silenced. (The same name and definition again is accepted as a no-op.)
    with pytest.raises(OperationFailure):
        await create_vector_index(lifecycle, with_year, name=name)

    await update_vector_index(lifecycle, with_year, name=name)
    assert await ids({"year": {"$gte": 2001}}) == {1, 2}  # the new path is declared now

    await drop_vector_index(lifecycle, name=name)
    assert await search_index_info(lifecycle, name) is None
    # Without its index, $vectorSearch returns nothing rather than an error. That's why
    # MongoCatalogue.search turns an empty answer on a missing index into an error (503).
    assert await ids({"runtime": {"$lte": 91}}) == set()


# Two extra films, each breaking exactly one limit of the all-filters query, so the
# `avoid` ($nin on an array) and language filters are each shown to exclude on their own.
ONLY_AVOIDED: Final = film(9101, "Only Avoided", similarity=0.80, streamable=["ES:8"],
                           runtime=95, us="PG-13", warnings=["drug_use"])  # fmt: skip
ONLY_FOREIGN: Final = film(9102, "Only Foreign", similarity=0.79, streamable=["ES:8"],
                           runtime=95, language="de", us="PG-13")  # fmt: skip


async def test_vector_search_applies_all_prefilters_together(atlas_uri: str) -> None:
    films = [*FILMS, ONLY_AVOIDED, ONLY_FOREIGN]
    database = await seeded(atlas_uri, "all_prefilters", films)
    limits = AppliedLimits(
        max_runtime=120,
        max_intensity=3,
        avoid=frozenset({"gore", "drug_use"}),
        year_min=2000,
        year_max=2022,
        original_languages=frozenset({"en"}),
        audience="teens",  # with the certification paths: all 9 filter paths in one query
    )
    exclude = [9002, *range(1, 5_000)]  # 5,000 ids, one of them a film that would pass
    query = CandidateQuery(
        vector=QUERY_VECTOR, streamable_any=SELECTED, exclude_ids=exclude, limits=limits, limit=150
    )
    assert broken_limits(ONLY_AVOIDED, limits) == ["avoid"]
    assert broken_limits(ONLY_FOREIGN, limits) == ["original_language"]

    found = await MongoCatalogue(database).search(query)

    expected = {
        m.id
        for m in films
        if passes_checks(m, streamable_keys=SELECTED, exclude_ids=set(exclude), limits=limits)
    }
    assert expected == {9001, 9004, 9009, 9010, 9011, 9017, 9018}
    assert {c.movie.id for c in found} == expected, "every film built to pass is returned"
    for candidate in found:
        assert passes_checks(
            candidate.movie, streamable_keys=SELECTED, exclude_ids=set(exclude), limits=limits
        )
    await database.client.close()


@pytest.mark.parametrize(("audience", "expected"), [("kids", KIDS), ("teens", TEENS)])
async def test_audience_rule_on_atlas_matches_domain_rule(
    database: AsyncDatabase[Document],
    audience: str,
    expected: set[int],
) -> None:
    catalogue = MongoCatalogue(database)
    limits = AppliedLimits.model_validate({"audience": audience})
    query = CandidateQuery(
        vector=QUERY_VECTOR, streamable_any=SELECTED, exclude_ids=[], limits=limits, limit=150
    )
    direct = {c.movie.id for c in await catalogue.search(query)}
    domain = {
        m.id
        for m in FILMS
        if passes_checks(m, streamable_keys=SELECTED, exclude_ids=(), limits=limits)
    }
    # Evidence of the path: with the pre-filter on, Atlas alone returns exactly the films
    # the rule accepts (an $or with the no-rating case, feat-030: it does).
    if catalogue.audience_in_prefilter:
        assert direct == domain, "Atlas holds the audience rule as a pre-filter"
    else:
        assert direct >= domain, "without the pre-filter, step 4 applies the rule"

    llm = ScriptedLanguageModel(make_intent(audience=audience))
    response = await post(app_on(catalogue, llm), BASE_REQUEST)

    assert response.status_code == 200
    assert set(llm.received_ids) == expected  # after step 4 and one film per collection


async def test_search_end_to_end_on_atlas(database: AsyncDatabase[Document]) -> None:
    catalogue = MongoCatalogue(database)
    # A film refreshed a day later that streams nowhere: it never appears in results,
    # but the catalogue's date must be its date (the newest, P6).
    newest = AVAILABLE_AT + timedelta(days=1)
    gone = film(9100, "Gone Everywhere", similarity=0.5, streamable=[], available_at=newest)
    await catalogue.upsert_many([gone.model_copy(update={"embedding": []})])

    # Part 1's success scenario, with its assertions (test_walking_skeleton.py).
    llm = ScriptedLanguageModel()
    response = await post(app_on(catalogue, llm), BASE_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "success"
    assert [r["id"] for r in body["results"]] == [9001, 9002, 9003, 9004, 9005]
    for result in body["results"]:
        movie = CATALOGUE[result["id"]]
        assert set(SELECTED) & set(movie.streamable), "P1"
        assert result["services"]
        for service in result["services"]:
            assert f"ES:{service['id']}" in set(SELECTED) & set(movie.streamable)
        assert result["title"] == movie.title
        assert result["year"] == movie.year
        assert result["runtime"] == movie.runtime
        assert result["poster_url"] == f"https://image.tmdb.org/t/p/w342/fixture-{movie.id}.jpg"
        assert result["tmdb_url"] == f"https://www.themoviedb.org/movie/{movie.id}"
        assert 0 < len(result["pitch"]) <= 350, "P2"
        assert result["availability_updated_at"].startswith(AVAILABLE_AT.isoformat()[:19])
        assert result["availability_updated_at"].endswith("Z")
    assert body["results"][0]["services"] == [
        {"id": 8, "name": "Netflix"},
        {"id": 337, "name": "Disney Plus"},
    ]
    assert body["attribution"] == {"tmdb": TMDB_NOTICE, "availability": JUSTWATCH_NOTICE}
    assert body["notes"] == []
    assert body["availability_updated_at"].startswith(newest.isoformat()[:19]), "P6: newest"
    assert body["availability_updated_at"].endswith("Z")
    timings = set(body["trace"]["timings_ms"])
    assert {"understand", "embed", "retrieve", "freshness", "check", "pick_and_pitch"} <= timings
    assert body["trace"]["tokens"] == {"input": 1020, "output": 280}
    assert body["trace"]["cost_usd"] == pytest.approx(0.0006)

    # Part 1's exclusion scenario, with its assertions.
    llm = ScriptedLanguageModel()
    response = await post(app_on(catalogue, llm), {**BASE_REQUEST, "exclude_ids": [9001, 9004]})

    assert response.status_code == 200
    received = set(llm.received_ids)
    assert not {9001, 9004} & received, "US3"
    assert not {9001, 9004} & {r["id"] for r in response.json()["results"]}
    assert received & {9009, 9010, 9011} == {9010}, "one film per collection"
    no_collection = {
        9002, 9003, 9005, 9006, 9007, 9008, 9014, 9015, 9016, 9017, 9018, 9019, 9020
    }  # fmt: skip
    assert no_collection <= received, "films without a collection are never deduplicated"


async def test_search_returns_503_when_database_is_down(atlas_uri: str) -> None:
    # Unreachable, with the timeouts the app ships with (connect's defaults).
    client = connect("mongodb://localhost:1/?directConnection=true")
    catalogue = MongoCatalogue(client["nowhere"])
    llm = ScriptedLanguageModel()

    started = time.monotonic()
    response = await post(app_on(catalogue, llm), BASE_REQUEST)
    elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.json()["state"] == "service_unavailable"
    assert elapsed < 5, f"answered in {elapsed:.1f}s: a quick 503, never a hang"
    assert llm.pick_calls == 0, "no step-5 call"
    await client.close()

    # Reachable, but the vector index is missing: also a 503, not an empty *Partial*.
    client = connect(atlas_uri, timeout_ms=10_000)
    no_index = MongoCatalogue(client["no_index"])
    await no_index.upsert_many(FILMS)
    llm = ScriptedLanguageModel()

    response = await post(app_on(no_index, llm), BASE_REQUEST)

    assert response.status_code == 503
    assert llm.pick_calls == 0
    await client.close()


BUNDLE: Final[dict[str, Any]] = {  # hand-written, not real TMDB data
    "id": 77001,
    "title": "Fixture Bundle Film",
    "original_title": "Fixture Bundle Film",
    "original_language": "en",
    "release_date": "2019-05-01",
    "runtime": 101,
    "overview": "A made-up film for the seed-mapping test.",
    "tagline": "",
    "poster_path": "/bundle.jpg",
    "genres": [{"id": 35, "name": "Comedy"}],
    "belongs_to_collection": {"id": 555, "name": "Fixture Collection"},
    "vote_average": 7.1,
    "vote_count": 1234,
    "popularity": 12.5,
    "keywords": {"keywords": [{"name": "friendship"}, {"name": "aftercreditsstinger"}]},
    "credits": {
        "cast": [{"name": f"Actor {n}", "order": n} for n in (5, 1, 0, 3, 2, 4)],
        "crew": [{"job": "Writer", "name": "A Writer"}, {"job": "Director", "name": "A Director"}],
    },
    "release_dates": {
        "results": [
            {
                "iso_3166_1": "US",
                "release_dates": [
                    {"certification": ""},
                    {"certification": "NR"},
                    {"certification": "PG-13"},
                ],
            },
            {"iso_3166_1": "ES", "release_dates": [{"certification": "12"}]},
        ]
    },
    "watch/providers": {
        "results": {
            "ES": {"flatrate": [{"provider_id": 8}], "rent": [{"provider_id": 2}]},
            "US": {"buy": [{"provider_id": 3}]},
            "BO": {"flatrate": [{"provider_id": 337}]},
            "FR": {"flatrate": [{"provider_id": 8}]},
        }
    },
}


async def test_seed_maps_tmdb_bundle_and_is_idempotent(atlas_uri: str) -> None:
    client = connect(atlas_uri, timeout_ms=10_000)
    database = client["seed_mapping"]
    refreshed_at = datetime(2026, 11, 25, 4, 0, tzinfo=UTC)
    movie = movie_from_bundle(
        BUNDLE,
        profile=FILMS[0].profile.model_copy(),
        embedding=list(QUERY_VECTOR),
        refreshed_at=refreshed_at,
        embedding_model="hash-embedder-384 (fake)",
    )

    catalogue = MongoCatalogue(database)
    await catalogue.upsert_many([movie])
    await catalogue.upsert_many([movie])

    movies = database[MOVIES]
    assert await movies.count_documents({}) == 1
    stored = await movies.find_one({"_id": 77001})
    assert stored is not None
    assert stored["streamable"] == ["ES:8", "BO:337"], "flat-rate only, launch countries only"
    assert (stored["certification_us"], stored["certification_es"]) == ("PG-13", "12")
    assert stored["keywords"] == ["friendship"], "credit-scene tags dropped"
    assert stored["collection_id"] == 555
    assert stored["poster_path"] == "/bundle.jpg"
    assert stored["availability_updated_at"] == refreshed_at  # read back with its time zone
    assert stored["credits"]["cast"] == [f"Actor {n}" for n in range(5)]
    assert stored["credits"]["directors"] == ["A Director"]
    assert stored["tagline"] is None
    assert Profile.model_validate(stored["profile"]) == FILMS[0].profile
    await client.close()
