"""A stored movie and its emotional profile (architecture §5, the fields part 1 needs).

Part 2 (feat-030) adds the remaining data-model fields when it maps TMDB bundles.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class Credits(BaseModel):
    model_config = ConfigDict(frozen=True)

    directors: list[str] = Field(default_factory=list[str])
    cast: list[str] = Field(default_factory=list[str])  # the top 5 billed


class Movie(BaseModel):
    """One catalogue movie (architecture §5). `id` is the TMDB id.

    The fields after `embedding` are optional: part 1's fixtures don't need them, and the
    signals that come from later features (Wikidata, the WR score) stay `None` until then.
    """

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
    # TMDB metadata
    original_title: str | None = None
    genres: list[str] = Field(default_factory=list[str])
    keywords: list[str] = Field(default_factory=list[str])
    overview: str | None = None
    tagline: str | None = None
    credits: Credits = Field(default_factory=Credits)
    tmdb_vote_average: float | None = None
    tmdb_vote_count: int | None = None
    tmdb_popularity: float | None = None
    # Quality signals and retention (feat-020)
    quality_score: float | None = None
    critic_score: float | None = None
    awards_count: int | None = None
    unstreamable_since: datetime | None = None
    # Provenance: what built the profile and the vector
    embedding_model: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    source_hash: str | None = None
    updated_at: datetime | None = None

    @field_validator("certification_us", "certification_es")
    @classmethod
    def _no_rating_is_none(cls, value: str | None) -> str | None:
        """An empty or `NR` rating counts as no rating (architecture Q16)."""
        if value is None or value.strip() in {"", "NR"}:
            return None
        return value.strip()


class Candidate(BaseModel):
    """A movie returned by the vector search, with its similarity score."""

    model_config = ConfigDict(frozen=True)

    movie: Movie
    score: float
