"""Unit tests for the step-6 checks (domain/output_checks.py)."""

from watch_tonight.domain.output_checks import Pick, check_picks


def picks(*ids: int, pitch: str = "A warm, gentle film.") -> list[Pick]:
    return [Pick(movie_id=i, pitch=pitch) for i in ids]


def test_valid_picks_have_no_errors() -> None:
    assert check_picks(picks(1, 2, 3, 4, 5), [1, 2, 3, 4, 5, 6]) == []
    assert check_picks(picks(2), [2]) == []  # fewer candidates: pick them all
    assert check_picks([], []) == []


def test_each_problem_is_reported_for_the_model_to_fix() -> None:
    errors = check_picks(
        [*picks(1, 2, 9), Pick(movie_id=1, pitch=" "), Pick(movie_id=3, pitch="x" * 351)],
        [1, 2, 3, 4, 5],
    )
    assert errors == [
        "Movie 9 is not one of the candidates.",
        "Movie 1 is picked more than once.",
        "The pitch for movie 1 is empty.",
        "The pitch for movie 3 has 351 characters; the limit is 350.",
    ]


def test_wrong_count_is_reported() -> None:
    assert check_picks(picks(1, 2), [1, 2, 3]) == ["Pick exactly 3 movies; you picked 2."]


def test_a_pitch_of_exactly_350_characters_is_valid() -> None:
    assert check_picks(picks(1, pitch="x" * 350), [1]) == []
