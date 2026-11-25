"""Acceptance tests for feat-018, walking skeleton part 1 (docs/specs/18-walking-skeleton.md).

`POST /search` end to end through the API with in-memory adapters over fictional films
(see `walking_skeleton_fixtures.py`). Test names match the spec.
"""

import copy
from collections.abc import Sequence
from typing import Any

import pytest
from evals.deterministic.checks import EvalCase, run_checks
from tests.acceptance.walking_skeleton_fixtures import (
    AVAILABLE_AT,
    BASE_REQUEST,
    CATALOGUE,
    FailingSearch,
    FixedEmbedder,
    PickScript,
    RecordingSearch,
    ScriptedLanguageModel,
    UnfilteredSearch,
    client_for,
    first_five_picks,
    make_intent,
    result_for,
)

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.movie import Candidate
from watch_tonight.domain.output_checks import Pick
from watch_tonight.domain.ports import CandidateSearch
from watch_tonight.domain.search import JUSTWATCH_NOTICE, TMDB_NOTICE

SELECTED = {"ES:8", "ES:337"}
TOP_FIVE_BY_SCORE = [9001, 9002, 9003, 9004, 9005]  # 9012 and 9013 rank higher but fail P1


def request(**changes: Any) -> dict[str, Any]:
    return {**BASE_REQUEST, **changes}


def note_codes(body: dict[str, Any]) -> list[str]:
    return [note["code"] for note in body["notes"]]


def test_search_returns_five_streamable_movies_with_pitches_attribution_and_freshness() -> None:
    client = client_for(ScriptedLanguageModel())

    response = client.post("/search", json=request())

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["state"] == "success"
    assert [r["id"] for r in body["results"]] == TOP_FIVE_BY_SCORE
    for result in body["results"]:
        movie = CATALOGUE[result["id"]]
        assert SELECTED & set(movie.streamable), "P1: streamable on a selected service"
        assert result["services"], "P1: the services it streams on are listed"
        for service in result["services"]:
            assert f"ES:{service['id']}" in SELECTED & set(movie.streamable)
            assert service["name"] in {"Netflix", "Disney Plus"}
        assert result["title"] == movie.title
        assert result["year"] == movie.year
        assert result["runtime"] == movie.runtime
        assert result["poster_url"] == f"https://image.tmdb.org/t/p/w342/fixture-{movie.id}.jpg"
        assert result["tmdb_url"] == f"https://www.themoviedb.org/movie/{movie.id}"
        assert 0 < len(result["pitch"]) <= 350, "P2: a pitch of at most 350 characters"
        assert result["availability_updated_at"].startswith(AVAILABLE_AT.isoformat()[:19])
    assert body["attribution"] == {"tmdb": TMDB_NOTICE, "availability": JUSTWATCH_NOTICE}
    assert body["notes"] == []
    trace = body["trace"]
    assert {"understand", "embed", "retrieve", "check", "pick_and_pitch"} <= set(
        trace["timings_ms"]
    )
    assert trace["tokens"] == {"input": 1020, "output": 280}
    assert trace["cost_usd"] == pytest.approx(0.0006)


def test_search_enforces_merged_ui_and_intent_constraints_strictly() -> None:
    intent = make_intent(
        max_runtime_minutes=100,  # stricter than the UI's 120
        max_intensity=4,  # looser than the UI's 3
        avoid=["strong_language"],
        year_min=2000,
        year_max=2022,
        original_languages=["en"],
    )
    llm = ScriptedLanguageModel(intent)
    search = UnfilteredSearch()  # returns every film, breaking every limit
    client = client_for(llm, search)

    response = client.post(
        "/search", json=request(max_runtime=120, max_intensity=3, avoid=["gore"])
    )

    assert response.status_code == 200
    limits = search.queries[0].limits
    assert limits.max_runtime == 100
    assert limits.max_intensity == 3
    assert limits.avoid == {"gore", "strong_language"}
    assert (limits.year_min, limits.year_max) == (2000, 2022)
    assert limits.original_languages == {"en"}
    # Only these films pass every limit by value, and P1:
    assert set(llm.received_ids) == {9004, 9017, 9019}
    for result in response.json()["results"]:
        movie = CATALOGUE[result["id"]]
        assert movie.runtime <= 100
        assert movie.profile.intensity <= 3
        assert not {"gore", "strong_language"} & set(movie.profile.content_warnings)
        assert 2000 <= movie.year <= 2022
        assert movie.original_language == "en"
        assert SELECTED & set(movie.streamable)


