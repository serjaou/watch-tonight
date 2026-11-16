"""feat-011 spike: draft Pydantic schemas and deterministic checks for the three LLM calls.

THROWAWAY. The closed vocabulary below is a placeholder so the spike can test
"filters from a closed vocabulary" (architecture Q11). The real vocabulary is
designed in the profile feature (feat-016 / feat-012), not here.

Schemas sent to the providers stay simple (types, enums, required fields), and the
stricter rules (lengths, counts, IDs) live in `check_*` functions, the same split as
query steps 2 and 6 in docs/architecture.md: schema-valid first, then deterministic checks.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

Tone = Literal[
    "light",
    "funny",
    "heartwarming",
    "romantic",
    "uplifting",
    "thoughtful",
    "melancholic",
    "dark",
    "tense",
    "scary",
    "exciting",
    "weird",
]

ContentWarning = Literal[
    "violence",
    "gore",
    "sexual_content",
    "nudity",
    "strong_language",
    "drug_use",
    "self_harm",
    "animal_harm",
    "child_harm",
    "sexual_violence",
    "horror_scares",
    "flashing_lights",
]

Intensity = Literal[1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Call 1 (online): understand
# ---------------------------------------------------------------------------
class Intent(BaseModel):
    input_language: str
    summary_en: str
    tone: list[Tone]
    themes: list[str]
    max_runtime_minutes: int | None
    avoid: list[ContentWarning]
    max_intensity: Intensity | None


def check_intent(intent: Intent) -> list[str]:
    problems: list[str] = []
    if not intent.summary_en.strip():
        problems.append("empty summary_en")
    if len(intent.summary_en) > 400:
        problems.append(f"summary_en too long ({len(intent.summary_en)} chars)")
    if len(intent.tone) > 3:
        problems.append(f"too many tones ({len(intent.tone)})")
    if len(intent.themes) > 5:
        problems.append(f"too many themes ({len(intent.themes)})")
    if intent.max_runtime_minutes is not None and not 30 <= intent.max_runtime_minutes <= 300:
        problems.append(f"odd max_runtime_minutes={intent.max_runtime_minutes}")
    return problems


# ---------------------------------------------------------------------------
# Call 2 (online): re-rank + pitch
# ---------------------------------------------------------------------------
class Pick(BaseModel):
    tmdb_id: int
    pitch: str


class Rerank(BaseModel):
    picks: list[Pick]


PITCH_MAX = 350
# P2 / ADR 0001 heuristic: second person or "fit for you" phrasing.
_P2_PATTERNS = re.compile(
    r"\b(you|your|you're|youre|yourself|you'll|you've|viewer|viewers|tonight|mood|"
    r"perfect for|ideal for|great for|just what)\b",
    re.IGNORECASE,
)


def p2_flags(pitch: str) -> list[str]:
    return sorted({m.group(0).lower() for m in _P2_PATTERNS.finditer(pitch)})


def check_rerank(rerank: Rerank, candidate_ids: set[int]) -> list[str]:
    """Step-6 deterministic checks. Returns blocking problems (would trigger a retry)."""
    problems: list[str] = []
    want = min(5, len(candidate_ids))
    ids = [p.tmdb_id for p in rerank.picks]
    if len(ids) != want:
        problems.append(f"expected {want} picks, got {len(ids)}")
    if len(set(ids)) != len(ids):
        problems.append("duplicate picks")
    invented = [i for i in ids if i not in candidate_ids]
    if invented:
        problems.append(f"ids not in candidates: {invented}")
    for p in rerank.picks:
        if len(p.pitch) > PITCH_MAX:
            problems.append(f"pitch for {p.tmdb_id} is {len(p.pitch)} chars")
        if not p.pitch.strip():
            problems.append(f"empty pitch for {p.tmdb_id}")
    return problems


# ---------------------------------------------------------------------------
# Call 3 (offline): emotional profile, once per movie
# ---------------------------------------------------------------------------
class Profile(BaseModel):
    tone: list[Tone]
    pacing: Literal["slow", "medium", "fast"]
    intensity: Intensity
    themes: list[str]
    content_warnings: list[ContentWarning]
    summary_en: str


def check_profile(profile: Profile) -> list[str]:
    problems: list[str] = []
    if not 1 <= len(profile.tone) <= 3:
        problems.append(f"tone count {len(profile.tone)}")
    if not 1 <= len(profile.themes) <= 5:
        problems.append(f"themes count {len(profile.themes)}")
    if len(profile.summary_en) > 450:
        problems.append(f"summary_en {len(profile.summary_en)} chars")
    return problems
