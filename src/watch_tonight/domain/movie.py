"""A stored movie and its emotional profile (architecture §5, the fields part 1 needs).

Part 2 (feat-030) adds the remaining data-model fields when it maps TMDB bundles.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from watch_tonight.domain.vocabulary import (
    ContentWarning,
    EndingFeel,
    HumorStyle,
    Intensity,
    Pacing,
    Tone,
    ViewingEffort,
)


class Profile(BaseModel):
    """How the movie feels to watch; written offline by the LLM from TMDB data."""

    model_config = ConfigDict(frozen=True)

    tone: list[Tone]
    pacing: Pacing
    intensity: Intensity
    viewing_effort: ViewingEffort
    ending_feel: EndingFeel
    humor_style: HumorStyle
    content_warnings: list[ContentWarning]
    themes: list[str]
    summary: str


class Movie(BaseModel):
    """One catalogue movie. `id` is the TMDB id."""

    model_config = ConfigDict(frozen=True)

    id: int
    title: str
    year: int
    runtime: int
    original_language: str
    collection_id: int | None
    certification_us: str | None
    certification_es: str | None
    poster_path: str
    streamable: list[str]  # "country:provider", flat-rate only (P1)
    availability_updated_at: datetime
    profile: Profile
    embedding: list[float] = Field(default_factory=list[float], repr=False)


class Candidate(BaseModel):
    """A movie returned by the vector search, with its similarity score."""

    model_config = ConfigDict(frozen=True)

    movie: Movie
    score: float