@pytest.mark.parametrize(
    ("audience", "expected"),
    [
        # US rating first (9019: US R beats Spanish 7), else Spanish (9006 yes, 9007 no),
        # else the profile (9004 gentle yes; 9008 and 9017 no). One film per collection.
        ("kids", {9001, 9004, 9006, 9010, 9015}),
        # Teens also accept PG-13 (9002, 9005), Spanish 12 (9018) and a profile of
        # intensity 3 with violence (9017).
        ("teens", {9001, 9002, 9004, 9005, 9006, 9010, 9015, 9017, 9018}),
    ],
)
def test_search_enforces_audience_certification_and_profile_fallback_rule(
    audience: str, expected: set[int]
) -> None:
    llm = ScriptedLanguageModel(make_intent(audience=audience))
    client = client_for(llm)

    response = client.post("/search", json=request())

    assert response.status_code == 200
    assert set(llm.received_ids) == expected
    assert {r["id"] for r in response.json()["results"]} <= expected


def test_search_excludes_seen_ids_and_deduplicates_collections() -> None:
    llm = ScriptedLanguageModel()
    client = client_for(llm, UnfilteredSearch())  # step 4 must exclude and dedupe itself

    response = client.post("/search", json=request(exclude_ids=[9001, 9004]))

    assert response.status_code == 200
    received = set(llm.received_ids)
    assert not {9001, 9004} & received, "US3: shown movies never come back"
    assert not {9001, 9004} & {r["id"] for r in response.json()["results"]}
    assert received & {9009, 9010, 9011} == {9010}, "only the best-scoring film of 777"
    no_collection = {9002, 9003, 9005, 9006, 9007, 9008, 9014, 9015, 9016, 9017, 9018, 9019}
    assert no_collection <= received, "films without a collection are never deduplicated"


def test_search_partial_state_including_zero_results() -> None:
    llm = ScriptedLanguageModel(make_intent(original_languages=["fr"]))
    response = client_for(llm).post("/search", json=request())

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "partial"
    assert [r["id"] for r in body["results"]] == [9003]
    assert body["results"][0]["pitch"]
    assert note_codes(body) == ["partial"]

    llm = ScriptedLanguageModel(make_intent(original_languages=["ja"]))
    response = client_for(llm).post("/search", json=request())

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "partial"
    assert body["results"] == []
    assert note_codes(body) == ["partial"]
    assert llm.pick_calls == 0, "no re-rank-and-pitch call when nothing passed"


def test_search_notes_constraints_it_could_not_apply() -> None:
    for extra, state in [({}, "success"), ({"original_languages": ["fr"]}, "partial")]:
        llm = ScriptedLanguageModel(make_intent(unmapped_constraints=["no spiders"], **extra))
        response = client_for(llm).post("/search", json=request())

        body = response.json()
        assert body["state"] == state
        unmapped = [n for n in body["notes"] if n["code"] == "unmapped_constraints"]
        assert [n["message"] for n in unmapped] == ["We couldn't apply: no spiders"]


def _invented_id(candidates: Sequence[Candidate]) -> list[Pick]:
    return [Pick(movie_id=424242, pitch="An invented film."), *first_five_picks(candidates)[:4]]


def _duplicate(candidates: Sequence[Candidate]) -> list[Pick]:
    picks = first_five_picks(candidates)
    return [*picks[:4], picks[0]]


