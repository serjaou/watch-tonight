---
id: feat-008
type: spike
status: questions ready   # questions ready -> answered
timebox: 2 sessions
---
# Spike: TMDB terms, rate limits and watch-provider coverage (ES, US, BO)

## Why
The corpus, the data model and the attribution text (P5) all depend on what TMDB allows and what its watch-provider data covers. Architecture open questions Q1 and Q2.

## Questions
Each answer: the finding, plus evidence (link to the terms, command and output, or numbers from the script).

1. **Terms of use.** For a public, non-commercial portfolio app, may we:
   - store TMDB metadata in our own database, and for how long (caching or refresh rules)?
   - store short review excerpts and send them to an LLM to build profiles?
   - *Changes:* `movies` fields (`review_snippets`), enrichment inputs.
2. **Attribution.** What exactly must the UI, API and MCP responses show for TMDB (wording, logo rules) and for JustWatch data served through TMDB's watch providers?
   - *Changes:* P5 wording, the attribution field.
3. **Rate limits.** What are TMDB's current limits, and how long would ingesting 20k movies take (details, keywords, reviews and providers per movie)?
   - *Changes:* corpus size, batching and retries in the ingest job.
4. **Flat-rate vs rent/buy.** Does `/movie/{id}/watch/providers` separate flat-rate from rent and buy, per country? Can `discover` (`with_watch_providers` + `watch_region` + monetization type) list all flat-rate movies per provider and country in bulk?
   - *Changes:* P1 filter, the refresh job's strategy (per movie vs per provider).
5. **Coverage.** For ES, US and BO: which flat-rate providers exist, and how many movies each? Is BO usable at launch?
   - *Changes:* countries at launch (product.md).
6. **English data.** For a sample of popular movies, how many have an English overview, keywords and at least one review, and how many lack a `poster_path` (architecture Q13)?
   - *Changes:* enrichment quality, minimum data to include a movie.
7. **Rate of change.** How many flat-rate titles per country change from one day to the next (added or removed), and how many of the added ones are new to our corpus?
   - *Changes:* refresh schedule, and how often ingest must re-run to add new titles (architecture Q12).
8. **Images.** May the UI show TMDB posters and provider logos by linking to TMDB's image servers (storing only `poster_path` / `logo_path`)? Which sizes exist, and what attribution or usage limits apply?
   - *Changes:* the poster in each result (product.md §2), data model, UI.

## How
- Throwaway script in `spikes/08-tmdb/` (never `src/`):
  - fetch ~500 popular movies with providers for ES, US and BO (questions 4 and 6);
  - read per-provider totals from `discover` (question 5);
  - take two provider snapshots at least a day apart (question 7).
- Needs a TMDB API key in `.env` (`TMDB_API_KEY`; the owner creates the account).
