"""Acceptance tests for feat-000 (Harness dry run: Product Rule P4 mood prompt validation)."""

import pytest

from watch_tonight.domain.prompt_validation import (
    MAX_PROMPT_LENGTH,
    PromptValidationError,
    validate_mood_prompt,
)


def test_valid_prompt_is_trimmed() -> None:
    result = validate_mood_prompt("  I feel tired, want something light  ")
    assert result == "I feel tired, want something light"


def test_empty_prompt_rejected() -> None:
    with pytest.raises(PromptValidationError, match="must not be empty"):
        validate_mood_prompt("   \n\t  ")


def test_overlong_prompt_rejected() -> None:
    overlong = "a" * (MAX_PROMPT_LENGTH + 1)
    with pytest.raises(PromptValidationError, match="at most 500 characters"):
        validate_mood_prompt(overlong)
