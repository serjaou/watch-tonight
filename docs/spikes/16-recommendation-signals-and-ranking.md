---
id: feat-016
type: spike
status: questions ready   # questions ready -> answered
timebox: 2 sessions
---
# Spike: Movie corpus selection, external enrichment signals, emotional profile schema, and hybrid ranking

## Why
The core value of `watch-tonight` is **recommendation quality**: turning a user's free-text mood (from a vague *"tired, want something light"* to a hyper-specific *"gritty 90s neo-noir with a twist"*) into 5 streamable movies they genuinely want to watch tonight, each backed by a grounded factual pitch (`docs/product.md` P1–P3).

Before we lock the MongoDB schema and slice the MVP in `feat-012`, we want **80–90% of the movie document schema, emotional profile schema, and selection/ranking algorithm validated on real data**, rather than discovering after building the pipeline that pure vector cosine similarity over basic plot synopses recommends obscure low-quality filler.

---

## 1. Context: What We Know & Have Decided So Far

### 1.1 How many movies exist vs. our target corpus (`feat-008`, `feat-009`)
- **Total on TMDB:** ~1.1 million movie entries globally, but the vast majority are unstreamable, obscure shorts, student films, or entries with almost no viewer ratings.
- **Streamable flat-rate in ES, US, and BO (`feat-008`):** Across subscription services in Spain (`ES`), the United States (`US`), and Bolivia (`BO`), there are roughly **25,000–35,000 unique movies** available on flat-rate subscriptions (`flatrate`), of which **~10,000–20,000** have meaningful audience engagement.
- **Atlas M0 storage ceiling (`feat-009`):** Our empirical probe (`spikes/09-atlas/report.json`) proved that **20,000 full movie documents + vectors + HNSW vector index** fit comfortably inside MongoDB Atlas M0's free `512 MiB` limit at every candidate dimension (`~27.6%` at 384-d, `~54.2%` at 768-d, `~70.5%` at 1024-d with float64 arrays, or **`17.4%–36.5%`** using `bson.binary.Binary.from_vector(..., FLOAT32)`).

### 1.2 How ingestion works (`feat-008`, `docs/architecture.md` §4)
1. **Candidate discovery:** Query TMDB `/discover/movie` (`watch_region=ES|US|BO`, `with_watch_monetization_types=flatrate`) to collect candidate TMDB movie IDs that are streamable in at least one launch country.
   - *Finding from `feat-008` Q4:* `/discover/movie` has a hard 500-page (`10,000`-result) pagination cap per query and cannot be filtered per provider reliably due to cross-provider monetization bleed. Therefore, `/discover/movie` is used **only** to gather candidate movie IDs (sliced by popularity/vote count/release window if >10k), never to assign `streamable` provider tags.
2. **Per-movie bundle fetch (`1` HTTP call per movie):**
   - `GET /3/movie/{id}?language=en-US&append_to_response=keywords,reviews,watch/providers,credits,release_dates`
   - Measured throughput in `feat-008` Q3: **25.2 req/s** (`10` concurrent workers, `0` HTTP `429`s), meaning **20,000 movies take ~14 minutes** to fetch.
3. **Daily availability refresh:**
   - Queries `/movie/{id}/watch/providers` per stored movie and extracts `results[country]["flatrate"]` (for `ES`, `US`, `BO` in one call) to rewrite `streamable: ["ES:8", "US:337", ...]` and `availability_updated_at` (P1, P6).

### 1.3 What TMDB provides in that single per-movie call (`feat-008` Q6)
From our 500-movie popular probe + 480-movie deep flat-rate probe (`spikes/08-tmdb/report.json`), a single `/movie/{id}?append_to_response=...` response provides:
- **Core identity & display facts:**
  - `id` (TMDB integer ID), `imdb_id` (e.g. `"tt0133093"` — crucial for joining external datasets!), `title`, `original_title`, `original_language`, `origin_country`, `release_date` (`year`), `runtime` (`99.4%` > 0), `poster_path` (`100.0%` present), `backdrop_path`.
- **Narrative & thematic inputs:**
  - `tagline` (short marketing hook), `overview` (English synopsis, `100.0%` present, median `245` chars), `genres` (`99.8%` present), `keywords` (`94.6%` have $\ge 1$ keyword; median `15` keywords per movie, e.g. `["simulated reality", "dystopia", "artificial intelligence"]`).
- **People, franchise & maturity metadata:**
  - `credits`: `directors`, `writers`, top-billed `cast`, `composer`.
  - `belongs_to_collection`: `{id, name}` when the movie is part of a series/franchise (e.g. *The Lord of the Rings Collection*).
  - `release_dates`: MPAA / local age certifications (e.g. `G`, `PG`, `PG-13`, `R`, `NC-17`).
