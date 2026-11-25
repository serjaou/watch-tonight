"""Unit tests for request validation (step 1), the 422 mapping, and the infra fakes."""

import math

import pytest
from pydantic import ValidationError

from watch_tonight.api.app import _field_error  # pyright: ignore[reportPrivateUsage]
from watch_tonight.domain.search import SearchRequest
from watch_tonight.infra.fakes import EMBEDDING_DIMENSIONS, HashEmbedder
from watch_tonight.infra.memory import cosine_similarity


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
