"""The six deterministic evals (product.md §7; architecture §6).

Each check reads what a client sees (the request body, the HTTP status and the JSON
response), plus the catalogue and the intent that step 2 returned, and lists violations.
An empty list is a pass. Part 4 (feat-029) runs the same checks against the real model.

**Independent of the code they check.** They share no logic or constants with `src/`:
they restate the product rules (product.md P1 to P6, architecture Q16) in their own words,
so a bug in the search code can't hide in its own check. They import only the input
data models (`Movie`, `QueryIntent`).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, cast

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.movie import Movie

# The product's numbers, written out here on purpose (P4, P2, the one task).
PROMPT_MAX_CHARS: Final = 500
PITCH_MAX_CHARS: Final = 350
RESULTS_PER_PAGE: Final = 5
# P5, as product.md words it.
TMDB_NOTICE: Final = (
    "This product uses TMDB and the TMDB APIs but is not endorsed, certified, "
    "or otherwise approved by TMDB."
)
JUSTWATCH_NOTICE: Final = "Streaming availability by JustWatch"


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


# --- P1 ------------------------------------------------------------------------------


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
        listed = [f"{country}:{s['id']}" for s in result["services"]]
        if not listed:
            violations.append(f"{movie.id} lists no service")
        if len(listed) != len(set(listed)):
            violations.append(f"{movie.id} lists a service twice")
        for key in listed:
            if key not in keys or key not in movie.streamable:
                violations.append(f"{movie.id} lists {key}, which is wrong")
    return violations


# --- P3, with the audience rule of architecture Q16 restated -------------------------

_AUDIENCE_RULES: Final[Mapping[str, tuple[set[str], set[str], int, set[str]]]] = {
    # audience: (US ratings, Spanish ratings, max intensity, warnings that exclude)
    "kids": (
        {"G", "PG"},
        {"A", "Ai", "7", "7i"},
        2,
        {
            "violence", "gore", "sexual_content", "nudity", "sexual_violence",
            "horror_scares", "drug_use", "strong_language", "self_harm", "child_harm",
            "animal_harm",
        },
    ),
    "teens": (
        {"G", "PG", "PG-13"},
        {"A", "Ai", "7", "7i", "12"},
        3,
        {"sexual_content", "nudity", "sexual_violence", "gore"},
    ),
}  # fmt: skip


def _suits(movie: Movie, audience: str) -> bool:
    us, es, max_intensity, excluded = _AUDIENCE_RULES[audience]
    no_rating = (None, "", "NR")  # Q16: the first non-empty, non-NR rating counts
    if movie.certification_us not in no_rating:
        return movie.certification_us in us
    if movie.certification_es not in no_rating:
        return movie.certification_es in es
    warnings = set(movie.profile.content_warnings)
    return movie.profile.intensity <= max_intensity and not warnings & excluded


def _broken(movie: Movie, request: Mapping[str, Any], intent: QueryIntent) -> list[str]:
    """The limits as applied: the stricter of the UI and the text, both `avoid` lists."""
    broken: list[str] = []
    runtimes = [v for v in (request.get("max_runtime"), intent.max_runtime_minutes) if v]
    if runtimes and movie.runtime > min(runtimes):
        broken.append("runtime")
    intensities = [v for v in (request.get("max_intensity"), intent.max_intensity) if v]
    if intensities and movie.profile.intensity > min(intensities):
        broken.append("intensity")
    if (set(request.get("avoid", [])) | set(intent.avoid)) & set(movie.profile.content_warnings):
        broken.append("avoid")
    if intent.year_min is not None and movie.year < intent.year_min:
        broken.append("year_min")
    if intent.year_max is not None and movie.year > intent.year_max:
        broken.append("year_max")
    if intent.original_languages and movie.original_language not in intent.original_languages:
        broken.append("original_language")
    if intent.audience is not None and not _suits(movie, intent.audience):
        broken.append("audience")
    return broken


def check_limits_as_applied(case: EvalCase) -> list[str]:
    """P3 on the limits as applied: no result breaks a UI or text limit, or was excluded."""
    if case.status_code != 200 or case.intent is None:
        return []
    excluded = set(case.request.get("exclude_ids", []))
    violations: list[str] = []
    for result in _results(case):
        movie = case.catalogue.get(result["id"])
        if movie is None:
            continue
        broken = _broken(movie, case.request, case.intent)
        if broken:
            violations.append(f"{movie.id} breaks {broken}")
        if movie.id in excluded:
            violations.append(f"{movie.id} was in exclude_ids")
    return violations


# --- P4, P2 length, real ids ---------------------------------------------------------


def check_input_bounds(case: EvalCase) -> list[str]:
    """P4: empty or over-long text is rejected with 422, never truncated and searched."""
    text = case.request.get("text")
    if not isinstance(text, str):
        return []
    length = len(text.strip())
    if (length == 0 or length > PROMPT_MAX_CHARS) and case.status_code != 422:
        return [f"text of {length} characters got HTTP {case.status_code}, not 422"]
    return []


def check_pitch_length(case: EvalCase) -> list[str]:
    """P2's length rule: every pitch is non-empty and at most 350 characters."""
    violations: list[str] = []
    for result in _results(case):
        pitch = result.get("pitch")
        if pitch is not None and not (pitch.strip() and len(pitch) <= PITCH_MAX_CHARS):
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


