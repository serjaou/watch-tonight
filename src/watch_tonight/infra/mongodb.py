"""MongoDB Atlas adapters: `MovieRepository` and `CandidateSearch` (architecture §2, §5).

They run on `mongodb-atlas-local` now and on Atlas M0 later (feat-021). The pre-filter has
the same meaning as the step-4 checks in `domain/limits.py`; step 4 re-checks it anyway.
"""

import asyncio
import contextlib
import logging
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Final

from pymongo import AsyncMongoClient, ReplaceOne
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import CollectionInvalid
from pymongo.operations import SearchIndexModel

from watch_tonight.domain.limits import AUDIENCE_RULES
from watch_tonight.domain.movie import Candidate, Movie
from watch_tonight.domain.ports import CandidateQuery
from watch_tonight.domain.vocabulary import Audience

logger = logging.getLogger(__name__)

Document = dict[str, Any]

# The local image, pinned to a dated build of MongoDB 8.0 like Atlas M0. compose.yaml and
# the integration tests use it; a unit test checks compose.yaml matches.
ATLAS_LOCAL_IMAGE: Final[str] = "mongodb/mongodb-atlas-local:8.0.38-20261124T121746Z"
MOVIES: Final[str] = "movies"
VECTOR_INDEX: Final[str] = "movies_vector"
EMBEDDING_DIMENSIONS: Final[int] = 384  # BAAI/bge-small-en-v1.5 (ADR 0007)
# Every path the pre-filter uses must be declared, or Atlas raises OperationFailure (spike 09).
FILTER_PATHS: Final[tuple[str, ...]] = (
    "_id",
    "streamable",
    "runtime",
    "year",
    "original_language",
    "certification_us",
    "certification_es",
    "profile.intensity",
    "profile.content_warnings",
)
# Whether Atlas holds the audience rule (an $or with the no-rating case) as a pre-filter.
# Set from the feat-030 integration test; when False, step 4 alone applies the rule.
AUDIENCE_IN_PREFILTER: Final[bool] = True


def connect(
    uri: str, *, timeout_ms: int = 3_000, operation_timeout_ms: int = 10_000
) -> AsyncMongoClient[Document]:
    """A client with time-zone-aware dates and bounded waits (Q8: a database that is down
    or stalls is a 503, never a hang): `timeout_ms` to find the server, and
    `operation_timeout_ms` for a reply on an open connection (`socketTimeoutMS`).

    Not pymongo's `timeoutMS`: when set, it replaces the short server-selection timeout,
    so a database that is down took 10 s instead of 3 s to fail (feat-030 test).
    """
    return AsyncMongoClient(
        uri,
        tz_aware=True,
        serverSelectionTimeoutMS=timeout_ms,
        socketTimeoutMS=operation_timeout_ms,
    )


# --- Documents ---------------------------------------------------------------------------


def movie_to_document(movie: Movie) -> Document:
    document = movie.model_dump(exclude={"id"})
    document["_id"] = movie.id
    return document


def document_to_movie(document: Mapping[str, Any]) -> Movie:
    data = {k: v for k, v in document.items() if k not in {"_id", "score"}}
    return Movie.model_validate({"id": document["_id"], **data})


# --- The pre-filter -----------------------------------------------------------------------


def audience_clause(audience: Audience) -> Document:
    """Architecture Q16 as a filter: the US rating, else the Spanish one, else the profile."""
    rule = AUDIENCE_RULES[audience]
    no_us = {"certification_us": {"$eq": None}}
    no_es = {"certification_es": {"$eq": None}}
    return {
        "$or": [
            {"certification_us": {"$in": sorted(rule.us_ratings)}},
            {"$and": [no_us, {"certification_es": {"$in": sorted(rule.es_ratings)}}]},
            {
                "$and": [
                    no_us,
                    no_es,
                    {"profile.intensity": {"$lte": rule.max_intensity}},
                    {"profile.content_warnings": {"$nin": sorted(rule.excluded_warnings)}},
                ]
            },
        ]
    }