- **Popularity, rating & crowd signals (returned by TMDB, but NOT yet in `docs/architecture.md` §5!):**
  - `vote_average` (TMDB 0–10 user score), `vote_count` (number of user ratings), `popularity` (TMDB's daily decaying trending score driven by page views, searches, and watchlist additions).
- **Community reviews (`reviews`):**
  - `82.8%` of popular movies have $\ge 1$ English user review (median `4` reviews).
  - *Legal/terms constraint (`feat-008` Q1):* Under TMDB terms, we must **not** persist or redistribute raw user reviews (`review_snippets`) in our database or API/MCP responses, and any LLM call that touches TMDB data must **not** train on inputs (`feat-011` Q2). However, transient in-memory use during offline profile extraction (with training opt-out) or using public non-TMDB signals is worth evaluating.

### 1.4 How the Emotional Profile & Online Search work (`docs/architecture.md` §3–§4, Q11)
- **Why an LLM is used offline (`Enrich` job):**
  - A TMDB `overview` states *plot mechanics* ("A man moves to a coastal town after a personal loss"), not *emotional experience* ("slow-burn, quietly devastating, cathartic, high emotional weight").
  - The **Enrich** job runs an LLM **once offline per movie** to synthesize the movie's metadata + keywords into a structured `profile`:
    1. **Closed-vocabulary fields (`Q11`):** `intensity` (1–5 scale), `content_warnings` (fixed enum), `pacing`, `tone`, `themes` — indexed as pre-filters in Atlas `$vectorSearch` (`feat-009` Q2) and checked deterministically in `application` (P3).
    2. **Dense experiential `summary`:** A rich text paragraph describing how the movie feels to watch, which the **Embed** job converts into the vector stored in `movies.embedding`.
- **How online recommendation works (`SearchMovies` use case — 2 LLM calls + 1 vector search):**
  1. **Step 1 (`Validate`):** Check prompt length ($\le 500$ chars, P4), country, and providers.
  2. **Step 2 (`Understand` — Online LLM Call 1):** Translates the user's free-text mood (in any language, Q9) into:
     - structured filters over the shared closed vocabulary (`max_runtime`, `max_intensity`, `avoid` warnings), merged with UI constraints (stricter wins);
     - an **expanded English semantic search description** written in the same experiential style as `profile.summary`.
  3. **Step 3 (`Retrieve` — Atlas `$vectorSearch`):** Embeds the expanded query and runs `$vectorSearch` with pre-filters (`streamable` `$in`, `runtime` $\le$, `_id` `$nin`, `profile.intensity` $\le$, `profile.content_warnings` `$nin`), returning the top **30–50** candidates in `~60 ms` p50 / `~121 ms` p95 (`feat-009` Q5).
  4. **Step 4 (`Check & Rank candidates` — deterministic in `application`):** Verifies P1 and P3 deterministically.
  5. **Step 5 (`Re-rank & pitch` — Online LLM Call 2):** Selects the final **5** movies from the top candidates and writes a grounded pitch ($\le 350$ chars, about the movie never the user, no spoilers, P2 & ADR 0001).
  6. **Step 6 (`Validate output`):** Verifies IDs are from Step 4 and pitches $\le 350$ chars; falls back to *Results without pitches* (Q8) if the LLM fails after 1 retry.

---

## 2. The Four Gaps in Pure Vector Similarity (Why This Spike Exists)

If Step 3 simply takes the top 30–50 movies by raw vector cosine similarity (`vectorSearchScore`) over `profile.summary` and hands them to the LLM, four failure modes appear:

### Gap A: The "1984 Movie Problem" (Quality, Era & Cultural Relevance Priors)
- **Problem:** A mediocre, forgotten 1984 TV movie (`vote_average: 5.1`, `vote_count: 18`) whose synopsis describes a "lighthearted romantic comedy" can have the exact same cosine similarity (`0.84`) to *"something light and romantic"* as *When Harry Met Sally* (1989, `7.7`, `4,200` votes) or *Palm Springs* (2020, `7.4`, `3,100` votes). Most users do **not** want a random movie from 1984 unless:
  1. it is a genuinely beloved, iconic classic (`high rating` + `high vote count`), **or**
  2. the user explicitly asked for an 80s/classic film, **or**
  3. its semantic match to a very specific niche prompt is substantially stronger than modern alternatives.
- **What we need to design & test:**
  1. **Age-aware corpus admission gate (Ingest filter):** Exclude low-engagement filler before spending LLM tokens on enrichment. For example, a movie from $< 2$ years ago may only need `vote_count >= 30`, whereas a movie $> 15$ years old may need `vote_count >= 200–500` and a minimum Bayesian quality score to earn a spot in the 20k corpus.
  2. **Bayesian Weighted Rating (`quality_score` / `WR`):** Raw average ratings are noisy for low vote counts (a `9.0` with 3 votes is worse than a `7.6` with 5,000 votes). Using IMDb's Bayesian credibility formula:
     $$\text{WR} = \frac{v}{v + m} R + \frac{m}{v + m} C$$
     (where $R$ is the movie's rating, $v$ is its vote count, $C$ is the corpus mean rating, and $m$ is the prior weight, e.g. $m = 500$ votes) gives a single calibrated `0–10` quality prior.
  3. **Era / Recency decay & Trending boost (`popularity`):** Test a gentle age discount on non-classic older titles alongside a logarithmic boost from `popularity` (current cultural momentum), deactivated when the user asks for older/classic cinema.

### Gap B: User Prompt Specificity (Broad/Vague vs. Hyper-Specific Queries)
- **Problem:**
  - **Broad prompt:** *"I feel tired, give me something easy to watch"* → 3,000 movies in the corpus match "easy to watch". Small differences in cosine similarity (`0.78` vs `0.75`) are mostly embedding noise. Here, **quality (`WR`), crowd appeal (`vote_count`), and trending (`popularity`)** must drive candidate ranking.
  - **Specific prompt:** *"A slow-burn sci-fi mystery where a small crew is trapped on a spaceship or station and paranoia sets in"* → Only ~15–30 movies truly fit. Here, **semantic similarity (`vectorSearchScore`)** must dominate so a `6.9`-rated exact match (*Sunshine* or *Moon*) beats a `8.5`-rated unrelated drama.
- **What we need to design & test:**
  - Add `specificity` (`"broad" | "medium" | "specific"`) and optional soft intent signals (`era_preference`, `mainstream_vs_indie`) to Step 2's `QueryIntent` schema, and use `specificity` to dynamically weight `semantic_score` vs. `quality_score` vs. `popularity_score` in Step 4!

### Gap C: External Enrichment Sources (Value vs. Complexity/Cost)
What external data beyond TMDB's basic metadata can make our quality priors and emotional profiles significantly better while keeping our **$0 budget** (`docs/product.md` §1) and legal terms?
1. **IMDb Non-Commercial Datasets (`https://datasets.imdbws.com/`) — Prime Candidate:**
   - IMDb publishes free daily gzipped TSV files (`title.ratings.tsv.gz`, ~7 MB compressed, ~1.5M titles) containing `tconst` (`imdb_id`), `averageRating`, and `numVotes`.
   - Because TMDB's `/movie/{id}` already returns `imdb_id`, joining IMDb ratings + vote counts offline is an **in-memory hash join** taking $< 3$ seconds for 20,000 movies with **zero API calls and $0 cost**.
   - *Why it matters:* IMDb has 10×–50× more votes per movie than TMDB (`The Matrix` has ~2.1M votes on IMDb vs ~25k on TMDB), making Bayesian `WR` and classic-movie detection dramatically more accurate.
2. **Transient TMDB `reviews` & `keywords` during offline LLM enrichment:**
   - Already fetched in the same single TMDB HTTP call (`append_to_response=keywords,reviews`).
   - Testing whether passing truncated review excerpts transiently to the offline enrichment prompt (without storing raw reviews in MongoDB, and using an LLM API tier that does not train on inputs) improves the accuracy of `tone`, `pacing`, `viewing_effort`, and `ending_feel`.
3. **Wikidata / Wikipedia plot & reception or OMDb (Rotten Tomatoes / Metacritic):**
   - Evaluate whether OMDb (1,000/day free cap → bottleneck for 20k movies) or Wikipedia reception summaries add enough signal over `TMDB + IMDb TSV` to justify any extra complexity, or if `TMDB + IMDb TSV` already hits the 90% sweet spot.

### Gap D: Richer Emotional Profile Schema & Diversity in the Final 5
- **Profile dimensions that matter for mood selection:**
  - Beyond `tone`, `pacing`, `intensity`, `themes`, and `content_warnings`, what fields help both the embedding and the Step 5 re-ranker?
    - `viewing_effort`: `"comfort_background" | "easy" | "engaging" | "demanding"` (cognitive load).
    - `emotional_arc` / `ending_feel`: `"uplifting" | "warm_resolved" | "bittersweet" | "tense_cathartic" | "bleak_or_ambiguous"` (avoids recommending a movie with a soul-crushing ending when someone asks for a feel-good drama!).
    - `humor_style` (when applicable): `"none" | "witty_dry" | "warm_gentle" | "absurd_satirical" | "broad_slapstick"`.
- **Candidate diversity (Step 4 → Step 5):**
  - Deduplicating franchises (`belongs_to_collection`) so we never return *John Wick 1*, *John Wick 2*, and *John Wick 3* in the same 5 recommendations, and ensuring the 25–30 candidates passed to Step 5 span slightly different angles of the user's mood.

---

## 3. Questions to Answer in This Spike

Each answer must include the finding, empirical evidence from `spikes/16-recommendation/`, and what it changes in `docs/architecture.md`.

1. **Corpus selection & "the 1984 problem".**
   - Across TMDB's flat-rate streamable catalog for ES, US, and BO, how many movies survive different quality/engagement gates (e.g. `vote_count` + age-adjusted minimum votes/rating)?
   - What corpus admission rule gives us the best 10k–20k movie pool where older movies (pre-2000) are iconic/well-regarded classics while recent releases (last 1–3 years) aren't unfairly filtered out by lower cumulative vote counts?
   - *Changes:* Ingest job filtering rules, target corpus size (`docs/architecture.md` §4).

2. **External data sources (`IMDb TSV`, transient `TMDB reviews`, etc.).**
   - How many of our sampled TMDB streamable movies have a valid `imdb_id` that matches `title.ratings.tsv.gz` from `datasets.imdbws.com`, and how much does combining IMDb `averageRating` + `numVotes` with TMDB `vote_average` + `vote_count` + `popularity` improve the Bayesian quality score (`WR`)?
   - What are the exact licensing/non-commercial terms of `datasets.imdbws.com` for a public portfolio project (`docs/product.md` §1)?
   - Does passing transient TMDB `reviews` (or Wikipedia reception) to the offline enrichment LLM noticeably improve profile accuracy over `overview + tagline + keywords + genres + credits` alone, or is `TMDB bundle + IMDb ratings TSV` the optimal 90% design?
   - *Changes:* Offline pipeline inputs (`docs/architecture.md` §1 & §4), attribution (`P5` if applicable), `movies` schema (§5).

3. **Movie document & Emotional Profile schema (locking 80–90% before `feat-012`).**
   - What is the concrete v1 schema for `movies` and `movies.profile` (including closed-vocabulary enums for `tone`, `pacing`, `intensity`, `viewing_effort`, `ending_feel`, `content_warnings`, plus the text `summary` that gets embedded)?
   - What exact text template should be fed to the embedding model (just `profile.summary`, or a structured concatenation of `tone + pacing + viewing_effort + ending_feel + themes + summary`)?
   - *Changes:* `docs/architecture.md` §3 (step 2 & step 4 closed vocabulary) and §5 (`movies` document schema).

4. **Hybrid retrieval & ranking formula (Vector + Quality + Era/Recency + Popularity + Specificity).**
   - Since Atlas `$vectorSearch` orders candidates purely by vector similarity (`numCandidates` → top $K$), how many candidates should Step 3 retrieve ($K = 50$ vs $K = 100$ vs $K = 150$) so that high-quality matches aren't crowded out before Step 4's hybrid re-scoring?
   - What hybrid scoring formula in Step 4:
     $$\text{Score}(m, q) = w_{\text{sem}}(q) \cdot \widehat{\text{sim}}(m, q) + w_{\text{qual}}(q) \cdot \widehat{\text{WR}}(m) + w_{\text{rec}}(q) \cdot \text{era\_factor}(m, q) + w_{\text{pop}}(q) \cdot \widehat{\text{pop}}(m)$$
     produces the best top-25 pool for Step 5 across both **broad/vague prompts** and **hyper-specific prompts**, while preventingfranchise duplicates (`belongs_to_collection`)?
   - *Changes:* `docs/architecture.md` §3 (Query steps 2, 3, 4, and 5).

---

## 4. How
- Throwaway scripts and evaluation artifacts in `spikes/16-recommendation/` (never `src/`):
  1. Pull a stratified sample of **~200–300 real streamable movies** from TMDB across eras (1970s–2026) and quality tiers (iconic classics, modern crowd-pleasers, indie hidden gems, and low-rated filler), and join them with IMDb's `title.ratings.tsv.gz`.
  2. Enrich a representative subset (**~40–60 movies**) with candidate LLM profile schemas (comparing with vs. without transient review snippets) and embed them using the model selected in `feat-010`.
  3. Run **10–12 test mood queries** (ranging from vague *"tired, something light"* to specific *"tense submarine or single-location thriller"*, plus era-specific queries) and compare the top-25 and top-5 picks produced by:
     - **Baseline:** pure `$vectorSearch` cosine similarity;
     - **Hybrid v1:** `$vectorSearch` ($K = 100$) → Step 4 hybrid re-score (`similarity + Bayesian WR + era/recency + popularity` weighted by query `specificity` + collection deduplication).
  4. Record the side-by-side results, the winning hybrid formula, and the proposed v1 `movies` + `profile` schema in this file for owner review before `feat-012`.
