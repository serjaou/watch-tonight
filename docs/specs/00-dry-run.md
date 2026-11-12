---
id: feat-000
stories: [US1]
status: approved
---
# Harness Dry Run: Mood Prompt Validator (Rule P4)

## Goal
Validate and normalize the user's free-text mood prompt in the domain layer according to Product Rule P4 (non-empty after trimming, and at most 500 characters; never silently truncated).

## Acceptance tests (written or approved by the owner)
- [x] Given a valid mood prompt with surrounding whitespace, when validated, then it returns the trimmed prompt -> `tests/acceptance/test_dry_run.py::test_valid_prompt_is_trimmed`
- [x] Given an empty or whitespace-only prompt, when validated, then it raises `PromptValidationError` -> `tests/acceptance/test_dry_run.py::test_empty_prompt_rejected`
- [x] Given a prompt longer than 500 characters, when validated, then it raises `PromptValidationError` without truncating -> `tests/acceptance/test_dry_run.py::test_overlong_prompt_rejected`

## Out of scope
- FastAPI HTTP error mapping (belongs to the API slice).
- LLM query understanding.

## Design notes (with C# comparison)
- Implemented in `src/watch_tonight/domain/prompt_validation.py` with zero external dependencies (Clean Architecture `domain` layer).
- Uses a custom domain exception `PromptValidationError(ValueError)` and a constant `MAX_PROMPT_LENGTH: Final[int] = 500` (`Final` in Python `typing` is the static-analysis equivalent of `const` / `readonly` in C#).

## Open questions (must be empty before status: approved)
- None
