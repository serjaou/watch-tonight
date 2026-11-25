"""Unit tests for the MongoDB adapter's pure parts, the TMDB mapping and the settings guard."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from tests.unit.builders import movie

from watch_tonight.domain.limits import AUDIENCE_RULES, AppliedLimits
from watch_tonight.domain.ports import CandidateQuery
from watch_tonight.infra.mongodb import (
    ATLAS_LOCAL_IMAGE,
    FILTER_PATHS,
    audience_clause,
    build_prefilter,
    document_to_movie,
    movie_to_document,
    vector_index_definition,
)
from watch_tonight.infra.settings import is_local_mongodb
from watch_tonight.infra.tmdb_mapping import (
    admission_problems,
    first_certification,
    flat_rate_keys,
    movie_from_bundle,
)


def query(limits: AppliedLimits, exclude: list[int] | None = None) -> CandidateQuery:
    return CandidateQuery(
        vector=[1.0], streamable_any=["ES:8"], exclude_ids=exclude or [], limits=limits, limit=150
    )


def test_prefilter_with_no_limits_keeps_only_availability() -> None:
    assert build_prefilter(query(AppliedLimits()), audience_in_prefilter=True) == {
        "$and": [{"streamable": {"$in": ["ES:8"]}}]
    }


def test_prefilter_holds_every_limit() -> None:
    limits = AppliedLimits(
        max_runtime=100,
        max_intensity=3,
        avoid=frozenset({"gore", "violence"}),
        year_min=2000,
        year_max=2010,
        original_languages=frozenset({"en"}),
        audience="kids",
    )
    clauses = build_prefilter(query(limits, [7]), audience_in_prefilter=True)["$and"]
    assert clauses == [
        {"streamable": {"$in": ["ES:8"]}},
        {"_id": {"$nin": [7]}},
        {"runtime": {"$lte": 100}},
        {"profile.intensity": {"$lte": 3}},
        {"profile.content_warnings": {"$nin": ["gore", "violence"]}},
        {"year": {"$gte": 2000}},
        {"year": {"$lte": 2010}},
        {"original_language": {"$in": ["en"]}},
        audience_clause("kids"),
    ]
    without = build_prefilter(query(limits, [7]), audience_in_prefilter=False)["$and"]
    assert audience_clause("kids") not in without


def _field_paths(node: Any) -> set[str]:
    """Every field name in a filter document (operators start with `$`)."""
    if isinstance(node, list):
        found: set[str] = set()
        for item in cast(list[Any], node):
            found |= _field_paths(item)
        return found
    if isinstance(node, dict):
        paths: set[str] = set()
        for key, value in cast(dict[str, Any], node).items():
            if not key.startswith("$"):
                paths.add(key)
            paths |= _field_paths(value)
        return paths
    return set()


def test_every_prefilter_path_is_declared_in_the_index() -> None:
    declared = {f["path"] for f in vector_index_definition()["fields"] if f["type"] == "filter"}
    assert declared == set(FILTER_PATHS)
    every_limit = AppliedLimits(
        max_runtime=100,
        max_intensity=3,
        avoid=frozenset({"gore"}),
        year_min=2000,
        year_max=2010,
        original_languages=frozenset({"en"}),
        audience="kids",
    )
    used = _field_paths(build_prefilter(query(every_limit, [7]), audience_in_prefilter=True))
    assert used == declared  # a new filter clause can't skip the index declaration


def test_compose_uses_the_pinned_image() -> None:
    compose = Path("compose.yaml").read_text(encoding="utf-8")
    assert f"image: {ATLAS_LOCAL_IMAGE}\n" in compose


def test_movie_from_bundle_maps_the_data_model() -> None:
    bundle: dict[str, Any] = {
        "id": 5,
        "title": "Five",
        "original_language": "en",
        "release_date": "2001-02-03",
        "runtime": 90,
        "overview": "A film.",
        "tagline": "",
        "poster_path": "/five.jpg",
        "genres": [{"name": "Drama"}],
        "belongs_to_collection": None,
        "keywords": {"keywords": [{"name": "duringcreditsstinger"}, {"name": "rain"}]},
        "credits": {
            "cast": [{"name": f"C{n}", "order": n} for n in (6, 2, 0, 1, 5, 3, 4)],
            "crew": [{"job": "Director", "name": "D1"}, {"job": "Director", "name": "D2"}],
        },
        "watch/providers": {"results": {"ES": {"rent": [{"provider_id": 2}]}}},
    }
    when = datetime(2026, 11, 25, tzinfo=UTC)
    mapped = movie_from_bundle(
        bundle, profile=movie(1).profile, embedding=[1.0], refreshed_at=when, embedding_model="x"
    )
    assert (mapped.year, mapped.keywords, mapped.tagline) == (2001, ["rain"], None)
    assert mapped.credits.cast == ["C0", "C1", "C2", "C3", "C4"]
    assert mapped.credits.directors == ["D1", "D2"]
    assert (mapped.collection_id, mapped.certification_us, mapped.certification_es) == (
        None,
        None,
        None,
    )
    assert mapped.streamable == []
    assert mapped.unstreamable_since == when, "Q17: set when it streams nowhere"
    with pytest.raises(ValueError, match="no poster, runtime is 0 or missing"):
        movie_from_bundle(
            {**bundle, "poster_path": None, "runtime": 0},
            profile=movie(1).profile,
            embedding=[],
            refreshed_at=when,
            embedding_model="x",
        )


def test_audience_clause_follows_the_rule_table() -> None:
    clause = audience_clause("teens")["$or"]
    rule = AUDIENCE_RULES["teens"]
    assert clause[0] == {"certification_us": {"$in": sorted(rule.us_ratings)}}
    assert {"certification_es": {"$in": sorted(rule.es_ratings)}} in clause[1]["$and"]
    assert {"profile.intensity": {"$lte": rule.max_intensity}} in clause[2]["$and"]


def test_document_round_trip() -> None:
    original = movie(42, collection=7, us="PG").model_copy(update={"embedding": [0.5, 0.5]})
    document = movie_to_document(original)
    assert document["_id"] == 42
    assert "id" not in document
    assert document_to_movie({**document, "score": 0.9}) == original


BUNDLE: dict[str, Any] = {
    "release_dates": {
        "results": [
            {
                "iso_3166_1": "US",
                "release_dates": [{"certification": "NR"}, {"certification": "R"}],
            },
            {"iso_3166_1": "ES", "release_dates": [{"certification": " "}]},
        ]
    },
    "watch/providers": {
        "results": {
            "US": {
                "flatrate": [{"provider_id": 8}, {"provider_id": 8}],
                "rent": [{"provider_id": 2}],
            },
            "ES": {"ads": [{"provider_id": 1796}]},
            "DE": {"flatrate": [{"provider_id": 8}]},
        }
    },
}


def test_certification_skips_empty_and_nr() -> None:
    assert first_certification(BUNDLE, "US") == "R"
    assert first_certification(BUNDLE, "ES") is None
    assert first_certification(BUNDLE, "BO") is None


def test_flat_rate_keys_only_in_launch_countries() -> None:
    assert flat_rate_keys(BUNDLE) == ["US:8"]


def test_admission_problems_name_each_missing_field() -> None:
    assert admission_problems({"release_date": "", "runtime": 0}) == [
        "no release year",
        "no overview",
        "no poster",
        "runtime is 0 or missing",
        "no genre",
    ]


@pytest.mark.parametrize(
    ("uri", "local"),
    [
        ("mongodb://localhost:27017/?directConnection=true", True),
        ("mongodb://test:test@127.0.0.1:32768/?directConnection=true", True),
        ("mongodb://[::1]:27017", True),
        ("mongodb+srv://user:secret@cluster0.example.mongodb.net/", False),
        ("mongodb://localhost:27017,db.example.com:27017", False),
        ("mongodb://", False),
    ],
)
def test_is_local_mongodb(uri: str, local: bool) -> None:
    assert is_local_mongodb(uri) is local


def test_movie_dates_keep_their_time_zone() -> None:
    when = datetime(2026, 11, 25, tzinfo=UTC)
    document = movie_to_document(movie(1).model_copy(update={"availability_updated_at": when}))
    assert document["availability_updated_at"].tzinfo is not None
