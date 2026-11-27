---
id: feat-008
type: spike
status: answered
timebox: 2 sessions
---
# Spike: TMDB terms, rate limits and watch-provider coverage (ES, US, BO)

## Why
The corpus, the data model and the attribution text (P5) all depend on what TMDB allows and what its watch-provider data covers. Architecture open questions Q1, Q2, Q12 and Q13.

## Questions & Findings

Each answer records the finding, the evidence (official documentation links, command and output from `spikes/08-tmdb/probe_tmdb.py` / `spikes/08-tmdb/report.json`), and what it changes in the architecture.

---

### 1. Terms of use
> For a public, non-commercial portfolio app, may we:
> - store TMDB metadata in our own database, and for how long (caching or refresh rules)?
> - store short review excerpts and send them to an LLM to build profiles?
> - *Changes:* `movies` fields (`review_snippets`), enrichment inputs.

- **Finding:**
  1. **Licence:** TMDB grants a free, non-exclusive licence to use the API in non-commercial applications (no revenue, fees, or advertising). `watch-tonight` is a zero-cost, non-commercial project (`docs/product.md` §1).
  2. **How long we may store metadata:** at most 6 months. Section 1.C of the terms forbids caching *"for longer than 6 months, any information obtained through or from TMDB or the TMDB APIs"*. So availability is refreshed daily, and all other stored metadata is re-fetched at least every 6 months. TMDB's `/3/movie/changes` endpoint can narrow the re-fetch to films that changed. (The `Cache-Control: public, max-age=28125` header on API responses only tells HTTP clients how long to keep one response; it isn't a storage rule.)
  3. **No redistribution:** TMDB data stays in the app's own database. Raw API responses are never committed to the repo or served in bulk; spike outputs that contain them are gitignored (`docs/conventions.md`).
  4. **Reviews:** we **do not persist or serve raw user reviews (`review_snippets`)**. Each review belongs to its author, and 17.2% of popular movies have none anyway (Q6).
  5. **LLM calls:** no model is trained on TMDB data, and the LLM provider's API tier must not train on our inputs (checked in `feat-011` Q2).
