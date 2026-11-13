---
id: feat-011
type: spike
status: questions ready   # questions ready -> answered
timebox: 2 sessions
---
# Spike: runtime LLM (provider, cost, structured output, framework)

## Why
The product calls an LLM twice per query (understand, re-rank + pitch) and once per movie offline (emotional profile). The provider and model decide quality, cost per query, the cost of enriching 5–20k movies, and latency. Budget: zero cost by default, a small spend when it clearly improves quality (product.md §1). The framework choice shapes the `LanguageModel` adapter. Architecture open question Q6. This was on the inception brief's Week 1 checklist but had no backlog item.

## Questions
Each answer: the finding, plus evidence (docs link and date, command and output, measurements).

1. **Limits and cost.** Compare at least two candidates: Gemini on its free tier, and a low-cost OpenAI model (e.g. a "mini" tier).
   - For each: rate limits (requests and tokens per minute and per day) and price per million input and output tokens.
   - Cost per query (2 calls) and per 1,000 profiles. Can enrichment of 20k movies stay within a small budget, and how many days does it take?
   - *Changes:* provider and model, corpus size, enrichment batching, eval budget.
2. **Data use.** What do each candidate's terms say about using prompts and outputs (the user's mood text is sent to the model)?
   - *Changes:* privacy note in the UI or README, possibly the provider.
3. **Structured output.** Does the model reliably return JSON matching a Pydantic schema for:
   - the query intent, including filters from a closed vocabulary and an English summary for non-English input (architecture Q9, Q11);
   - the re-rank with pitches (≤ 350 chars, about the movie only)?

   Try 10 queries, at least 3 of them not in English.
   - *Changes:* the retries in query steps 2 and 6 (architecture.md), prompt design.
4. **Latency.** p50/p95 for each of the two online calls.
   - *Changes:* p95 latency target (open question Q7), whether to merge the two calls.
5. **Framework.** For two structured calls, what does Pydantic AI add over the providers' plain SDKs (retries, validation, testing with fakes, switching provider)?
   - *Changes:* the `infra` adapter and a new dependency (needs an ADR).
6. **Fallback.** If the chosen provider's quota or budget runs out, which provider could replace it behind the same port?
   - *Changes:* the *Service unavailable* state, configuration.

## How
- Throwaway scripts in `spikes/11-llm/` with 10 sample queries.
- Build each re-rank prompt with 30–50 candidates (TMDB overviews or synthetic profiles), as in the real query flow, and record input and output tokens per call: candidates make up most of the prompt (questions 1 and 4).
- For enrichment, profile ~20 sample movies and record tokens per movie.
- Needs API keys in `.env` for the providers compared (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`; owner). Add any new key name to `.env.example`.
