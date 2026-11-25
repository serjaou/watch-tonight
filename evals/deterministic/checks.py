"""The six deterministic evals (product.md §7; architecture §6).

Each check reads what a client sees (the request body, the HTTP status and the JSON
response), plus the catalogue and the intent that step 2 returned, and lists violations.
An empty list is a pass. Part 4 (feat-029) runs the same checks against the real model.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from pydantic import ValidationError

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.limits import broken_limits, merge_limits
from watch_tonight.domain.movie import Movie
from watch_tonight.domain.prompt_validation import MAX_PROMPT_LENGTH
from watch_tonight.domain.search import (
    MAX_PITCH_LENGTH,
    RESULTS_PER_PAGE,
    InvalidInputResponse,
    SearchRequest,
    SearchResponse,
    ServiceUnavailableResponse,
)


@dataclass(frozen=True)
class EvalCase:
    name: str
    request: Mapping[str, Any]  # the JSON body sent to POST /search
    status_code: int
    response: Mapping[str, Any]  # the JSON body received
    catalogue: Mapping[int, Movie]
    intent: QueryIntent | None = None  # what step 2 returned; None if it never ran


def _results(case: EvalCase) -> Sequence[Mapping[str, Any]]:
    if case.status_code != 200:
        return []
    results: Sequence[Mapping[str, Any]] = case.response.get("results", [])
    return results


def check_availability(case: EvalCase) -> list[str]:
    """P1: every result is streamable on a selected service in the selected country."""
    country = case.request.get("country")
    keys = {f"{country}:{p}" for p in case.request.get("providers", [])}
    violations: list[str] = []
    for result in _results(case):
        movie = case.catalogue.get(result["id"])
        if movie is None:
            continue  # check_real_ids reports it
        if keys.isdisjoint(movie.streamable):
            violations.append(f"{movie.id} is not streamable on the selected services")
        if not result["services"]:
            violations.append(f"{movie.id} lists no service")
        for service in result["services"]:
            key = f"{country}:{service['id']}"
            if key not in keys or key not in movie.streamable:
                violations.append(f"{movie.id} lists service {service['id']}, which is wrong")
    return violations


def check_limits_as_applied(case: EvalCase) -> list[str]:
    """P3 on the limits as applied: no result breaks a merged UI/text limit or is excluded."""
    if case.status_code != 200 or case.intent is None:
        return []
    request = SearchRequest.model_validate(case.request)
    limits = merge_limits(request, case.intent)
    violations: list[str] = []
    for result in _results(case):
        movie = case.catalogue.get(result["id"])
        if movie is None:
            continue
        broken = broken_limits(movie, limits)
        if broken:
            violations.append(f"{movie.id} breaks {broken}")
        if movie.id in request.exclude_ids:
            violations.append(f"{movie.id} was in exclude_ids")
    return violations


def check_input_bounds(case: EvalCase) -> list[str]:
    """P4: empty or over-long text is rejected with 422, never truncated and searched."""
    text = case.request.get("text")
    if not isinstance(text, str):
        return []
    length = len(text.strip())
    if (length == 0 or length > MAX_PROMPT_LENGTH) and case.status_code != 422:
        return [f"text of {length} characters got HTTP {case.status_code}, not 422"]
    return []


def check_pitch_length(case: EvalCase) -> list[str]:
    """P2's length rule: every pitch is non-empty and at most 350 characters."""
    violations: list[str] = []
    for result in _results(case):
        pitch = result.get("pitch")
        if pitch is not None and not (len(pitch.strip()) > 0 and len(pitch) <= MAX_PITCH_LENGTH):
            violations.append(f"{result['id']} has a pitch of {len(pitch)} characters")
    return violations


def check_real_ids(case: EvalCase) -> list[str]:
    """Every result is a real catalogue movie, with its real title (nothing invented)."""
    violations: list[str] = []
    for result in _results(case):
        movie = case.catalogue.get(result["id"])
        if movie is None:
            violations.append(f"{result['id']} is not in the catalogue")
        elif result["title"] != movie.title:
            violations.append(f"{movie.id} has title {result['title']!r}, not {movie.title!r}")
    return violations


def _state_rules(response: SearchResponse) -> list[str]:
    count = len(response.results)
    codes = {note.code for note in response.notes}
    pitched = [r.pitch is not None for r in response.results]
    violations: list[str] = []
    if response.state == "success" and (count != RESULTS_PER_PAGE or not all(pitched)):
        violations.append("success needs exactly 5 results, all with pitches")
    if response.state == "partial" and (count >= RESULTS_PER_PAGE or not all(pitched)):
        violations.append("partial needs fewer than 5 results, all with pitches")
    if response.state == "results_without_pitches" and (
        any(pitched) or "pitches_unavailable" not in codes or count > RESULTS_PER_PAGE
    ):
        violations.append("results_without_pitches needs up to 5 results, no pitches, a note")
    if (count < RESULTS_PER_PAGE) != ("partial" in codes):
        violations.append("the partial note must appear exactly when fewer than 5 results")
    return violations


def check_schema(case: EvalCase) -> list[str]:
    """The response matches the contract for its status, and its state is consistent."""
    try:
        if case.status_code == 200:
            return _state_rules(SearchResponse.model_validate(case.response))
        if case.status_code == 422:
            InvalidInputResponse.model_validate(case.response)
            return []
        if case.status_code == 503:
            ServiceUnavailableResponse.model_validate(case.response)
            return [] if "results" not in case.response else ["503 must not carry results"]
    except ValidationError as error:
        return [f"schema: {error.error_count()} error(s): {error.errors()[0]['msg']}"]
    return [f"unexpected HTTP status {case.status_code}"]


Check = Callable[[EvalCase], list[str]]

CHECKS: Final[Mapping[str, Check]] = {
    "availability": check_availability,
    "limits_as_applied": check_limits_as_applied,
    "input_bounds": check_input_bounds,
    "pitch_length": check_pitch_length,
    "real_ids": check_real_ids,
    "schema": check_schema,
}


def run_checks(case: EvalCase) -> dict[str, list[str]]:
    """Every check on one case; a passing case maps each name to an empty list."""
    return {name: check(case) for name, check in CHECKS.items()}