- **Evidence:**
  - [TMDB API Terms of Use](https://www.themoviedb.org/api-terms-of-use) (last updated 2023-10-20), sections 1.C and 3, and the [TMDB Developer FAQ](https://developer.themoviedb.org/docs/faq).
  - Observed response header: `"cache-control": "public, max-age=28125"` (≈ 7.8 h).
- **Changes:**
  - **Drop `review_snippets` from the `movies` collection** in `docs/architecture.md` §5. Build emotional profiles from `overview`, `keywords`, `genres`, `credits`, `runtime`, and `year` (all 94.6%–100% present in Q6).
  - **Re-fetch stored metadata at least every 6 months** (`docs/architecture.md` §4, the ingest task's re-fetch policy).

---

### 2. Attribution
> What exactly must the UI, API and MCP responses show for TMDB (wording, logo rules) and for JustWatch data served through TMDB's watch providers?
> - *Changes:* P5 wording, the attribution field.

- **Finding:**
  1. **TMDB attribution ([API Terms of Use](https://www.themoviedb.org/api-terms-of-use), [Logos & Attribution](https://www.themoviedb.org/about/logos-attribution)):**
     - **Mandatory disclaimer text:** *"This product uses the TMDB API but is not endorsed or certified by TMDB."*
     - **Logo rules:** The web UI must display the official TMDB logo (from `https://www.themoviedb.org/about/logos-attribution`), less prominent than `watch-tonight`'s own branding, linked to `https://www.themoviedb.org/`, and never implying endorsement.
     - **Per-movie link:** Every recommendation card links to `https://www.themoviedb.org/movie/{id}` (`docs/product.md` §2).
  2. **JustWatch attribution ([Movie Watch Providers API reference](https://developer.themoviedb.org/reference/movie-watch-providers)):**
     - TMDB's watch-provider documentation mandates: *"In order to use this data you must attribute the source of the data as JustWatch. If we find any usage not complying with these terms we will revoke access to the API."*
     - Each `/movie/{id}/watch/providers` country entry also provides a `link` (e.g. `https://www.themoviedb.org/movie/{id}/watch?locale={country}`).
- **Evidence:**
  - [TMDB Logos & Attribution](https://www.themoviedb.org/about/logos-attribution) and [Movie Watch Providers endpoint docs](https://developer.themoviedb.org/reference/movie-watch-providers).
  - Sample `link` in `spikes/08-tmdb/report.json` (`sample_provider_structure`): `"https://www.themoviedb.org/movie/687163-project-hail-mary/watch?locale=US"`.
- **Changes:**
  - **API & MCP `attribution` response field (P5):**
    `"This product uses the TMDB API but is not endorsed or certified by TMDB. Streaming availability data is provided by JustWatch."`
  - **Web UI footer (P5):** Official TMDB logo (linked to `https://www.themoviedb.org/`) + the exact disclaimer text above + visible JustWatch credit.

---

### 3. Rate limits
> What are TMDB's current limits, and how long would ingesting 20k movies take (details, keywords, reviews and providers per movie)?
> - *Changes:* corpus size, batching and retries in the ingest job.

- **Finding:**
  1. **Published limit ([TMDB Rate Limiting](https://developer.themoviedb.org/docs/rate-limiting)):** TMDB retired its old `40 requests / 10 seconds` cap; the soft ceiling is **~40–50 requests/second** per IP, returning HTTP `429 Too Many Requests` (with `Retry-After`) if exceeded.
  2. **`append_to_response` cuts per-movie requests by 4×–5×:** A single request to `GET /3/movie/{id}?language=en-US&append_to_response=keywords,reviews,watch/providers,credits` returns movie details, keywords, reviews, watch providers (for **all** countries at once), and cast/director credits in **1 HTTP call**.
  3. **Measured throughput & latency (`spikes/08-tmdb/report.json`):**
     - Full probe (`1,035` requests): `59.15 s` (`17.5 req/s` overall across sequential + parallel phases), **`0` HTTP `429` responses**, **`p50 = 176.6 ms`**, **`p95 = 1,073.1 ms`**.
     - 500-movie bundle batch (`10` concurrent workers fetching `/movie/{id}?append_to_response=keywords,reviews,watch/providers,credits`): **`500` movies in `19.84 s` = `25.2 req/s` sustained** with **`0` retries / `0` `429`s**.
  4. **Time to ingest 20,000 movies:**
     - `20,000` `/movie/{id}?append_to_response=...` calls + `~1,000` `/discover/movie` pages = `~21,000` calls.
     - At our measured **25.2 req/s** (`10` workers): **`~833 s` (`~13.9 minutes`)**.
     - At a conservative throttled **20 req/s**: **`~1,050 s` (`~17.5 minutes`)**.
     - TMDB rate limits are **not** the bottleneck for a 5k–20k corpus (Atlas storage in `feat-009` and LLM enrichment cost in `feat-011` will bound corpus size).
- **Evidence:**
  ```text
  $ uv run python spikes/08-tmdb/probe_tmdb.py
  "request_telemetry": {
    "total_requests": 1035,
    "total_elapsed_s": 59.15,
    "overall_rps": 17.5,
    "latency_p50_ms": 176.6,
    "latency_p95_ms": 1073.1,
    "status_counts": { "200": 1034, "400": 1 },
    "retries_429_or_network": 0
  },
  "popular_500_probe": {
    "sample_size": 500,
    "batch_500_elapsed_s": 19.84,
    "batch_500_achieved_rps": 25.2
  }
  ```
- **Changes:**
  - In `MovieSource` (`infra`), fetch movie metadata + keywords + credits + watch providers in **one** call via `append_to_response=keywords,watch/providers,credits`.
  - Use bounded concurrency (`8–10` concurrent requests, `~20–25 req/s`) and honour `Retry-After` / exponential backoff on HTTP `429` and `5xx`.

---

### 4. Flat-rate vs rent/buy
> Does `/movie/{id}/watch/providers` separate flat-rate from rent and buy, per country? Can `discover` (`with_watch_providers` + `watch_region` + monetization type) list all flat-rate movies per provider and country in bulk?
> - *Changes:* P1 filter, the refresh job's strategy (per movie vs per provider).

- **Finding:**
  1. **`/movie/{id}/watch/providers` cleanly separates monetization types per country:**
     - Under `results[country]`, TMDB returns separate lists for `"flatrate"` (subscription streaming), `"rent"`, `"buy"`, `"free"`, and `"ads"`.
     - Reading only `results[country].get("flatrate", [])` guarantees **Product Rule P1** (subscription flat-rate only, never rent/buy/free-with-ads).
  2. **CRITICAL FINDING — `/discover/movie` CANNOT be used to build per-provider `streamable` tags:**
     - **Bug / limitation 1 (Cross-provider monetization bleed):** In `/discover/movie`, `with_watch_providers=<id>` and `with_watch_monetization_types=flatrate` are evaluated as **separate movie-level predicates** in that country, NOT joined on the same provider!
       - Proof (`uv run python spikes/08-tmdb/probe_tmdb.py --verify-discover`): querying `/discover/movie?watch_region=US&with_watch_providers=2&with_watch_monetization_types=flatrate` for `provider_id=2` (*Apple TV Store*, a pure rent/buy store) reports `20,001` movies. Inspecting the top 5 returned movies (`687163`, `354912`, `155`, `1595325`, `940721`) via `/movie/{id}/watch/providers` shows **`provider_2_in_flatrate: false`** and **`provider_2_in_rent: true, provider_2_in_buy: true`** on **5 out of 5** (they matched only because *other* providers like Netflix `8` or Disney+ `337` had `flatrate` on those movies!).
       - Using `/discover/movie` per provider to populate `streamable` would tag rent/buy movies as flat-rate and break **Product Rule P1**.
     - **Limitation 2 (Hard 500-page / 10,000-movie pagination cap):** `/discover/movie` rejects `page=501` with HTTP `400` (`status_code: 22`, `"Invalid page: Pages start at 1 and max at 500"`).
     - **Limitation 3 (Request volume):** Summing per-provider discover pages across ES (`5,619`), US (`23,450`), and BO (`1,802`) is `30,871` pages — more requests than refreshing per movie.
- **Evidence:**
  ```text
  $ uv run python spikes/08-tmdb/probe_tmdb.py --verify-discover
  "apple_tv_store_id_2_with_flatrate_filter": [
    {
      "movie_id": 687163,
      "provider_2_in_flatrate": false,
      "provider_2_in_rent": true,
      "provider_2_in_buy": true,
      "actual_flatrate_provider_ids": [9, 257, 583, 2383, 636, 34, 2100]
    }, ... (5/5 have provider_2_in_flatrate: false)
  ]
  ```
  And in `spikes/08-tmdb/report.json` (`discover_pagination_check`):
  ```json
  "page_500_results_len": 20,
  "page_501_response": {
    "_http_error": 400,
    "_error_body": "{\"success\":false,\"status_code\":22,\"status_message\":\"Invalid page: Pages start at 1 and max at 500. They are expected to be an integer.\"}"
  }
  ```
- **Changes:**
  - **Ingest candidate discovery:** Use `/discover/movie?watch_region=ES|US|BO&with_watch_monetization_types=flatrate&sort_by=popularity.desc` (pages `1..N`, without `with_watch_providers`) solely to collect candidate movie IDs that have flat-rate streaming in at least one target country.
  - **Refresh strategy = Per Movie (`/movie/{id}/watch/providers`):** Both initial ingest (via `append_to_response=watch/providers`) and the daily refresh job must read `results[country]["flatrate"]` from `/movie/{id}/watch/providers`. One request per movie returns **all countries at once**, so refreshing 10k–20k stored movies takes `10k–20k` requests (`~7–14 minutes` at 25 req/s) and is 100% P1-accurate.

---

### 5. Coverage (ES, US, BO)
> For ES, US and BO: which flat-rate providers exist, and how many movies each? Is BO usable at launch?
> - *Changes:* countries at launch (product.md).

- **Finding:**
  1. **Flat-rate coverage across the 500 popular movies sample** (ground-truth `results[country]["flatrate"]` from `/movie/{id}/watch/providers` in `spikes/08-tmdb/report.json` & `snapshot_1.json`):
     - **US:** **`366 / 500` (`73.2%`)** streamable flat-rate (`60` distinct flat-rate provider IDs in Popular 500; `295` catalog providers listed in `/watch/providers/movie`).
     - **ES:** **`335 / 500` (`67.0%`)** streamable flat-rate (`34` distinct flat-rate provider IDs in Popular 500; `97` catalog providers listed).
     - **BO:** **`312 / 500` (`62.4%`)** streamable flat-rate (`10` distinct flat-rate provider IDs in Popular 500; `40` catalog providers listed).
     - **Union (`ES ∪ US ∪ BO`):** **`393 / 500` (`78.6%`)** of popular movies have `>= 1` flat-rate provider in at least one of the three countries.
  2. **Top true flat-rate providers per country** (ranked by hits in Popular 500, with `/discover/movie` catalog size):

     | Country | Provider (`provider_id`) | Popular 500 (`flatrate`) | Discover `total_results` |
     |---|---|---:|---:|
     | **ES** | Amazon Prime Video (`119`) *(+ `2100` with Ads)* | `116 / 500` (`23.2%`) | `8,715` |
     | **ES** | Movistar Plus+ Ficción Total (`149`) *(+ `2241` Movistar Plus+)* | `116 / 500` (`23.2%`) | `6,215` *(+ `2,059`)* |
     | **ES** | Disney Plus (`337`) | `108 / 500` (`21.6%`) | `2,510` |
     | **ES** | Netflix (`8`) *(+ `1796` Standard with Ads)* | `76 / 500` (`15.2%`) | `6,744` |
     | **ES** | HBO Max (`1899`) *(+ `1825` Amazon Channel)* | `56 / 500` (`11.2%`) | `889` |
     | **ES** | SkyShowtime (`1773`) *(+ `2801` Amazon Channel)* | `28 / 500` (`5.6%`) | `571` |
     | **ES** | Tivify (`1838`) | `25 / 500` (`5.0%`) | `1,858` |
     | **ES** | Filmin (`63`) | `15 / 500` (`3.0%`) | `11,820` |
     | **ES** | Apple TV+ (`350`) *(+ `2243` Amazon Channel)* | `9 / 500` (`1.8%`) | `121` |
     | **ES** | Atres Player (`62`), FlixOlé (`393`), MUBI (`11`), Acontra+ (`1717`) | `1–3 / 500` each | `389` / `3,410` / `395` / `1,768` |
     | **US** | Disney Plus (`337`) | `83 / 500` (`16.6%`) | `1,731` |
     | **US** | HBO Max (`1899`) *(+ `1825` Amazon Channel)* | `60 / 500` (`12.0%`) | `2,060` |
     | **US** | YouTube TV (`2528`) | `61 / 500` (`12.2%`) | `1,395` |
     | **US** | Netflix (`8`) *(+ `1796` Standard with Ads)* | `55 / 500` (`11.0%`) | `4,805` |
     | **US** | Amazon Prime Video (`9`) *(+ `2100` with Ads)* | `54 / 500` (`10.8%`) | `20,001*` |
     | **US** | fuboTV (`257`) | `43 / 500` (`8.6%`) | `12,205` |
     | **US** | Paramount+ (`2616` Essential / `2303` Premium / `582` Channel) | `41 / 500` (`8.2%`) | `1,198` |
     | **US** | Peacock Premium (`386`) *(+ `387` Plus)* | `31 / 500` (`6.2%`) | `1,216` |
     | **US** | Philo (`2383`) | `31 / 500` (`6.2%`) | `8,547` |
     | **US** | Hulu (`15`) | `22 / 500` (`4.4%`) | `1,348` |
     | **US** | Starz (`1855`), AMC+ (`526`), MGM+ (`34`), Criterion (`258`), Shudder (`99`), Apple TV+ (`350`), MUBI (`11`) | `11–14 / 500` | `134–2,398` |
     | **BO** | Disney Plus (`337`) | `105 / 500` (`21.0%`) | `2,265` |
     | **BO** | HBO Max (`1899`) | `100 / 500` (`20.0%`) | `2,087` |
     | **BO** | Amazon Prime Video (`119`) | `86 / 500` (`17.2%`) | `6,872` |
     | **BO** | Netflix (`8`) | `70 / 500` (`14.0%`) | `4,894` |
     | **BO** | Paramount Plus (`531`) | `18 / 500` (`3.6%`) | `326` |
     | **BO** | Apple TV+ (`350`) | `9 / 500` (`1.8%`) | `120` |
     | **BO** | VIX (`457`), MUBI (`11`) | `3 / 500`, `2 / 500` | `103`, `575` |

  3. **Is BO usable at launch?**
     - **Yes.** Bolivia (`BO`) has **62.4%** flat-rate availability across the top 500 popular movies (vs 67.0% in ES and 73.2% in US) and deep catalogs on Netflix (`4,894`), Amazon Prime Video (`6,872`), Disney+ (`2,265`), HBO Max (`2,087`), MUBI (`575`), Paramount+ (`326`), and Apple TV+ (`120`).
  4. **Provider-ID nuances for `feat-012`:**
     - **Same brand, different IDs across countries:** Amazon Prime Video is `9` in `US` vs `119` in `ES`/`BO`; Paramount+ is `2616`/`2303` in `US` vs `531` in `BO`. Storing `streamable` as `"{country}:{provider_id}"` (`docs/architecture.md` §5) handles this naturally.
     - **Curated user-facing provider list per country:** `/watch/providers/movie` lists 97 (ES), 295 (US), and 40 (BO) entries, including pure rent/buy stores (`Apple TV Store` `2`, `Amazon Video` `10`), ad tiers (`Netflix Standard with Ads` `1796`, `Amazon Prime Video with Ads` `2100`), and third-party channels (`HBO Max Amazon Channel` `1825`). The `providers` collection should expose a curated list of primary flat-rate services per country (optionally aliasing ad-tier/channel IDs onto their parent service).
- **Evidence:**
  - `spikes/08-tmdb/report.json` (`watch_providers.countries.{ES,US,BO}` and `popular_500_probe.watch_providers_in_popular_500`) and `spikes/08-tmdb/snapshot_1.json`.
- **Changes:**
  - **Keep all three launch countries (`ES`, `US`, `BO`)** in `docs/product.md` §1 and `docs/architecture.md` (answers Q2).
  - Scope `providers` per country (`{country, provider_id, name, logo_path}`) with a curated list of major flat-rate services per country.

---

### 6. English data & missing `poster_path` (Architecture Q13)
> For a sample of popular movies, how many have an English overview, keywords and at least one review, and how many lack a `poster_path` (architecture Q13)?
> - *Changes:* enrichment quality, minimum data to include a movie.

- **Finding:**
  1. **Popular 500 movies (`GET /3/movie/{id}?language=en-US&append_to_response=keywords,reviews,watch/providers,credits`):**
     - **English `overview`:** **`500 / 500` (`100.0%`)**, median length `245` characters.
     - **`poster_path` present:** **`500 / 500` (`100.0%`)** — **`0 / 500` (`0.0%`) lack `poster_path`**.
     - **`keywords` (`>= 1`):** **`473 / 500` (`94.6%`)**; `>= 3` keywords: `451 / 500` (`90.2%`); median `15.0` keywords.
     - **`reviews` (`>= 1` English review):** **`414 / 500` (`82.8%`)**; `>= 3` reviews: `330 / 500` (`66.0%`); median `4.0` reviews.
     - **`runtime > 0`:** **`497 / 500` (`99.4%`)**.
     - **`genres` (`>= 1`):** **`499 / 500` (`99.8%`)**.
     - **`credits` (director + cast):** **`496 / 500` (`99.2%`)**.
     - **`overview` + `>= 1` keyword:** **`473 / 500` (`94.6%`)**.
     - **`overview` + `>= 1` keyword + `>= 1` review:** **`410 / 500` (`82.0%`)**.
  2. **Deep flat-rate catalog check (`480` movies sampled across `/discover/movie` pages `1, 10, 50, 100, 200, 300, 400, 500` = ranks `1..10,000` in ES, US, and BO):**
     - **Missing `poster_path`:** **`0 / 160` (`0.0%`) in ES**, **`0 / 160` (`0.0%`) in US**, **`0 / 160` (`0.0%`) in BO** (`0 / 480` total).
     - **Missing `overview`:** **`0 / 160` (`0.0%`) in ES**, **`0 / 160` (`0.0%`) in US**, **`0 / 160` (`0.0%`) in BO** (`0 / 480` total).
- **Evidence:**
  ```json
  "english_data_completeness": {
    "has_overview": 500, "has_overview_pct": 100.0, "overview_chars_median": 245.0,
    "has_at_least_1_keyword": 473, "has_at_least_1_keyword_pct": 94.6, "keywords_median": 15.0,
    "has_at_least_1_review": 414, "has_at_least_1_review_pct": 82.8, "reviews_median": 4.0,
    "has_poster_path": 500, "has_poster_path_pct": 100.0,
    "missing_poster_path_count": 0, "missing_poster_path_pct": 0.0,
    "has_runtime_gt_0": 497, "has_genres": 499, "has_director_and_cast": 496
  },
  "deep_flatrate_catalog_sample": {
    "ES": { "sampled_movies_across_pages_1_to_500": 160, "missing_poster_path": 0, "missing_overview": 0 },
    "US": { "sampled_movies_across_pages_1_to_500": 160, "missing_poster_path": 0, "missing_overview": 0 },
    "BO": { "sampled_movies_across_pages_1_to_500": 160, "missing_poster_path": 0, "missing_overview": 0 }
  }
  ```
- **Changes:**
  - **Minimum data gate at Ingest:** Require non-empty English `overview`, `runtime > 0`, `>= 1` genre, and non-null `poster_path` (`> 99%` of popular streamable movies pass all four).
  - **Architecture Q13 (Decided by owner, 2026-11-14):** Leave movies without a `poster_path` out of the corpus at ingest time (`0.0%` missing across 500 popular and 480 deep-sampled flat-rate movies; no UI placeholder needed).
  - **Enrichment inputs:** Treat `keywords` (94.6% present) as optional enrichment context alongside `overview`, `genres`, and `credits`, so the 5.4% of movies without TMDB keywords still get enriched cleanly.

---

### 7. Rate of change
> How many flat-rate titles per country change from one day to the next (added or removed), and how many of the added ones are new to our corpus?
> - *Changes:* refresh schedule, and how often ingest must re-run to add new titles (architecture Q12).

> **Update (feat-017, 2026-11-21):** the week-long extrapolation in finding 1 and the "over 90% are rotations" claim in finding 2 are not supported ([checkpoint review](../checkpoint-2026-11-16/04-spikes-foundations.md)). feat-017 re-measured churn from two complete catalogue crawls 5.3 days apart: see [spike 16, Q1](16-recommendation-signals-and-ranking.md#q1-corpus-selection-the-1984-problem-retention). The per-provider changes on the Popular 500 below are still the only measurement of provider swaps within a country.

- **Finding:**
  1. **Measured 24.5-hour flat-rate provider churn (`spikes/08-tmdb/snapshot_1.json` at `2026-11-14T14:48:37Z` vs. `spikes/08-tmdb/snapshot_2.json` at `2026-11-15T15:18:19Z`):**
     - Across the exact same **500 popular movies** (`common_popular_movies_compared: 500`):
       - **ES:** **`11 / 500` movies (`2.2%`)** changed flat-rate availability (`+9` added movie-provider pairs, `-6` removed movie-provider pairs; e.g., *The Lord of the Rings: The Return of the King* `#122` added to Amazon Prime Video ES `ES:119`/`ES:2100`; *The Hangover* `#18785` removed from HBO Max ES `ES:1899`/`ES:1825`; *Gladiator* `#98` and *Terminator 2* `#280` added to Tivify `ES:1838`).
       - **US:** **`13 / 500` movies (`2.6%`)** changed flat-rate availability (`+14` added movie-provider pairs, `-10` removed movie-provider pairs; e.g., *The Hunger Games* films `#70160`, `#101299`, `#131631` moved onto Peacock `US:386`/`US:387`; *GoodFellas* `#769`, *The Lion King* `#8587`, and *Beauty and the Beast* `#10020` left fuboTV `US:257`; *The Green Mile* `#497` and *Saving Private Ryan* `#857` left Philo `US:2383`).
       - **BO:** **`3 / 500` movies (`0.6%`)** changed flat-rate availability (`+3` added movie-provider pairs, `0` removed; e.g., *The Lord of the Rings: The Return of the King* `#122` added to Amazon Prime Video BO `BO:119`).
     - Extrapolated to a 10k–20k movie corpus, **~100–500 movies change flat-rate provider tags per day** (`~0.6%–2.6%` daily churn), confirming that **daily availability refresh is mandatory** to uphold Product Rule P1 (without daily refresh, `~2%` of popular movies go stale per day and `~10–15%` within a week).
  2. **How many newly added flat-rate titles are genuinely new to our corpus?**
     - **Top 100 Popular Flat-Rate per country:** `ES` had `7` additions (`0` outside Snapshot 1's Popular 500), `US` had `16` additions (`1` outside Popular 500), and `BO` had `7` additions (`1` outside Popular 500). Over **90% of daily flat-rate additions on major services are catalog rotations of existing movies** (like *Return of the King* or *The Hunger Games*) that are **already stored, enriched, and embedded in a 10k–20k corpus**!
     - **Top 100 Newest Release Date Flat-Rate per country (`per_country_newest_100_flatrate_churn`):** Only **`1` brand-new release in ES**, **`3` in US**, and **`1` in BO** entered the newest-releases flat-rate list over 24.5 hours.
     - **Global `/3/movie/changes` endpoint:** Reports `16,634` movie IDs (`167` pages) modified across all of TMDB in 24h (mostly metadata/translations on obscure titles), so refreshing our stored corpus directly via `/movie/{id}/watch/providers` (`~7–14 min` at `25 req/s`) is simpler and more direct.
- **Evidence:**
  ```text
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
    },
    "per_country_top_100_flatrate_churn": {
      "ES": { "top_100_added": 7, "top_100_removed": 8, "added_not_in_snapshot1_popular_500": 0 },
      "US": { "top_100_added": 16, "top_100_removed": 11, "added_not_in_snapshot1_popular_500": 1 },
      "BO": { "top_100_added": 7, "top_100_removed": 6, "added_not_in_snapshot1_popular_500": 1 }
    },
    "per_country_newest_100_flatrate_churn": {
      "ES": { "newest_100_added": 1, "newest_100_removed": 1, "added_not_in_snapshot1_popular_500": 0 },
      "US": { "newest_100_added": 3, "newest_100_removed": 3, "added_not_in_snapshot1_popular_500": 3 },
      "BO": { "newest_100_added": 1, "newest_100_removed": 1, "added_not_in_snapshot1_popular_500": 0 }
    }
  }
  ```
- **Changes (Architecture Q12):**
  - **Daily Refresh (`Refresh availability` job):** Run **daily** over stored movies (`/movie/{id}/watch/providers`, updating only `streamable` and `availability_updated_at`). Keep movies in MongoDB when `streamable` becomes `[]` so returning catalog rotations require zero re-enrichment or re-embedding.
  - **Weekly (or tiny daily delta) `Ingest → Enrich → Embed`:** Since >90% of daily provider additions are existing catalog titles and only `~1–5` brand-new releases per day enter flat-rate streaming across ES/US/BO, running candidate discovery + `Ingest → Enrich → Embed` **weekly** (or on the `< 10/day` brand-new IDs that pass our quality gate) keeps LLM and embedding costs near **$0**.

---

### 8. Images
> May the UI show TMDB posters and provider logos by linking to TMDB's image servers (storing only `poster_path` / `logo_path`)? Which sizes exist, and what attribution or usage limits apply?
> - *Changes:* the poster in each result (product.md §2), data model, UI.

- **Finding:**
  1. **Linking to TMDB's image CDN (`https://image.tmdb.org/t/p/`):** Explicitly supported and expected ([TMDB Image Basics](https://developer.themoviedb.org/docs/image-basics)). Storing only `poster_path` / `logo_path` in MongoDB and rendering `https://image.tmdb.org/t/p/{size}{path}` in the client requires zero image storage cost (`docs/architecture.md` §6).
  2. **Available sizes from `GET /3/configuration` (`spikes/08-tmdb/report.json` → `configuration`):**
     - `secure_base_url`: `"https://image.tmdb.org/t/p/"`
     - `poster_sizes`: `["w92", "w154", "w185", "w342", "w500", "w780", "original"]`
     - `logo_sizes`: `["w45", "w92", "w154", "w185", "w300", "w500", "original"]`
     - `backdrop_sizes`: `["w300", "w780", "w1280", "original"]`
  3. **Usage & attribution rules:**
     - Always use HTTPS (`secure_base_url`).
     - Use sized assets (`w342` or `w500` for movie cards; `w45` or `w92` for provider logos) rather than `original` to avoid unnecessary CDN bandwidth and keep mobile loads fast (`≈375 px` viewport).
     - Covered by the TMDB attribution and logo rules in Q2.
- **Evidence:**
  ```json
  "configuration": {
    "base_url": "http://image.tmdb.org/t/p/",
    "secure_base_url": "https://image.tmdb.org/t/p/",
    "poster_sizes": ["w92", "w154", "w185", "w342", "w500", "w780", "original"],
    "logo_sizes": ["w45", "w92", "w154", "w185", "w300", "w500", "original"],
    "backdrop_sizes": ["w300", "w780", "w1280", "original"]
  }
  ```
- **Changes:**
  - Store `poster_path` on `movies` and `logo_path` on `providers`.
  - Construct `poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"` (or `w500`) in the response mapper and `logo_url = f"https://image.tmdb.org/t/p/w92{logo_path}"` for provider badges.

## How
- Throwaway script in `spikes/08-tmdb/probe_tmdb.py` (never `src/`):
  - fetches `/configuration`, `/watch/providers/regions`, `/watch/providers/movie` + `/discover/movie` for ES, US and BO (questions 4, 5 and 8);
  - fetches 500 popular movies with `append_to_response=keywords,reviews,watch/providers,credits` and deep-samples 480 flat-rate movies across pages `1..500` (questions 3, 4 and 6);
  - verifies `/discover/movie` cross-provider monetization behavior (`--verify-discover`, question 4);
  - saves provider snapshots and compares two snapshots taken at least a day apart (`--compare`, question 7).
