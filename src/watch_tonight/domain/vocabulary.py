"""The closed v1 vocabulary shared by movie profiles and query intents (ADR 0005).

Values come from spike 16 §5 Q3 (`spikes/16-recommendation/schemas_v1.py`). The profile
design feature (feat-019) anchors their definitions. `Literal` types are like C# enums
that serialize as strings, and pyright checks every use.
"""

from typing import Final, Literal, get_args

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
Audience = Literal["kids", "teens"]
Specificity = Literal["broad", "medium", "specific"]
EraMode = Literal["modern_default", "classic_or_any_era"]
AcclaimPreference = Literal["crowd_pleaser", "critically_acclaimed", "hidden_gem", "any"]

CONTENT_WARNINGS: Final[tuple[ContentWarning, ...]] = get_args(ContentWarning)
