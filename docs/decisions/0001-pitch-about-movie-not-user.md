# 0001. Recommendations use movie-only pitches, never user/mood justifications

- **Date:** 2026-11-11
- **Status:** Accepted
- **Context:** The initial brief described accompanying each recommended movie with a "reason" explaining why the movie matched the user's mood criteria. During `docs/product.md` refinement, the owner noted that explanations talking about the user ("Because you're tired, this isn't too heavy...") feel patronizing and artificial.
- **Decision:** Every recommendation includes a 1–2 sentence **pitch** (Product Rule P2 in `docs/product.md`) that is strictly about the movie itself—highlighting the qualities of the film relevant to the request (tone, pace, setting, performances, themes) stated as facts from the movie's data, with no spoilers. It must never mention the user, their mood, their request, or claim the movie will make them feel a certain way.
- **Consequences:**
  - The re-ranking/explanation LLM prompt and the LLM-as-judge evaluation rubric must explicitly forbid second-person references ("you", "your mood") and match-justification phrasing.
  - Every factual claim in the pitch must still be grounded in the movie's catalogue/profile data.
