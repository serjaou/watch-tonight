"""Unit tests for boundary conditions in `watch_tonight.domain.prompt_validation`."""

import pytest

from watch_tonight.domain.prompt_validation import (
    MAX_PROMPT_LENGTH,
    PromptValidationError,
    validate_mood_prompt,
)


@pytest.mark.parametrize("length", [1, 250, MAX_PROMPT_LENGTH])
def test_prompt_within_limit_passes(length: int) -> None:
    prompt = "x" * length
    assert validate_mood_prompt(prompt) == prompt


def test_padded_prompt_at_exact_limit_passes_after_strip() -> None:
    prompt = "  " + ("x" * MAX_PROMPT_LENGTH) + "  "
    assert len(validate_mood_prompt(prompt)) == MAX_PROMPT_LENGTH


def test_subclass_of_value_error() -> None:
    assert issubclass(PromptValidationError, ValueError)