# --- Schema, written out as JSON shapes --------------------------------------------------

_RESULT_TYPES: Final[Mapping[str, type | tuple[type, ...]]] = {
    "id": int,
    "title": str,
    "year": int,
    "runtime": int,
    "poster_url": str,
    "services": list,
    "pitch": (str, type(None)),
    "tmdb_url": str,
    "availability_updated_at": str,
}


def _keys(name: str, value: Any, expected: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return [f"{name} is not an object"]
    keys = {str(k) for k in cast(dict[object, object], value)}
    return [] if keys == expected else [f"{name} has keys {sorted(keys)}, not {sorted(expected)}"]


def _result_shape(index: int, result: Any) -> list[str]:
    errors = _keys(f"results[{index}]", result, set(_RESULT_TYPES))
    if errors:
        return errors
    for key, kind in _RESULT_TYPES.items():
        if not isinstance(result[key], kind):
            errors.append(f"results[{index}].{key} has the wrong type")
    if errors:
        return errors
    for service in result["services"]:
        errors += _keys(f"results[{index}].services[]", service, {"id", "name"})
    if not result["poster_url"].startswith("https://image.tmdb.org/t/p/"):
        errors.append(f"results[{index}].poster_url is not a TMDB image URL")
    if result["tmdb_url"] != f"https://www.themoviedb.org/movie/{result['id']}":
        errors.append(f"results[{index}].tmdb_url is not the movie's TMDB page")
    try:
        datetime.fromisoformat(result["availability_updated_at"])
    except ValueError:
        errors.append(f"results[{index}].availability_updated_at is not a date (P6)")
    return errors


def _state_rules(response: Mapping[str, Any]) -> list[str]:
    results: list[Any] = response["results"]
    count = len(results)
    codes = {note["code"] for note in response["notes"]}
    pitched = [r["pitch"] is not None for r in results]
    state = response["state"]
    errors: list[str] = []
    if state == "success" and (count != RESULTS_PER_PAGE or not all(pitched)):
        errors.append("success needs exactly 5 results, all with pitches")
    if state == "partial" and (count >= RESULTS_PER_PAGE or not all(pitched)):
        errors.append("partial needs fewer than 5 results, all with pitches")
    if state == "results_without_pitches" and (
        any(pitched) or "pitches_unavailable" not in codes or count > RESULTS_PER_PAGE
    ):
        errors.append("results_without_pitches needs up to 5 results, no pitches, a note")
    if (count < RESULTS_PER_PAGE) != ("partial" in codes):
        errors.append("the partial note must appear exactly when fewer than 5 results")
    return errors


def _success_shape(response: Mapping[str, Any]) -> list[str]:
    errors = _keys("response", response, {"state", "results", "notes", "attribution", "trace"})
    if errors:
        return errors
    if response["state"] not in {"success", "partial", "results_without_pitches"}:
        errors.append(f"unknown state {response['state']!r}")
    for index, result in enumerate(response["results"]):
        errors += _result_shape(index, result)
    for note in response["notes"]:
        errors += _keys("notes[]", note, {"code", "message"})
        if note.get("code") not in {"partial", "pitches_unavailable", "unmapped_constraints"}:
            errors.append(f"unknown note code {note.get('code')!r}")
    if response["attribution"] != {"tmdb": TMDB_NOTICE, "availability": JUSTWATCH_NOTICE}:
        errors.append("attribution differs from P5")
    errors += _keys("trace", response["trace"], {"timings_ms", "tokens", "cost_usd"})
    return errors or _state_rules(response)


def check_schema(case: EvalCase) -> list[str]:
    """The response has the contract's shape for its status, and a consistent state."""
    response = case.response
    if case.status_code == 200:
        return _success_shape(response)
    if case.status_code == 422:
        errors = _keys("response", response, {"state", "errors"})
        if not errors and (response["state"] != "invalid_input" or not response["errors"]):
            errors.append("422 needs state invalid_input and at least one error")
        for error in response.get("errors", []):
            errors += _keys("errors[]", error, {"field", "message"})
        return errors
    if case.status_code == 503:
        errors = _keys("response", response, {"state", "message"})
        if not errors and response["state"] != "service_unavailable":
            errors.append("503 needs state service_unavailable")
        return errors
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