def build_prefilter(query: CandidateQuery, *, audience_in_prefilter: bool) -> Document:
    """Step 3's pre-filter: availability (P1), exclusions (US3) and every hard limit (P3)."""
    limits = query.limits
    clauses: list[Document] = [{"streamable": {"$in": list(query.streamable_any)}}]
    if query.exclude_ids:
        clauses.append({"_id": {"$nin": list(query.exclude_ids)}})
    if limits.max_runtime is not None:
        clauses.append({"runtime": {"$lte": limits.max_runtime}})
    if limits.max_intensity is not None:
        clauses.append({"profile.intensity": {"$lte": limits.max_intensity}})
    if limits.avoid:
        clauses.append({"profile.content_warnings": {"$nin": sorted(limits.avoid)}})
    if limits.year_min is not None:
        clauses.append({"year": {"$gte": limits.year_min}})
    if limits.year_max is not None:
        clauses.append({"year": {"$lte": limits.year_max}})
    if limits.original_languages:
        clauses.append({"original_language": {"$in": sorted(limits.original_languages)}})
    if limits.audience is not None and audience_in_prefilter:
        clauses.append(audience_clause(limits.audience))
    return {"$and": clauses}


# --- Index lifecycle (spike 09 never verified update and drop) -----------------------------


def vector_index_definition(filter_paths: Sequence[str] = FILTER_PATHS) -> Document:
    return {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": EMBEDDING_DIMENSIONS,
                "similarity": "cosine",
            },
            *({"type": "filter", "path": path} for path in filter_paths),
        ]
    }


def _paths(definition: Mapping[str, Any]) -> set[str]:
    """What makes two vector index definitions the same for us: every field's path, type,
    and for the vector field its dimensions and similarity."""
    return {
        "|".join(str(field.get(key, "")) for key in ("path", "type", "numDimensions", "similarity"))
        for field in definition.get("fields", [])
    }


async def search_index_info(collection: AsyncCollection[Document], name: str) -> Document | None:
    cursor = await collection.list_search_indexes(name)
    async for info in cursor:
        return dict(info)
    return None


async def wait_until_queryable(
    collection: AsyncCollection[Document],
    name: str,
    definition: Mapping[str, Any],
    *,
    timeout_s: float = 120,
) -> None:
    """Indexes build asynchronously: wait until this definition is READY and queryable."""
    deadline = asyncio.get_running_loop().time() + timeout_s
    while True:
        info = await search_index_info(collection, name)
        if info is not None:
            if info.get("status") == "FAILED":
                raise RuntimeError(f"Search index {name!r} failed to build: {info}")
            latest = info.get("latestDefinition", {})
            if (
                info.get("queryable")
                and info.get("status") == "READY"
                and _paths(latest) == _paths(definition)
            ):
                return
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError(f"Search index {name!r} not queryable after {timeout_s}s: {info}")
        await asyncio.sleep(0.5)


async def create_vector_index(
    collection: AsyncCollection[Document],
    definition: Mapping[str, Any],
    *,
    name: str = VECTOR_INDEX,
    timeout_s: float = 120,
) -> None:
    model = SearchIndexModel(definition=dict(definition), name=name, type="vectorSearch")
    await collection.create_search_index(model)
    await wait_until_queryable(collection, name, definition, timeout_s=timeout_s)


async def update_vector_index(
    collection: AsyncCollection[Document],
    definition: Mapping[str, Any],
    *,
    name: str = VECTOR_INDEX,
    timeout_s: float = 120,
) -> None:
    """Replace the definition by dropping and re-creating the index.

    `mongodb-atlas-local` 8.0.38 rejects `updateSearchIndex` for vector indexes: without a
    type it reads the definition as a text index (`"mappings" is required`), and it has no
    `type` field (feat-030, verified 2026-11-25). So searches fail (503) until the new index
    is queryable (an empty result on a missing index is turned into an error in
    `MongoCatalogue.search`). Atlas documents an in-place update; feat-021 checks it on M0.
    """
    await drop_vector_index(collection, name=name, timeout_s=timeout_s)
    await create_vector_index(collection, definition, name=name, timeout_s=timeout_s)


async def drop_vector_index(
    collection: AsyncCollection[Document], *, name: str = VECTOR_INDEX, timeout_s: float = 120
) -> None:
    await collection.drop_search_index(name)
    deadline = asyncio.get_running_loop().time() + timeout_s
    while await search_index_info(collection, name) is not None:
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError(f"Search index {name!r} still present after {timeout_s}s")
        await asyncio.sleep(0.5)


