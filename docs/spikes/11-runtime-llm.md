---
id: feat-011
type: spike
status: questions ready   # questions ready -> answered
timebox: 2 sessions
---
# Spike: runtime LLM (Gemini free tier, structured output, framework)

## Why
The product calls an LLM twice per query (understand, re-rank + pitch) and once per movie offline (emotional profile). Free-tier limits decide whether enrichment of 5–20k movies is feasible and how fast queries can be; the framework choice shapes the `LanguageModel` adapter. Architecture open question Q6. This was on the inception brief's Week 1 checklist but had no backlog item.

## Questions
Each answer: the finding, plus evidence (docs link and date, command and output, measurements).

1. **Limits.** For the candidate Gemini model(s) on the free tier: requests per minute and per day, tokens per minute.
   - Can enrichment of 20k movies finish in a reasonable number of days?
   - Do 2 calls per query leave room for a demo and the evals?
   - *Changes:* corpus size, enrichment batching, eval budget.
2. **Data use.** What do the free-tier terms say about using prompts and outputs (the user's mood text is sent to the model)?
   - *Changes:* privacy note in the UI or README, possibly the provider.
3. **Structured output.** Does the model reliably return JSON matching a Pydantic schema for:
   - the query intent;
   - the re-rank with pitches (≤ 350 chars, about the movie only)?

   Try 10 queries.
   - *Changes:* the retry in query step 6 (architecture.md), prompt design.
4. **Latency.** p50/p95 for each of the two online calls.
   - *Changes:* p95 latency target (open question Q7), whether to merge the two calls.
5. **Framework.** For two structured calls, what does Pydantic AI add over the plain Google SDK (retries, validation, testing with fakes, provider swap)?
   - *Changes:* the `infra` adapter and a new dependency (needs an ADR).
6. **Fallback.** If the free quota runs out, which provider could replace it behind the same port (e.g. Groq, OpenRouter free models)?
   - *Changes:* the *Service unavailable* state, configuration.

## How
- Throwaway scripts in `spikes/11-llm/` with 10 sample queries.
- Build each re-rank prompt with 30–50 candidates (TMDB overviews or synthetic profiles), as in the real query flow, and record input and output tokens per call: candidates make up most of the prompt (questions 1 and 4).
- For enrichment, profile ~20 sample movies and record tokens per movie.
- Needs a Gemini API key in `.env` (`GEMINI_API_KEY`; owner).
