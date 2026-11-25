"""Step 4, *Check and rank candidates*: every rule re-checked by value, never by an LLM.

See the query flow in `docs/architecture.md` §3, step 4. The database pre-filters the same
rules in step 3; step 4 checks them again because a rule that must never break should not
rely on one layer (like validating in the domain despite a database CHECK constraint).

Each hard limit is its own unit: a field in `AppliedLimits`, a line in `merge_limits`, a
check function, and an entry in `LIMIT_CHECKS`. Adding one (genre, director, ...) adds a
unit and changes none of the others (owner, 2026-11-24; ADR 0005).
"""

from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from typing import Final

from pydantic import BaseModel, ConfigDict

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.movie import Candidate, Movie
from watch_tonight.domain.search import SearchRequest
from watch_tonight.domain.vocabulary import Audience, ContentWarning


class AppliedLimits(BaseModel):
    """The hard limits in force for one search: UI and text merged (architecture §3, step 2)."""

    model_config = ConfigDict(frozen=True)

    max_runtime: int | None = None
    max_intensity: int | None = None
    avoid: frozenset[ContentWarning] = frozenset()
    year_min: int | None = None
    year_max: int | None = None
    original_languages: frozenset[str] = frozenset()
    audience: Audience | None = None


def _stricter_max(*values: int | None) -> int | None:
    present = [v for v in values if v is not None]
    return min(present) if present else None


def merge_limits(request: SearchRequest, intent: QueryIntent) -> AppliedLimits:
    """When the UI and the text set the same limit, the stricter one applies (P3)."""
    return AppliedLimits(
        max_runtime=_stricter_max(request.max_runtime, intent.max_runtime_minutes),
        max_intensity=_stricter_max(request.max_intensity, intent.max_intensity),
        avoid=frozenset(request.avoid) | frozenset(intent.avoid),
        year_min=intent.year_min,
        year_max=intent.year_max,
        original_languages=frozenset(intent.original_languages),
        audience=intent.audience,
    )


# --- The audience rule (architecture Q16) ------------------------------------------------

_KIDS_US: Final = frozenset({"G", "PG"})
_KIDS_ES: Final = frozenset({"A", "Ai", "7", "7i"})
_KIDS_MAX_INTENSITY: Final = 2
_KIDS_EXCLUDED: Final[frozenset[ContentWarning]] = frozenset(
    {
        "violence", "gore", "sexual_content", "nudity", "sexual_violence", "horror_scares",
        "drug_use", "strong_language", "self_harm", "child_harm", "animal_harm",
    }
)  # fmt: skip
_TEENS_US: Final = frozenset({"G", "PG", "PG-13"})
_TEENS_ES: Final = frozenset({"A", "Ai", "7", "7i", "12"})
_TEENS_MAX_INTENSITY: Final = 3
_TEENS_EXCLUDED: Final[frozenset[ContentWarning]] = frozenset(
    {"sexual_content", "nudity", "sexual_violence", "gore"}
)


def suits_audience(movie: Movie, audience: Audience) -> bool:
    """US certification first, else the Spanish one, else the emotional profile."""
    if audience == "kids":
        us, es, max_intensity, excluded = _KIDS_US, _KIDS_ES, _KIDS_MAX_INTENSITY, _KIDS_EXCLUDED
    else:
        us, es, max_intensity, excluded = (
            _TEENS_US,
            _TEENS_ES,
            _TEENS_MAX_INTENSITY,
            _TEENS_EXCLUDED,
        )
    if movie.certification_us is not None:
        return movie.certification_us in us
    if movie.certification_es is not None:
        return movie.certification_es in es
    profile = movie.profile
    return profile.intensity <= max_intensity and excluded.isdisjoint(profile.content_warnings)


# --- One check per hard limit: True means the movie breaks it ---------------------------


def _breaks_runtime(movie: Movie, limits: AppliedLimits) -> bool:
    return limits.max_runtime is not None and movie.runtime > limits.max_runtime


def _breaks_intensity(movie: Movie, limits: AppliedLimits) -> bool:
    return limits.max_intensity is not None and movie.profile.intensity > limits.max_intensity


def _breaks_avoid(movie: Movie, limits: AppliedLimits) -> bool:
    return not limits.avoid.isdisjoint(movie.profile.content_warnings)


def _breaks_year(movie: Movie, limits: AppliedLimits) -> bool:
    too_old = limits.year_min is not None and movie.year < limits.year_min
    too_new = limits.year_max is not None and movie.year > limits.year_max
    return too_old or too_new


def _breaks_original_language(movie: Movie, limits: AppliedLimits) -> bool:
    return bool(limits.original_languages) and (
        movie.original_language not in limits.original_languages
    )


def _breaks_audience(movie: Movie, limits: AppliedLimits) -> bool:
    return limits.audience is not None and not suits_audience(movie, limits.audience)


LimitCheck = Callable[[Movie, AppliedLimits], bool]

LIMIT_CHECKS: Final[Mapping[str, LimitCheck]] = {
    "runtime": _breaks_runtime,
    "intensity": _breaks_intensity,
    "avoid": _breaks_avoid,
    "year": _breaks_year,
    "original_language": _breaks_original_language,
    "audience": _breaks_audience,
}


def broken_limits(movie: Movie, limits: AppliedLimits) -> list[str]:
    """The names of the hard limits this movie breaks; empty when it passes them all."""
    return [name for name, breaks in LIMIT_CHECKS.items() if breaks(movie, limits)]


def is_streamable(movie: Movie, streamable_keys: Collection[str]) -> bool:
    """P1: streamable on at least one selected service in the selected country."""
    return any(key in streamable_keys for key in movie.streamable)


def passes_checks(
    movie: Movie,
    *,
    streamable_keys: Collection[str],
    exclude_ids: Collection[int],
    limits: AppliedLimits,
) -> bool:
    """Availability (P1), not already shown (US3), and every hard limit (P3)."""
    return (
        is_streamable(movie, streamable_keys)
        and movie.id not in exclude_ids
        and not broken_limits(movie, limits)
    )


def one_per_collection(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Keep the first (best-ranked) film of each collection; films without one all stay."""
    seen: set[int] = set()
    kept: list[Candidate] = []
    for candidate in candidates:
        collection_id = candidate.movie.collection_id
        if collection_id is not None:
            if collection_id in seen:
                continue
            seen.add(collection_id)
        kept.append(candidate)
    return kept


def check_and_rank(
    candidates: Sequence[Candidate],
    *,
    streamable_keys: Collection[str],
    exclude_ids: Collection[int],
    limits: AppliedLimits,
    keep: int,
) -> list[Candidate]:
    """Drop every candidate that breaks a rule, order by score, one film per collection.

    Until the hybrid score (feat-022), candidates are ordered by similarity alone; ties
    are broken by id so the order is stable.
    """
    valid = [
        c
        for c in candidates
        if passes_checks(
            c.movie, streamable_keys=streamable_keys, exclude_ids=exclude_ids, limits=limits
        )
    ]
    ranked = sorted(valid, key=lambda c: (-c.score, c.movie.id))
    return one_per_collection(ranked)[:keep]
