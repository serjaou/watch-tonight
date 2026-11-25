"""`QueryIntent`: what step 2 (Understand) turns the free text into (ADR 0005).

Every hard limit mirrors a stored movie field. The list of hard limits will grow (owner,
2026-11-24): genre, director, main cast and keyword flags come after spike feat-026.
"""

from pydantic import BaseModel, ConfigDict

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
    max_runtime_minutes: int | None
    max_intensity: Intensity | None
    avoid: list[ContentWarning]
    year_min: int | None
    year_max: int | None
    audience: Audience | None
    original_languages: list[str]  # ISO 639-1, only when the text asks for one
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