async def ensure_catalogue(database: AsyncDatabase[Document]) -> None:
    """Make the movies collection ready: the collection, the freshness index, and a vector
    index with today's filter paths (created, replaced if its paths changed, or waited for
    if a previous run left it building)."""
    with contextlib.suppress(CollectionInvalid):  # it already exists
        await database.create_collection(MOVIES)
    movies = database[MOVIES]
    await movies.create_index("availability_updated_at")
    wanted = vector_index_definition()
    info = await search_index_info(movies, VECTOR_INDEX)
    if info is None:
        await create_vector_index(movies, wanted)
    elif _paths(info.get("latestDefinition", {})) != _paths(wanted):
        await update_vector_index(movies, wanted)
    else:
        await wait_until_queryable(movies, VECTOR_INDEX, wanted)


async def wait_until_searchable(
    database: AsyncDatabase[Document], *, timeout_s: float = 120
) -> int:
    """After first-time inserts, wait until the vector index sees every stored movie with a
    vector. The search index syncs from the collection asynchronously (like an eventually
    consistent read model). It counts documents, so after replacing existing ones it can
    return before their new values are indexed. Returns the number of movies found.
    """
    movies = database[MOVIES]
    expected = await movies.count_documents({"embedding.0": {"$exists": True}})
    deadline = asyncio.get_running_loop().time() + timeout_s
    while True:
        probe = [0.0] * EMBEDDING_DIMENSIONS
        probe[0] = 1.0
        pipeline: list[Document] = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": probe,
                    "exact": True,  # exact search: no numCandidates cap
                    "limit": max(expected, 1),
                }
            },
            {"$count": "found"},
        ]
        cursor = await movies.aggregate(pipeline)
        rows = await cursor.to_list()
        found = int(rows[0]["found"]) if rows else 0
        if found >= expected:
            return found
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError(f"Vector index sees {found} of {expected} movies")
        await asyncio.sleep(0.5)


# --- The adapter ---------------------------------------------------------------------------


class MongoCatalogue:
    """`MovieRepository` and `CandidateSearch` on one MongoDB database."""

    def __init__(
        self,
        database: AsyncDatabase[Document],
        *,
        audience_in_prefilter: bool = AUDIENCE_IN_PREFILTER,
    ) -> None:
        self._movies: AsyncCollection[Document] = database[MOVIES]
        self.audience_in_prefilter = audience_in_prefilter

    async def upsert_many(self, movies: Sequence[Movie]) -> None:
        if movies:
            await self._movies.bulk_write(
                [ReplaceOne({"_id": m.id}, movie_to_document(m), upsert=True) for m in movies]
            )

    async def latest_availability_update(self) -> datetime | None:
        document = await self._movies.find_one(
            {}, projection={"availability_updated_at": 1}, sort=[("availability_updated_at", -1)]
        )
        if document is None:
            return None
        latest: datetime = document["availability_updated_at"]
        return latest

    async def search(self, query: CandidateQuery) -> list[Candidate]:
        pipeline: list[Document] = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": list(query.vector),
                    # Approximate search over this many neighbours; tuned at full scale in
                    # feat-021 (architecture §3, step 3).
                    "numCandidates": min(10_000, query.limit * 20),
                    "limit": query.limit,
                    "filter": build_prefilter(
                        query, audience_in_prefilter=self.audience_in_prefilter
                    ),
                }
            },
            {"$set": {"score": {"$meta": "vectorSearchScore"}}},
            {"$unset": "embedding"},
        ]
        cursor = await self._movies.aggregate(pipeline)
        candidates = [
            Candidate(movie=document_to_movie(document), score=float(document["score"]))
            async for document in cursor
        ]
        if not candidates:
            # $vectorSearch on a missing index returns nothing instead of an error. An empty
            # answer is only honest if the index exists and is queryable; otherwise raise,
            # so the search is a 503, not an empty *Partial* (Q8).
            info = await search_index_info(self._movies, VECTOR_INDEX)
            if info is None or not info.get("queryable"):
                raise RuntimeError(f"Vector index {VECTOR_INDEX!r} is missing or not queryable")
        return candidates
