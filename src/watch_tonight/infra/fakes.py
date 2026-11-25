"""Deterministic stand-ins for the embedder and the LLM: no model, no network, no cost.

They let the walking skeleton run end to end before the real adapters exist (parts 3 and 4,
feat-028 and feat-029), and keep fast tests fast afterwards.
"""

import hashlib
import math
import random
from collections.abc import Sequence
from typing import Final

from watch_tonight.domain.intent import QueryIntent
from watch_tonight.domain.movie import Candidate
from watch_tonight.domain.output_checks import Pick
from watch_tonight.domain.ports import Pitches, Understanding, Usage
from watch_tonight.domain.search import MAX_PITCH_LENGTH, RESULTS_PER_PAGE

EMBEDDING_DIMENSIONS: Final[int] = 384  # BAAI/bge-small-en-v1.5 (ADR 0007)


class HashEmbedder:
    """A unit vector derived from a SHA-256 hash of the text: same text, same vector."""

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions

    async def embed_query(self, text: str) -> list[float]:
        return self.embed(text)

    def embed(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        rng = random.Random(seed)
        vector = [rng.gauss(0.0, 1.0) for _ in range(self._dimensions)]
        norm = math.sqrt(sum(x * x for x in vector))
        return [x / norm for x in vector]


class EchoLanguageModel:
    """Understands nothing and picks the best-ranked candidates.

    Step 2 returns an intent with no limits whose description is the text itself;
    step 5 picks the first candidates and uses each profile summary as the pitch.
    """

    async def understand(self, text: str) -> Understanding:
        intent = QueryIntent(
            max_runtime_minutes=None,
            max_intensity=None,
            avoid=[],
            year_min=None,
            year_max=None,
            audience=None,
            original_languages=[],
            tone=[],
            pacing=None,
            viewing_effort=None,
            ending_feel=None,
            humor_style=None,
            themes=[],
            semantic_description=text,
            specificity="broad",
            era_mode="modern_default",
            acclaim_preference="any",
            unmapped_constraints=[],
        )
        return Understanding(intent=intent, usage=Usage())

    async def pick_and_pitch(self, intent: QueryIntent, candidates: Sequence[Candidate]) -> Pitches:
        picks = [
            Pick(movie_id=c.movie.id, pitch=c.movie.profile.summary[:MAX_PITCH_LENGTH])
            for c in candidates[:RESULTS_PER_PAGE]
        ]
        return Pitches(picks=picks, usage=Usage())
