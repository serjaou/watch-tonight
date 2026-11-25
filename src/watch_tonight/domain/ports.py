"""Ports: what the use case needs from the outside world (architecture §2).

A `Protocol` is like a C# interface that a class satisfies by its shape, without
declaring `: IMyInterface`; pyright checks the match. Adapters live in `infra`.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.limits import AppliedLimits
from watch_tonight.domain.movie import Candidate, Movie
from watch_tonight.domain.output_checks import Pick


class Usage(BaseModel):
    """Tokens and estimated cost of one LLM call; the trace adds them up."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class Understanding(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: QueryIntent
    usage: Usage


class Pitches(BaseModel):
    model_config = ConfigDict(frozen=True)

    picks: list[Pick]
    usage: Usage


class CandidateQuery(BaseModel):
    """Step 3: the query vector plus the pre-filter the database applies before ranking."""

    model_config = ConfigDict(frozen=True)

    vector: list[float]
    streamable_any: list[str]  # "country:provider" keys of the selected services
    exclude_ids: list[int]
    limits: AppliedLimits
    limit: int


class LanguageModel(Protocol):
    async def understand(self, text: str) -> Understanding:
        """Step 2: the free text as a `QueryIntent`. Raises when it can't."""
        ...

    async def pick_and_pitch(self, intent: QueryIntent, candidates: Sequence[Candidate]) -> Pitches:
        """Step 5: up to 5 picks from `candidates`, each with a pitch about the movie (P2)."""
        ...


class Embedder(Protocol):
    async def embed_query(self, text: str) -> list[float]:
        """Step 3a: the query vector."""
        ...


class CandidateSearch(Protocol):
    async def search(self, query: CandidateQuery) -> list[Candidate]:
        """Step 3b: the nearest movies that pass the pre-filter, best first."""
        ...


class MovieRepository(Protocol):
    async def upsert_many(self, movies: Sequence[Movie]) -> None:
        """Insert or replace movies by id."""
        ...

    async def latest_availability_update(self) -> datetime | None:
        """When availability was last refreshed: the newest `availability_updated_at`
        in the catalogue, or `None` when it is empty (P6)."""
        ...
