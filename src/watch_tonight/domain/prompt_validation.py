"""Domain validation for the user's free-text mood prompt (Product Rule P4)."""

from typing import Final

MAX_PROMPT_LENGTH: Final[int] = 500


class PromptValidationError(ValueError):
    """Raised when a mood prompt violates Product Rule P4 (empty or > 500 chars)."""


def validate_mood_prompt(raw_prompt: str) -> str:
    """Validate and normalize a free-text mood prompt.

    Strips leading/trailing whitespace, rejects empty strings, and rejects strings
    exceeding MAX_PROMPT_LENGTH without silently truncating.
    """
    cleaned = raw_prompt.strip()
    if not cleaned:
        raise PromptValidationError("Mood prompt must not be empty.")
    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise PromptValidationError(
            f"Mood prompt must be at most {MAX_PROMPT_LENGTH} characters (got {len(cleaned)})."
        )
    return cleaned
