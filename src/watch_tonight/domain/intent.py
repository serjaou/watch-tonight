"""`QueryIntent`: what step 2 (Understand) turns the free text into (ADR 0005).

Every hard limit mirrors a stored movie field. The list of hard limits will grow (owner,
2026-11-24): genre, director, main cast and keyword flags come after spike feat-026.
"""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from watch_tonight.domain.vocabulary import (
    AcclaimPreference,
    Audience,
    ContentWarning,
    EndingFeel,
    EraMode,
    HumorStyle,
    Intensity,
    Pacing,
    Specificity,
    Tone,
    ViewingEffort,
)


class QueryIntent(BaseModel):
    """Step 2 output. No defaults on purpose: the LLM must fill in every field."""

    model_config = ConfigDict(frozen=True)

    # Channel 1: hard limits, applied by the data layer and re-checked in step 4.
    # The bounds turn a nonsense value into a validation error, which the part-4 adapter
    # feeds back to the model, instead of a silent zero-result search.
    max_runtime_minutes: Annotated[int, Field(gt=0)] | None
    max_intensity: Intensity | None
    avoid: list[ContentWarning]
    year_min: Annotated[int, Field(ge=1880, le=2100)] | None
    year_max: Annotated[int, Field(ge=1880, le=2100)] | None
    audience: Audience | None
    # ISO 639-1 codes, only when the text asks for a language.
    original_languages: list[Annotated[str, Field(pattern=r"^[a-z]{2}$")]]
    # Channel 2: meaning, for the embedding and as context for step 5.
    tone: list[Tone]
    pacing: Pacing | None
    viewing_effort: ViewingEffort | None
    ending_feel: EndingFeel | None
    humor_style: HumorStyle | None
    themes: list[str]
    semantic_description: str
    # Channel 3: ranking hints for the hybrid score (feat-022).
    specificity: Specificity
    era_mode: EraMode
    acclaim_preference: AcclaimPreference
    # Things the text asks for that the vocabulary can't express (Q18).
    unmapped_constraints: list[str]

    @model_validator(mode="after")
    def _year_range_in_order(self) -> Self:
        if (
            self.year_min is not None
            and self.year_max is not None
            and self.year_min > self.year_max
        ):
            raise ValueError(f"year_min {self.year_min} is after year_max {self.year_max}")
        return self