def _four_picks(candidates: Sequence[Candidate]) -> list[Pick]:
    return first_five_picks(candidates)[:4]


def _long_pitch(candidates: Sequence[Candidate]) -> list[Pick]:
    picks = first_five_picks(candidates)
    return [Pick(movie_id=picks[0].movie_id, pitch="x" * 351), *picks[1:]]


@pytest.mark.parametrize(
    ("picks", "pick_error"),
    [
        (first_five_picks, RuntimeError("LLM down")),
        (_invented_id, None),
        (_duplicate, None),
        (_four_picks, None),
        (_long_pitch, None),
    ],
    ids=["raises", "invented-id", "duplicate", "wrong-count", "pitch-too-long"],
)
def test_search_falls_back_to_results_without_pitches(
    picks: PickScript, pick_error: Exception | None
) -> None:
    llm = ScriptedLanguageModel(picks=picks, pick_error=pick_error)
    response = client_for(llm).post("/search", json=request())

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "results_without_pitches"
    assert [r["id"] for r in body["results"]] == TOP_FIVE_BY_SCORE, "valid films, by score"
    assert all(r["pitch"] is None for r in body["results"])
    assert note_codes(body) == ["pitches_unavailable"]

    if pick_error is not None:
        # Fewer than 5 valid films and the LLM fails: the partial note comes too.
        llm = ScriptedLanguageModel(make_intent(original_languages=["fr"]), pick_error=pick_error)
        body = client_for(llm).post("/search", json=request()).json()
        assert body["state"] == "results_without_pitches"
        assert [r["id"] for r in body["results"]] == [9003]
        assert sorted(note_codes(body)) == ["partial", "pitches_unavailable"]


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"text": ""}, "text"),
        ({"text": "   "}, "text"),
        ({"text": "x" * 501}, "text"),
        ({"country": "FR"}, "country"),
        ({"providers": []}, "providers"),
        ({"providers": [99999]}, "providers"),
        ({"avoid": ["spiders"]}, "avoid"),
        ({"exclude_ids": list(range(5001))}, "exclude_ids"),
    ],
    ids=[
        "empty-text",
        "blank-text",
        "text-over-500",
        "unsupported-country",
        "no-provider",
        "provider-not-in-country",
        "avoid-outside-vocabulary",
        "too-many-exclude-ids",
    ],
)
def test_search_rejects_invalid_input_with_422(changes: dict[str, Any], field: str) -> None:
    llm = ScriptedLanguageModel()
    embedder = FixedEmbedder()
    search = RecordingSearch()
    client = client_for(llm, search, embedder)

    response = client.post("/search", json=request(**changes))

    assert response.status_code == 422
    body = response.json()
    assert body["state"] == "invalid_input"
    assert [e["field"].split(".")[0] for e in body["errors"]] == [field]
    assert body["errors"][0]["message"]
    assert (llm.understand_calls, embedder.calls, len(search.queries), llm.pick_calls) == (
        0,
        0,
        0,
        0,
    ), "no port is called"


@pytest.mark.parametrize(
    "failure", ["understand", "search"], ids=["understand-fails", "search-fails"]
)
def test_search_returns_503_when_understand_or_search_fails(failure: str) -> None:
    if failure == "understand":
        client = client_for(ScriptedLanguageModel(understand_error=RuntimeError("quota")))
    else:
        client = client_for(ScriptedLanguageModel(), FailingSearch())

    response = client.post("/search", json=request())

    assert response.status_code == 503
    body = response.json()
    assert body["state"] == "service_unavailable"
    assert "try again" in body["message"].lower()
    assert "results" not in body


def _case(
    name: str,
    body: dict[str, Any],
    llm: ScriptedLanguageModel,
    search: CandidateSearch | None = None,
) -> EvalCase:
    response = client_for(llm, search).post("/search", json=body)
    intent: QueryIntent | None = llm.intent if llm.understand_calls else None
    return EvalCase(name, body, response.status_code, response.json(), CATALOGUE, intent)


