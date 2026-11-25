"""Step 6, *Check the LLM's output*: picks and pitches, checked by value (architecture §3).

Pure functions. Part 4 (feat-029) runs them inside the Pydantic AI output validator, which
gives one retry with these messages fed back to the model (ADR 0006); `SearchMovies` runs
them again on whatever the port returns, as a final guard. The messages are written for
the model to read.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from watch_tonight.domain.search import MAX_PITCH_LENGTH, RESULTS_PER_PAGE


class Pick(BaseModel):
    """One movie the LLM chose in step 5, with its pitch."""

    model_config = ConfigDict(frozen=True)

    movie_id: int
    pitch: str


def check_picks(picks: Sequence[Pick], candidate_ids: Sequence[int]) -> list[str]:
    """Return every problem found; an empty list means the output is valid."""
    errors: list[str] = []
    expected = min(RESULTS_PER_PAGE, len(candidate_ids))
    if len(picks) != expected:
        errors.append(f"Pick exactly {expected} movies; you picked {len(picks)}.")
    known = set(candidate_ids)
    seen: set[int] = set()
    for pick in picks:
        if pick.movie_id not in known:
            errors.append(f"Movie {pick.movie_id} is not one of the candidates.")
        if pick.movie_id in seen:
            errors.append(f"Movie {pick.movie_id} is picked more than once.")
        seen.add(pick.movie_id)
        if not pick.pitch.strip():
            errors.append(f"The pitch for movie {pick.movie_id} is empty.")
        elif len(pick.pitch) > MAX_PITCH_LENGTH:
            errors.append(
                f"The pitch for movie {pick.movie_id} has {len(pick.pitch)} characters; "
                f"the limit is {MAX_PITCH_LENGTH}."
            )
    return errors
