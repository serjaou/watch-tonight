"""An in-memory catalogue: `MovieRepository` and `CandidateSearch` without a database.

Part 1 of the walking skeleton runs on it; afterwards it stays as the fast test double
for the Atlas adapters of part 2 (feat-030).
"""

import math
from collections.abc import Iterable, Sequence
from datetime import datetime

from watch_tonight.domain.limits import passes_checks
from watch_tonight.domain.movie import Candidate, Movie
from watch_tonight.domain.ports import CandidateQuery


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vectors differ in length: {len(a)} and {len(b)}")
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm


class InMemoryCatalogue:
    """Exact (brute-force) vector search with the same pre-filter meaning as Atlas."""

    def __init__(self, movies: Iterable[Movie] = ()) -> None:
        self._movies: dict[int, Movie] = {m.id: m for m in movies}

    async def upsert_many(self, movies: Sequence[Movie]) -> None:
        for movie in movies:
            self._movies[movie.id] = movie

    async def latest_availability_update(self) -> datetime | None:
        return max((m.availability_updated_at for m in self._movies.values()), default=None)

    async def search(self, query: CandidateQuery) -> list[Candidate]:
        exclude = set(query.exclude_ids)
        matches = [
            Candidate(movie=m, score=cosine_similarity(query.vector, m.embedding))
            for m in self._movies.values()
            if m.embedding  # like Atlas, a movie without a vector is never a candidate
            and passes_checks(
                m, streamable_keys=query.streamable_any, exclude_ids=exclude, limits=query.limits
            )
        ]
        matches.sort(key=lambda c: (-c.score, c.movie.id))
        return matches[: query.limit]
