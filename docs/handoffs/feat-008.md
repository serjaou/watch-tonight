# Handoff: `feat-008` — Spike: TMDB terms, rate limits and watch providers

- **Type:** `spike`
- **Date:** 2026-11-15
- **Machine · Tool:** Mac · Antigravity
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `1 (0)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- Built `spikes/08-tmdb/probe_tmdb.py` and executed it across two sessions separated by 24.5 hours (`snapshot_1.json` at `2026-11-14T14:48:37Z` and `snapshot_2.json` at `2026-11-15T15:18:19Z`), answering all 8 questions in `docs/spikes/08-tmdb-and-providers.md` (`status: answered`) and recording baselines in `docs/metrics.md` §1.4:
  - **Q1 (Terms of use):** Non-commercial portfolio use is allowed; caching/storing metadata in MongoDB Atlas is allowed (`Cache-Control: public, max-age=28125`); drop persisted `review_snippets` from `movies` and require LLM training opt-out in `feat-011`.
  - **Q2 (Attribution):** Documented exact TMDB disclaimer + logo rules and JustWatch credit for `P5`.
  - **Q3 (Rate limits & throughput):** `append_to_response=keywords,reviews,watch/providers,credits` fetches full movie metadata + all countries' providers in **1 HTTP call**. Measured **`25.2 req/s`** (`500` bundles in `19.84 s` with `10` workers, `p50 = 176.6 ms`, `p95 = 1,073.1 ms`, `0` HTTP `429`s) → **`~14 minutes`** to ingest `20,000` movies.
  - **Q4 (`flatrate` vs `rent`/`buy` & `/discover/movie` bug):** Proved `/discover/movie` evaluates `with_watch_providers` and `with_watch_monetization_types=flatrate` as separate movie-level predicates (returning 20,001 "flatrate" matches for pure rent/buy store `Apple TV Store = 2` when another provider has `flatrate`), and caps pagination at `500` pages (`10,000` results). Therefore, `streamable` must always be built from per-movie `/movie/{id}/watch/providers` (`results[country]["flatrate"]`).
  - **Q5 (Coverage in ES, US, BO):** Flat-rate coverage in Popular 500 is **US `73.2%`** (`366/500`), **ES `67.0%`** (`335/500`), and **BO `62.4%`** (`312/500`) — **BO is usable at launch**. Documented country-specific provider IDs (e.g. Prime Video `9` in US vs `119` in ES/BO).
  - **Q6 & Architecture Q13 (Data completeness & missing posters):** `100.0%` English `overview`, `94.6%` `>= 1` keyword, `82.8%` `>= 1` review, and **`0.0%` missing `poster_path`** across `500` popular + `480` deep-sampled flat-rate movies (pages `1..500`). Recorded owner decision on **Q13** in `docs/architecture.md` §7: exclude any movie lacking `poster_path` at ingest time.
  - **Q7 & Architecture Q12 (24.5h provider churn):** Across the 500 popular movies, **`11/500` (`2.2%`) in ES**, **`13/500` (`2.6%`) in US**, and **`3/500` (`0.6%`) in BO** changed flat-rate providers in 24.5 hours (`~100–500` movies/day at 20k scale), confirming daily availability refresh is essential. Over 90% of daily provider additions are existing catalog titles rotating between services, while only `1–3` brand-new releases/day per country enter flat-rate streaming.
  - **Q8 (Images):** Confirmed `https://image.tmdb.org/t/p/` hotlinking and sizes (`w342`/`w500` for posters, `w45`/`w92` for provider logos).

## Verification Evidence
```text
Mac, 2026-11-14 (Session 1) & 2026-11-15 (Session 2):
$ uv run python spikes/08-tmdb/probe_tmdb.py --snapshot-out spikes/08-tmdb/snapshot_2.json
Saved snapshot to /Users/sergio/Sergio/Workspaces/watch-tonight/spikes/08-tmdb/snapshot_2.json

$ uv run python spikes/08-tmdb/probe_tmdb.py --compare spikes/08-tmdb/snapshot_1.json spikes/08-tmdb/snapshot_2.json
{
  "snapshot_1_captured_at": "2026-11-14T14:48:37.662198+00:00",
  "snapshot_2_captured_at": "2026-11-15T15:18:19.485578+00:00",
  "common_popular_movies_compared": 500,
  "popular_500_id_turnover": 42,
  "per_country_popular_500_churn": {
    "ES": { "added_movie_provider_pairs": 9, "removed_movie_provider_pairs": 6, "movies_changed": 11 },
    "US": { "added_movie_provider_pairs": 14, "removed_movie_provider_pairs": 10, "movies_changed": 13 },
    "BO": { "added_movie_provider_pairs": 3, "removed_movie_provider_pairs": 0, "movies_changed": 3 }
  }
}

$ uv run poe check
Poe => ruff check src tests scripts
All checks passed!
Poe => ruff format --check src tests scripts
14 files already formatted
Poe => pyright
0 errors, 0 warnings, 0 informations
Poe => lint-imports
Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration'
..........................                                               [100%]
26 passed in 0.79s

Reviewer subagent (dc918267-b09a-43de-a088-a530425a7c4b):
Round 1: "No findings"
```
