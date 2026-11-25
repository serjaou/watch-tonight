"""Unit tests for request validation (step 1), the 422 mapping, models and infra."""

import math

import pytest
from pydantic import ValidationError
from tests.unit.builders import intent, movie

from watch_tonight.api.app import _field_error  # pyright: ignore[reportPrivateUsage]
from watch_tonight.domain.limits import AppliedLimits
from watch_tonight.domain.ports import CandidateQuery
from watch_tonight.domain.search import SearchRequest
from watch_tonight.infra.fakes import EMBEDDING_DIMENSIONS, HashEmbedder
from watch_tonight.infra.memory import InMemoryCatalogue, cosine_similarity


def test_request_trims_text_and_accepts_500_characters() -> None:
    req = SearchRequest(text="  " + "x" * 500 + " ", country="US", providers=[9, 15])
    assert req.text == "x" * 500
    assert (req.avoid, req.exclude_ids) == ([], [])


def test_provider_from_another_country_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Unknown service"):
        SearchRequest(text="x", country="US", providers=[119])  # 119 is Prime in ES/BO


def test_field_error_names_the_path_inside_the_body() -> None:
    error = _field_error({"loc": ("body", "avoid", 0), "msg": "Value error, nope"})
    assert (error.field, error.message) == ("avoid.0", "nope")
    assert _field_error({"loc": ("body",), "msg": "Field required"}).field == "body"
    assert _field_error({"loc": ("query", "x"), "msg": "bad"}).field == "body"


async def test_hash_embedder_is_deterministic_and_unit_length() -> None:
    embedder = HashEmbedder()
    first = await embedder.embed_query("a quiet film")
    assert first == await embedder.embed_query("a quiet film")
    assert first != await embedder.embed_query("a loud film")
    assert len(first) == EMBEDDING_DIMENSIONS
    assert math.isclose(math.sqrt(sum(x * x for x in first)), 1.0)


def test_cosine_similarity() -> None:
    assert cosine_similarity([1.0, 0.0], [0.6, 0.8]) == pytest.approx(0.6)
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    with pytest.raises(ValueError, match="differ in length"):
        cosine_similarity([1.0], [1.0, 0.0])


def test_repeated_providers_are_kept_once_in_order() -> None:
    req = SearchRequest(text="x", country="ES", providers=[337, 8, 337])
    assert req.providers == [337, 8]


def test_unreadable_json_is_reported_on_the_body() -> None:
    assert _field_error({"loc": ("body", 12), "msg": "JSON decode error"}).field == "body"


@pytest.mark.parametrize(
    "field", ["max_runtime_minutes", "year_min", "year_max", "original_languages"]
)
def test_intent_limits_have_bounds(field: str) -> None:
    bad: dict[str, object] = {
        "max_runtime_minutes": 0,
        "year_min": 1500,
        "year_max": 3000,
        "original_languages": ["EN"],
    }
    with pytest.raises(ValidationError, match=field):
        intent(**{field: bad[field]})


def test_empty_or_nr_rating_counts_as_no_rating() -> None:
    assert movie(us="NR", es="7").certification_us is None
    assert movie(us=" ", es="").certification_es is None
    assert movie(us="PG ").certification_us == "PG"


async def test_movie_without_a_vector_is_never_a_candidate() -> None:
    with_vector = movie(1).model_copy(update={"embedding": [1.0, 0.0]})
    catalogue = InMemoryCatalogue([with_vector, movie(2)])  # 2 has no vector
    query = CandidateQuery(
        vector=[1.0, 0.0],
        streamable_any=["ES:8"],
        exclude_ids=[],
        limits=AppliedLimits(),
        limit=10,
    )
    assert [c.movie.id for c in await catalogue.search(query)] == [1]
