"""The search request and response contract (spec 18, "Response contract").

The API and, later, the MCP server both use these models, so the two return the same
structured results (US4). Validating the request here is step 1 of the query flow.
"""

from datetime import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from watch_tonight.domain.prompt_validation import validate_mood_prompt
from watch_tonight.domain.providers import PROVIDERS, Country
from watch_tonight.domain.vocabulary import ContentWarning, Intensity

MAX_EXCLUDE_IDS: Final[int] = 5_000  # the size spike 09 tested in one pre-filter
MAX_PITCH_LENGTH: Final[int] = 350  # P2
RESULTS_PER_PAGE: Final[int] = 5

TMDB_NOTICE: Final[str] = (
    "This product uses TMDB and the TMDB APIs but is not endorsed, certified, "
    "or otherwise approved by TMDB."
)  # section 3 of TMDB's API terms (P5)
JUSTWATCH_NOTICE: Final[str] = "Streaming availability by JustWatch"


class SearchRequest(BaseModel):
    """Step 1, Validate. A request that fails here never reaches a port."""

    text: str
    country: Country
    providers: list[int] = Field(min_length=1)
    max_runtime: int | None = Field(default=None, gt=0)
    max_intensity: Intensity | None = None
    avoid: list[ContentWarning] = Field(default_factory=list[ContentWarning])
    exclude_ids: list[int] = Field(default_factory=list[int], max_length=MAX_EXCLUDE_IDS)

    @field_validator("text")
    @classmethod
    def _text_within_bounds(cls, value: str) -> str:
        return validate_mood_prompt(value)  # P4: trims; rejects empty or > 500 chars

    @field_validator("providers")
    @classmethod
    def _providers_known_in_country(cls, value: list[int], info: ValidationInfo) -> list[int]:
        country: Country | None = info.data.get("country")
        if country is None:  # the country error is already reported
            return value
        unknown = [p for p in value if p not in PROVIDERS[country]]
        if unknown:
            raise ValueError(f"Unknown service(s) for {country}: {unknown}")
        return list(dict.fromkeys(value))  # drop repeats, keep the order


ResponseState = Literal["success", "partial", "results_without_pitches"]
NoteCode = Literal["partial", "pitches_unavailable", "unmapped_constraints"]


class Service(BaseModel):
    id: int
    name: str


class MovieResult(BaseModel):
    id: int  # TMDB id; the client sends shown ids back as `exclude_ids` (US3)
    title: str
    year: int
    runtime: int
    poster_url: str
    services: list[Service]  # only the selected services it streams on there (P1)
    pitch: str | None
    tmdb_url: str
    availability_updated_at: datetime  # P6


class Note(BaseModel):
    code: NoteCode
    message: str


class Attribution(BaseModel):
    tmdb: str = TMDB_NOTICE
    availability: str = JUSTWATCH_NOTICE


class Tokens(BaseModel):
    input: int = 0
    output: int = 0


class Trace(BaseModel):
    timings_ms: dict[str, float]
    tokens: Tokens
    cost_usd: float


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ResponseState
    results: list[MovieResult]
    notes: list[Note]
    attribution: Attribution
    trace: Trace


class FieldError(BaseModel):
    field: str
    message: str


class InvalidInputResponse(BaseModel):
    """HTTP 422: the *Invalid input* state."""

    state: Literal["invalid_input"] = "invalid_input"
    errors: list[FieldError]


class ServiceUnavailableResponse(BaseModel):
    """HTTP 503: the *Service unavailable* state. Never carries results (Q8)."""

    state: Literal["service_unavailable"] = "service_unavailable"
    message: str