def test_deterministic_evals_pass_at_100_percent() -> None:
    limits_intent = make_intent(
        max_runtime_minutes=100, avoid=["strong_language"], year_min=2000, year_max=2022
    )
    cases = [
        _case("success", request(), ScriptedLanguageModel()),
        _case(
            "limits",
            request(max_runtime=120, max_intensity=3, avoid=["gore"]),
            ScriptedLanguageModel(limits_intent),
            UnfilteredSearch(),
        ),
        _case("kids", request(), ScriptedLanguageModel(make_intent(audience="kids"))),
        _case("teens", request(), ScriptedLanguageModel(make_intent(audience="teens"))),
        _case(
            "exclusions",
            request(exclude_ids=[9001, 9004]),
            ScriptedLanguageModel(),
            UnfilteredSearch(),
        ),
        _case("partial", request(), ScriptedLanguageModel(make_intent(original_languages=["fr"]))),
        _case("zero", request(), ScriptedLanguageModel(make_intent(original_languages=["ja"]))),
        _case(
            "unmapped",
            request(),
            ScriptedLanguageModel(make_intent(unmapped_constraints=["no spiders"])),
        ),
        _case("llm-raises", request(), ScriptedLanguageModel(pick_error=RuntimeError("down"))),
        _case("llm-invents", request(), ScriptedLanguageModel(picks=_invented_id)),
        _case("llm-duplicates", request(), ScriptedLanguageModel(picks=_duplicate)),
        _case("llm-long-pitch", request(), ScriptedLanguageModel(picks=_long_pitch)),
        _case("text-over-500", request(text="x" * 501), ScriptedLanguageModel()),
        _case("text-500", request(text="x" * 500), ScriptedLanguageModel()),
        _case("empty-text", request(text=" "), ScriptedLanguageModel()),
        _case(
            "understand-fails",
            request(),
            ScriptedLanguageModel(understand_error=RuntimeError("down")),
        ),
        _case("search-fails", request(), ScriptedLanguageModel(), FailingSearch()),
    ]

    failures = {c.name: v for c in cases for v in [run_checks(c)] if any(v.values())}
    assert failures == {}, "every deterministic eval passes on every scenario"

    # Each check must catch a planted violation, so none can pass by checking nothing.
    success = cases[0]
    planted: dict[str, EvalCase] = {}

    not_streamable = copy.deepcopy(dict(success.response))
    not_streamable["results"][0] = result_for(CATALOGUE[9012])  # US only
    planted["availability"] = EvalCase("p1", success.request, 200, not_streamable, CATALOGUE)

    too_long = copy.deepcopy(dict(success.response))
    too_long["results"][0] = result_for(CATALOGUE[9014])  # 165 minutes
    planted["limits_as_applied"] = EvalCase(
        "p3", success.request, 200, too_long, CATALOGUE, make_intent(max_runtime_minutes=100)
    )

    planted["input_bounds"] = EvalCase(
        "p4", request(text="x" * 501), 200, success.response, CATALOGUE
    )

    long_pitch = copy.deepcopy(dict(success.response))
    long_pitch["results"][0]["pitch"] = "x" * 351
    planted["pitch_length"] = EvalCase("p2", success.request, 200, long_pitch, CATALOGUE)

    invented = copy.deepcopy(dict(success.response))
    invented["results"][0]["id"] = 424242
    planted["real_ids"] = EvalCase("ids", success.request, 200, invented, CATALOGUE)

    four_results = copy.deepcopy(dict(success.response))
    four_results["results"] = four_results["results"][:4]  # "success" with only 4
    planted["schema"] = EvalCase("schema", success.request, 200, four_results, CATALOGUE)

    for check_name, case in planted.items():
        assert run_checks(case)[check_name], f"{check_name} misses a planted violation"
