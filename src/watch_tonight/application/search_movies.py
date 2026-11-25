"""`SearchMovies`: the one online use case (architecture §3, "Query flow").

The API and the MCP server call it and return the same response. Step 1 (Validate) has
already happened when a `SearchRequest` exists: Pydantic validated it on construction.
"""

import logging
import time
from collections.abc import Callable, Sequence
from typing import Final

from watch_tonight.domain.errors import ServiceUnavailableError
from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.limits import check_and_rank, merge_limits
from watch_tonight.domain.movie import Candidate
from watch_tonight.domain.output_checks import check_picks
from watch_tonight.domain.ports import (
    CandidateQuery,
    CandidateSearch,
    Embedder,
    LanguageModel,
    Pitches,
    Usage,
)
from watch_tonight.domain.providers import PROVIDERS, streamable_key
from watch_tonight.domain.search import (
    RESULTS_PER_PAGE,
    Attribution,
    MovieResult,
    Note,
    ResponseState,
    SearchRequest,
    SearchResponse,
    Service,
    Tokens,
    Trace,
)

logger = logging.getLogger(__name__)

SEARCH_LIMIT: Final[int] = 150  # K: candidates from the vector search (ADR 0008)
CANDIDATES_FOR_PITCH: Final[int] = 25  # what step 5 sees

POSTER_BASE_URL: Final[str] = "https://image.tmdb.org/t/p/w342"
TMDB_MOVIE_URL: Final[str] = "https://www.themoviedb.org/movie/"

PARTIAL_MESSAGE: Final[str] = "Fewer than 5 movies match. Try adding a service or relaxing a limit."
PITCHES_UNAVAILABLE_MESSAGE: Final[str] = "Pitches are temporarily unavailable."


class _Stopwatch:
    """Collects stage timings in milliseconds for the trace."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._last = clock()
        self.timings_ms: dict[str, float] = {}

    def lap(self, stage: str) -> None:
        now = self._clock()
        self.timings_ms[stage] = round((now - self._last) * 1000, 3)
        self._last = now


class SearchMovies:
    """Steps 2 to 7 of the query flow, over the ports. No retry loop here: in part 4 the
    LLM adapter retries once with the error fed back (ADR 0006); this class re-checks
    whatever the adapter returns, as a final guard."""

    def __init__(
        self,
        language_model: LanguageModel,
        embedder: Embedder,
        candidate_search: CandidateSearch,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._language_model = language_model
        self._embedder = embedder
        self._candidate_search = candidate_search
        self._clock = clock

    async def execute(self, request: SearchRequest) -> SearchResponse:
        watch = _Stopwatch(self._clock)
        usages: list[Usage] = []

        # Step 2 · Understand. Without an intent there is nothing honest to search for.
        try:
            understanding = await self._language_model.understand(request.text)
        except Exception as error:  # any adapter failure: down, quota, invalid twice
            logger.exception("Step 2 (understand) failed")
            raise ServiceUnavailableError("understand") from error
        intent = understanding.intent
        usages.append(understanding.usage)
        limits = merge_limits(request, intent)
        watch.lap("understand")

        # Step 3 · Retrieve: embed the description, then the filtered vector search.
        keys = [streamable_key(request.country, p) for p in request.providers]
        try:
            vector = await self._embedder.embed_query(intent.semantic_description)
            watch.lap("embed")
            candidates = await self._candidate_search.search(
                CandidateQuery(
                    vector=vector,
                    streamable_any=keys,
                    exclude_ids=request.exclude_ids,
                    limits=limits,
                    limit=SEARCH_LIMIT,
                )
            )
        except Exception as error:
            logger.exception("Step 3 (retrieve) failed")
            raise ServiceUnavailableError("retrieve") from error
        watch.lap("retrieve")

        # Step 4 · Check and rank: re-check every rule by value (domain/limits.py).
        valid = check_and_rank(
            candidates,
            streamable_keys=keys,
            exclude_ids=set(request.exclude_ids),
            limits=limits,
            keep=CANDIDATES_FOR_PITCH,
        )
        watch.lap("check")

        # Steps 5 and 6 · Pick and pitch, then check the answer. Skipped when nothing passed.
        pitches = await self._pick_and_pitch(intent, valid) if valid else None
        if valid:
            watch.lap("pick_and_pitch")
        if pitches is not None:
            usages.append(pitches.usage)

        # Step 7 · Respond.
        notes: list[Note] = []
        state: ResponseState
        if valid and pitches is None:
            state = "results_without_pitches"
            chosen = [(c, None) for c in valid[:RESULTS_PER_PAGE]]
            notes.append(Note(code="pitches_unavailable", message=PITCHES_UNAVAILABLE_MESSAGE))
        else:
            by_id = {c.movie.id: c for c in valid}
            chosen = [(by_id[p.movie_id], p.pitch) for p in pitches.picks] if pitches else []
            state = "success" if len(valid) >= RESULTS_PER_PAGE else "partial"
        if len(valid) < RESULTS_PER_PAGE:
            notes.append(Note(code="partial", message=PARTIAL_MESSAGE))
        if intent.unmapped_constraints:
            message = "We couldn't apply: " + ", ".join(intent.unmapped_constraints)
            notes.append(Note(code="unmapped_constraints", message=message))

        return SearchResponse(
            state=state,
            results=[_to_result(c, pitch, request) for c, pitch in chosen],
            notes=notes,
            attribution=Attribution(),
            trace=Trace(
                timings_ms=watch.timings_ms,
                tokens=Tokens(
                    input=sum(u.input_tokens for u in usages),
                    output=sum(u.output_tokens for u in usages),
                ),
                cost_usd=sum(u.cost_usd for u in usages),
            ),
        )

    async def _pick_and_pitch(
        self, intent: QueryIntent, candidates: Sequence[Candidate]
    ) -> Pitches | None:
        """Step 5 and the step-6 guard. `None` means *Results without pitches* (Q8)."""
        try:
            pitches = await self._language_model.pick_and_pitch(intent, candidates)
        except Exception:
            logger.exception("Step 5 (pick and pitch) failed")
            return None
        errors = check_picks(pitches.picks, [c.movie.id for c in candidates])
        if errors:
            logger.warning("Step 6 rejected the LLM's output: %s", errors)
            return None
        return pitches


def _to_result(candidate: Candidate, pitch: str | None, request: SearchRequest) -> MovieResult:
    movie = candidate.movie
    names = PROVIDERS[request.country]
    services = [
        Service(id=p, name=names[p])
        for p in request.providers
        if streamable_key(request.country, p) in movie.streamable
    ]
    return MovieResult(
        id=movie.id,
        title=movie.title,
        year=movie.year,
        runtime=movie.runtime,
        poster_url=POSTER_BASE_URL + movie.poster_path,
        services=services,
        pitch=pitch,
        tmdb_url=f"{TMDB_MOVIE_URL}{movie.id}",
        availability_updated_at=movie.availability_updated_at,
    )
