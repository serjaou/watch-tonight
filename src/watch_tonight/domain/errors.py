"""Domain exceptions that map to response states (architecture §6)."""


class ServiceUnavailableError(Exception):
    """The *Service unavailable* state: step 2 or the search failed (Q8).

    `stage` names the step that failed, for logs; it is never shown to the user.
    """

    def __init__(self, stage: str) -> None:
        super().__init__(f"Search failed at stage: {stage}")
        self.stage = stage
