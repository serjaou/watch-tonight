"""feat-016 spike Q3: candidate v1 schemas — movie profile <-> QueryIntent mirror. THROWAWAY.

Every QueryIntent field maps 1-to-1 onto a stored movie field (spike doc §2 Gap B):
  channel 1 (hard $vectorSearch pre-filters) -> runtime, year, certification_us,
            original_language, profile.intensity, profile.content_warnings
  channel 2 (symmetric embedding template)   -> profile.tone/pacing/viewing_effort/
            ending_feel/humor_style/themes/summary
  channel 3 (step-4 ranking controls)        -> quality_score, popularity, year, collection_id
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Tone = Literal[
    "light", "funny", "heartwarming", "romantic", "uplifting", "cozy", "whimsical",
    "thoughtful", "melancholic", "dark", "gritty", "tense", "scary", "exciting", "epic",
    "weird", "satirical",
]  # fmt: skip
Pacing = Literal["slow", "medium", "fast"]
ViewingEffort = Literal["comfort_background", "easy", "engaging", "demanding"]
EndingFeel = Literal[
    "uplifting", "warm_resolved", "bittersweet", "tense_cathartic", "bleak_or_ambiguous"
]
HumorStyle = Literal[
    "none", "witty_dry", "warm_gentle", "absurd_satirical", "broad_slapstick", "dark_humor"
]
ContentWarning = Literal[
    "violence", "gore", "sexual_content", "nudity", "strong_language", "drug_use",
    "self_harm", "animal_harm", "child_harm", "sexual_violence", "horror_scares",
    "flashing_lights",
]  # fmt: skip
Intensity = Literal[1, 2, 3, 4, 5]


class Profile(BaseModel):
    """movies.profile (LLM, offline, once per movie)."""

    tone: list[Tone]  # 1-3
    pacing: Pacing
    intensity: Intensity
    viewing_effort: ViewingEffort
    ending_feel: EndingFeel
    humor_style: HumorStyle
    content_warnings: list[ContentWarning]
    themes: list[str]  # 1-5 short English phrases
    summary: str  # <= 400 chars: how it feels to watch, no plot spoilers


class QueryIntent(BaseModel):
    """Step 2 output (LLM, online). Every field mirrors a stored movie field."""

    # channel 1: hard pre-filters
    max_runtime_minutes: int | None
    max_intensity: Intensity | None
    avoid: list[ContentWarning]
    year_min: int | None
    year_max: int | None
    audience: Literal["kids", "teens"] | None  # -> certification_us (G/PG, <=PG-13)
    original_languages: list[str]  # ISO 639-1, only when the text asks for one
    # channel 2: symmetric embedding template
    tone: list[Tone]
    pacing: Pacing | None
    viewing_effort: ViewingEffort | None
    ending_feel: EndingFeel | None
    humor_style: HumorStyle | None
    themes: list[str]
    semantic_description: str  # 2-3 sentences in the same style as profile.summary
    # channel 3: step-4 ranking controls
    specificity: Literal["broad", "medium", "specific"]
    era_mode: Literal["modern_default", "classic_or_any_era"]
    acclaim_preference: Literal["crowd_pleaser", "critically_acclaimed", "hidden_gem", "any"]


def template(
    tone: list[str],
    pacing: str | None,
    effort: str | None,
    ending: str | None,
    humor: str | None,
    themes: list[str],
    summary: str,
) -> str:
    """The one text format embedded for both movies (offline) and queries (online)."""
    parts = [
        ("Tone", ", ".join(tone)),
        ("Pacing", pacing or ""),
        ("Effort", (effort or "").replace("_", " ")),
        ("Ending", (ending or "").replace("_", " ")),
        ("Humor", (humor or "").replace("_", " ") if humor != "none" else ""),
        ("Themes", ", ".join(themes)),
        ("Summary", summary),
    ]
    return " | ".join(f"{k}: {v}" for k, v in parts if v)


def profile_text(p: Profile) -> str:
    return template(
        list(p.tone), p.pacing, p.viewing_effort, p.ending_feel, p.humor_style,
        p.themes, p.summary,
    )  # fmt: skip


def intent_text(q: QueryIntent) -> str:
    return template(
        list(q.tone), q.pacing, q.viewing_effort, q.ending_feel, q.humor_style,
        q.themes, q.semantic_description,
    )  # fmt: skip
