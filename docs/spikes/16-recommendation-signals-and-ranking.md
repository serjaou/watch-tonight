---
id: feat-016
type: spike
status: answered   # questions ready -> answered
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

### 1.2 How ingestion works & what to do with unstreamable movies (`feat-008`, `docs/architecture.md` §4)
1. **Candidate discovery:** Query TMDB `/discover/movie` (`watch_region=ES|US|BO`, `with_watch_monetization_types=flatrate`) to collect candidate TMDB movie IDs that are streamable in at least one launch country.
   - *Finding from `feat-008` Q4:* `/discover/movie` has a hard 500-page (`10,000`-result) pagination cap per query and cannot be filtered per provider reliably due to cross-provider monetization bleed. Therefore, `/discover/movie` is used **only** to gather candidate movie IDs (sliced by popularity/vote count/release window if >10k), never to assign `streamable` provider tags.
2. **Per-movie bundle fetch (`1` HTTP call per movie):**
   - `GET /3/movie/{id}?language=en-US&append_to_response=keywords,reviews,watch/providers,credits,release_dates`
   - Measured throughput in `feat-008` Q3: **25.2 req/s** (`10` concurrent workers, `0` HTTP `429`s), meaning **20,000 movies take ~14 minutes** to fetch.
3. **Daily availability refresh:**
   - Queries `/movie/{id}/watch/providers` per stored movie and extracts `results[country]["flatrate"]` (for `ES`, `US`, `BO` in one call) to rewrite `streamable: ["ES:8", "US:337", ...]` and `availability_updated_at` (P1, P6).
4. **Should we pre-ingest movies that are NOT currently streamable? (Lifecycle & retention trade-off):**
   - **Why pre-ingesting *all* unstreamable movies is a bad idea:**
     - **We only detect availability changes once a day anyway** (during the daily refresh job, never mid-query). When a new movie becomes streamable on Netflix/Prime/Disney+, running `/discover/movie?...&with_watch_monetization_types=flatrate` at the start of the daily job finds those newly streamable IDs in ~30 seconds, and ingesting + enriching + embedding the **~10–50 movies that became newly streamable that day** takes **under 1 minute**.
     - **Storage & HNSW index budget (`feat-009`):** Every movie stored with a vector in `movies` consumes Atlas M0's `512 MiB` quota and bloats the HNSW vector graph (`mongot` indexes every vector in the collection even if `streamable: []` filters it out at query time).
     - **Enrichment & refresh cost:** Paying LLM tokens to enrich 30,000 unstreamable movies that may never hit flat-rate in ES/US/BO wastes enrichment budget and slows down daily refresh.
   - **What we *should* do instead (The "Keep on Churn + Optional High-Priority Buffer" policy):**
     1. **Never delete a stored movie when it leaves streaming (`streamable: []`):** Once a movie has been ingested, enriched, and embedded, if it rotates off Netflix/Prime later, we **keep the document in MongoDB with `streamable: []`**. Its LLM profile and vector are already paid for, so if it returns to streaming 2 months later, the daily refresh simply updates `streamable: ["ES:8"]` and it is searchable again in 0 seconds with zero LLM cost!
     2. **Daily delta ingest of newly streamable titles:** Run candidate discovery along with the daily refresh (or every few days, informed by `feat-008` Q7 churn numbers) and immediately run `Ingest → Enrich → Embed` on the small delta of newly streamable movies that pass our quality gate.
     3. *(Optional evaluated in Q1 below):* Pre-ingest a small buffer (~500–1,000) of **brand-new theatrical releases** (`popularity` top tier from the last 6 months not yet on flat-rate), since those are the #1 movies likely to land on streaming next and the most valuable if we later add the "rent/buy opt-in" feature (`docs/product.md` §8).

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

### Gap B: User Prompt Specificity & The "Mirror Schema" Between LLM Step 2 and Movie Data
- **Problem:**
  - **Broad prompt:** *"I feel tired, give me something easy to watch"* → 3,000 movies in the corpus match "easy to watch". Small differences in cosine similarity (`0.78` vs `0.75`) are mostly embedding noise. Here, **quality (`WR`), crowd appeal (`vote_count`), and trending (`popularity`)** must drive candidate ranking.
  - **Specific prompt:** *"A slow-burn sci-fi mystery where a small crew is trapped on a spaceship or station and paranoia sets in"* → Only ~15–30 movies truly fit. Here, **semantic similarity (`vectorSearchScore`)** must dominate so a `6.9`-rated exact match (*Sunshine* or *Moon*) beats a `8.5`-rated unrelated drama.
- **Core Architectural Principle — The 3-Channel Mirror Schema (`Understand` $\leftrightarrow$ `movies`):**
  For the online LLM (Step 2 `Understand`) to translate a free-text prompt into a high-precision retrieval + ranking call, **every parameter Step 2 outputs must map 1-to-1 onto a field stored on the movie document**:

  | Channel | What Step 2 (`Understand` LLM) extracts from the user prompt | What `movies` / `movies.profile` stores offline to match it | How it is applied |
  |---|---|---|---|
  | **1. Hard Atlas `$vectorSearch` Pre-Filters** | • `max_runtime` (`int \| null`)<br>• `max_intensity` (`1..5 \| null`)<br>• `avoid_warnings` (`list[ContentWarning]`)<br>• `year_min` / `year_max` (`int \| null`, e.g. *"80s movie"* → `1980..1989`, *"recent"* → `2020..2026`) | • `streamable` (`["ES:8", ...]`)\<br>• `runtime` (`int`)<br>• ` year` (`int`, indexed as `filter`!)<br>• `profile.intensity` (`1..5`)<br>• `profile.content_warnings` (`list[str]`) | Pushed directly into `$vectorSearch.filter` (`$and`) so Atlas only scores candidates that obey all hard constraints. |
  | **2. Symmetric Embedding Template** | • `target_tone` (`list[Tone]`)<br>• `target_pacing` (`Pacing \| null`)<br>• `target_effort` (`ViewingEffort \| null`)<br>• `target_ending` (`EndingFeel \| null`)<br>• `target_themes` (`list[str]`)<br>• `semantic_description` (`str`, 2–3 sentences in movie-profile style) | • `profile.tone`<br>• `profile.pacing`<br>• `profile.viewing_effort`<br>• `profile.ending_feel`<br>• `profile.themes`<br>• `profile.summary` | Both the movie offline and the query online are formatted into the **exact same structured text template** before embedding: `Tone: ... \| Pacing: ... \| Effort: ... \| Ending: ... \| Themes: ... \| Summary: ...`. This aligns the query vector and movie vector in the same semantic subspace. |
  | **3. Deterministic Hybrid Ranking Controls (Step 4)** | • `specificity`: `"broad" \| "medium" \| "specific"`<br>• `era_mode`: `"modern_default" \| "classic_or_any_era"` (disables recency decay when the user asks for *"classics"*, *"old school"*, or a past decade!)<br>• `acclaim_preference`: `"crowd_pleaser" \| "critically_acclaimed" \| "hidden_gem" \| "any"` | • `quality_score` (Bayesian `WR` combining IMDb + TMDB / RT)<br>• `imdb_rating`, `imdb_votes`<br>• `rt_tomatometer` *(if available)*<br>• `tmdb_popularity`<br>• `year`<br>• `collection_id` (`belongs_to_collection`) | Step 4 re-scores the top $K$ (`100`) vector candidates deterministically using `specificity` and `era_mode`, deduplicates franchises (`collection_id`), and passes the top `25–30` with their structured fields + scores to Step 5 (`Re-rank & pitch`). |

### Gap C: External Enrichment Sources (Value vs. Complexity/Cost)
What external data beyond TMDB's basic metadata can make our quality priors and emotional profiles significantly better while keeping our **$0 budget** (`docs/product.md` §1) and legal terms?
1. **IMDb Non-Commercial Datasets (`https://datasets.imdbws.com/`) — Prime Candidate:**
   - IMDb publishes free daily gzipped TSV files (`title.ratings.tsv.gz`, ~7 MB compressed, ~1.5M titles) containing `tconst` (`imdb_id`), `averageRating`, and `numVotes`.
   - Because TMDB's `/movie/{id}` already returns `imdb_id`, joining IMDb ratings + vote counts offline is an **in-memory hash join** taking $< 3$ seconds for 20,000 movies with **zero API calls and $0 cost**.
   - *Why it matters:* IMDb has 10×–50× more votes per movie than TMDB (`The Matrix` has ~2.1M votes on IMDb vs ~25k on TMDB), making Bayesian `WR` and classic-movie detection dramatically more accurate.
2. **Transient TMDB `reviews` & `keywords` during offline LLM enrichment:**
   - Already fetched in the same single TMDB HTTP call (`append_to_response=keywords,reviews`).
   - Testing whether passing truncated review excerpts transiently to the offline enrichment prompt (without storing raw reviews in MongoDB, and using an LLM API tier that does not train on inputs) improves the accuracy of `tone`, `pacing`, `viewing_effort`, and `ending_feel`.
3. **Wikidata / OMDb (Rotten Tomatoes / Metacritic) / Wikipedia reception:**
   - **Wikidata SPARQL / dump (`$0`, public domain CC0):** Wikidata stores Rotten Tomatoes IDs, Metacritic scores, Academy Award / festival wins, and links to English Wikipedia articles keyed by `imdb_id` (`P345`) or TMDB ID (`P4947`).
   - **OMDb API (`imdb_id` → Rotten Tomatoes `%`, Metacritic score, `Awards` string):** Free key allows 1,000 calls/day (or $1/month Patron key allows 100,000 calls/day — within our "small spend is fine when it clearly improves quality with owner approval" rule in `docs/product.md` §1).
   - We will test in Question 2 whether adding **Rotten Tomatoes / Metacritic / Awards** (via Wikidata or OMDb) on top of **IMDb `title.ratings.tsv.gz` + TMDB** materially improves ranking (especially for separating "critically acclaimed indie" from "popular crowd-pleaser").

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

1. **Corpus selection, "the 1984 problem", and unstreamable movie retention.**
   - Across TMDB's flat-rate streamable catalog for ES, US, and BO, how many movies survive different quality/engagement gates (e.g. `vote_count` + age-adjusted minimum votes/rating)?
   - What corpus admission rule gives us the best 10k–20k movie pool where older movies (pre-2000) are iconic/well-regarded classics while recent releases (last 1–3 years) aren't unfairly filtered out by lower cumulative vote counts?
   - **Unstreamable retention & buffer policy:** Confirm the storage/refresh impact of keeping previously enriched movies when they rotate off streaming (`streamable: []`) vs. pre-ingesting a small buffer (~500–1,000) of recent high-popularity theatrical releases before they land on flat-rate streaming.
   - *Changes:* Ingest & Refresh job rules, target corpus size (`docs/architecture.md` §4).

2. **External data sources (`IMDb TSV`, `Rotten Tomatoes / Metacritic / Awards`, transient `TMDB reviews`).**
   - How many of our sampled TMDB streamable movies have a valid `imdb_id` that matches `title.ratings.tsv.gz` from `datasets.imdbws.com`, and how much does combining IMDb `averageRating` + `numVotes` with TMDB `vote_average` + `vote_count` + `popularity` improve the Bayesian quality score (`WR`)?
   - Can we also enrich movies with **Rotten Tomatoes / Metacritic / Awards** (via free Wikidata SPARQL/dumps or OMDb) and does that materially improve separating "critically acclaimed" from "mainstream crowd-pleaser"?
   - What are the exact licensing/non-commercial terms of `datasets.imdbws.com` (and Wikidata/OMDb if used) for a public portfolio project (`docs/product.md` §1)?
   - Does passing transient TMDB `reviews` to the offline enrichment LLM noticeably improve profile accuracy over `overview + tagline + keywords + genres + credits` alone?
   - *Changes:* Offline pipeline inputs (`docs/architecture.md` §1 & §4), attribution (`P5` if applicable), `movies` schema (§5).

3. **Mirror Schema: `QueryIntent` (Step 2) $\leftrightarrow$ `movies` & `movies.profile` (locking 80–90% before `feat-012`).**
   - What is the concrete v1 schema for `movies` and `movies.profile` (including closed-vocabulary enums for `tone`, `pacing`, `intensity`, `viewing_effort`, `ending_feel`, `humor_style`, `content_warnings`, plus `year`, `quality_score`, `imdb_rating`, `imdb_votes`, `collection_id`, and `summary`)?
   - What is the exact mirroring `QueryIntent` schema output by Step 2 (`Understand`) across all 3 channels:
     1. Hard `$vectorSearch` pre-filters (`streamable`, `runtime`, `_id`, `profile.intensity`, `profile.content_warnings`, plus `year` range when the user specifies a decade/era);
     2. Symmetric structured text template for embedding (aligning query embedding format 1-to-1 with movie embedding format);
     3. Step 4 hybrid ranking controls (`specificity`, `era_mode` to disable recency decay when the user asks for *"classics"* or a past era, `acclaim_preference`, `preferred_viewing_effort`, `preferred_ending_feel`)?
   - *Changes:* `docs/architecture.md` §3 (steps 2, 3, and 4) and §5 (`movies` document schema).

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

---

## 5. Findings & Evidence

Measured on **2026-11-16** on the Windows laptop with throwaway scripts in [`spikes/16-recommendation/`](../../spikes/16-recommendation/):
- **Committed evidence:** `*_report.json`, `pool_b_profiles.jsonl`, `rank_details.json`, and the ID snapshot `catalog_ids_2026-11-16.json.gz`.
- **Gitignored** (`data/`): the raw TMDB, IMDb and Wikidata files.
- **Raw TMDB reviews are never written to disk**, only counted.
- **Paid LLM spend: ≈ $0.13**, all `gpt-6-luna` except the 50 reference labels from `gpt-6.1-terra` ($1.00 / $5.00 per 1M tokens, re-fetched from [OpenAI pricing](https://developers.openai.com/api/docs/pricing) 2026-11-16; ≈ $0.07 of the total).
  - This deviates from PROGRESS.md's "`gpt-6-luna` only", for a reference model the A/B needed.

  | Step | Spend |
  |---|---|
  | Enrichment of 400 profiles | $0.122 |
  | Ranking intents + judge | $0.006 |
  | Field-match test | $0.001 |
  | Smoke test | $0.003 |

- **TMDB, Wikidata and IMDb downloads cost $0.** The source downloads are scripted in [fetch_sources.py](../../spikes/16-recommendation/fetch_sources.py), and the review follow-ups in [followups.py](../../spikes/16-recommendation/followups.py) → [followups_report.json](../../spikes/16-recommendation/followups_report.json).

### Q1. Corpus selection, the 1984 problem, retention

- **Finding: use gate G7, giving ≈ 14.5k movies.** It's TMDB-only (no IMDb) and gives a balanced era mix with no notorious filler. G7 means:
  - age-aware minimum TMDB votes: 20 if ≤ 1 year old, 60 if ≤ 3, 120 if ≤ 10, otherwise 200;
  - TMDB Bayesian quality score `WR ≥ 5.0` for every movie;
  - `WR ≥ 6.3` for films more than 25 years old.
- **Catalogue measured** by [catalog.py](../../spikes/16-recommendation/catalog.py), result in [catalog_stats.json](../../spikes/16-recommendation/catalog_stats.json):
  - **51,527** unique movies on flat-rate in ES/US/BO with `vote_count ≥ 10`: ES 26,110, US 42,062, BO 15,432.
  - 51,414 of them have a poster and an overview.
  - The crawl took 4,290 `/discover/movie` calls, all HTTP 200, in 256 s.
  - `/discover` caps `total_results` at 20,001, so the crawl is sliced by release window; no slice hit the 10k page cap.
- **Bayesian quality score:** `WR = v/(v+m)·R + m/(v+m)·C`, with TMDB `C = 6.08` (catalogue mean) and `m = 50` (median votes).
- **Gate results** ([corpus_report.json](../../spikes/16-recommendation/corpus_report.json)):

  | Gate | Kept | Pre-2000 share | Last 3 years | Weakest old film kept |
  |---|---|---|---|---|
  | none (votes ≥ 10) | 51,414 | 31.3% | 6,135 | *"MANOS" The Hands of Fate* (2.2) |
  | flat votes ≥ 200 | 12,421 | 27.0% | **1,165** (recent films starved) | *"MANOS"* (2.2), *Troll 2* (3.9) |
  | age-aware votes only | 12,554 | 12.8% | 3,219 | *Jaws: The Revenge* (4.1), *Batman & Robin* (4.4/5,653 votes) |
  | age-aware IMDb votes | 10,677 | 16.7% | 2,599 | *"MANOS"* (no quality bar) |
  | **G7** (recommended) | **14,478** | **17.4%** | **3,203** | *The Greatest Show on Earth* (6.34) |

  - **G7 by country:** ES 9,952, US 11,961, BO 6,835.
  - **G7 by decade:** pre-1970 797, 1970s 371, 1980s 565, 1990s 793, 2000s 2,156, 2010s 4,797, 2020s 4,999.
  - **What G7 drops:** poorly rated recent films (*The Anacondas* 2025, 3.6; *War of the Worlds* 2025, 4.0 with 1,208 votes) and low-vote non-English classics (see Q2, IMDb).
- **Retention: keep enriched movies when they leave streaming, with a size-based eviction rule; don't buffer theatrical releases for now.**
  - **Storage, from feat-009** (27.6% of M0 for 20k docs at 384-d with HNSW, ≈ 7.2 KiB per doc): G7 is ≈ 102 MiB, **20% of M0**.
  - **Churn rate, not yet measured for this catalogue.** feat-008 measured 0.6–2.6% of the Popular 500 *changing providers* per day (ES 2.2%, US 2.6%, BO 0.6%). That's an upper bound: most changes are provider swaps, not a movie leaving every launch country.
  - **Assumed scenario:** if 20% of the corpus left all launch countries each year, keeping those docs adds ≈ 20.5 MiB a year (4% of M0), so about 205 MiB over 10 years, and **no LLM cost**. Re-enriching a returning title would cost $0.00007 in Batch.
  - **Eviction rule (proposal):** delete `streamable: []` docs that have been unstreamable for more than 12 months, oldest first, whenever the collection passes 60% of M0. Keeping them is cheap but not unbounded.
  - **Refresh cost of retained docs:** zero per-doc calls, if the daily refresh starts from the `/discover` crawl (4,290 calls, ≈ 4 min). A stored movie missing from every region's flat-rate list gets `streamable: []` without a call, and per-movie `/watch/providers` calls are needed only for movies that are listed. This proposal still has to be confirmed in feat-017 or the ingest slice.
  - **Admission over time (proposal):** the daily crawl admits any crawled film that passes G7 and isn't stored yet. That's how recent films already on flat-rate get in once they cross the vote or WR bar.
    - The gate applies at admission only: a stored film whose refreshed `quality_score` later drops below G7 stays.
  - **A 1,000-film theatrical buffer** would cost 7.1 MiB and $0.07, but it only pays off with the rent/buy feature (product §8), so it's deferred.
  - **The real churn rate** is a new `todo` chore, **feat-017**: re-run `catalog.py` 24 h or more after 2026-11-16 and run [churn.py](../../spikes/16-recommendation/churn.py) against the committed snapshot. It sets the eviction threshold.
- **Enrichment cost of G7 with the v1 profile prompt:** 754 input and 134 output tokens per movie, so **≈ $1.03 once via Batch** ($2.06 standard). feat-011 estimated $1.10 for 20k with a shorter prompt.

### Q2. External data: IMDb, critics and awards, transient reviews

- **IMDb: measured, and recommended against.**
  - **Join:** the Wikidata `P4947 → P345` mapping (285,796 pairs, CC0, one 14.5 s SPARQL query, no per-movie TMDB calls) gives **90.7%** of usable movies an IMDb rating. 2020s films are lower at 81%, because Wikidata lags.
  - **IMDb mostly duplicates TMDB:**
    - IMDb has a median of **39× more votes** per movie.
    - Rating Spearman 0.81 overall, 0.78 when TMDB has fewer than 100 votes, 0.90 at 1,000 or more.
    - WR Spearman 0.83; the top-10% sets overlap 70%.
  - **What it would add to G7:** only **291 movies (2%)**, using the rule "excluded by G7, at least 10k IMDb votes and IMDb WR ≥ 7.0".
    - By language: English is the largest single group (87). Indian languages together are larger: Hindi 80, Tamil 42, Telugu 32, Malayalam 15 (e.g. *Dil Bechara*, *777 Charlie*).
    - 87 of the 291 are from before 2000.
  - **Licence** ([IMDb help](https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX), checked 2026-11-16):
    - *"The data can only be used for personal and non-commercial use"* and *"must not be altered/republished/resold/repurposed to create any kind of online/offline database of movie information"* (except individual personal use).
    - Attribution would be *"Information courtesy of IMDb (https://www.imdb.com). Used with permission."*
  - Storing IMDb ratings in our public corpus conflicts with the "database" clause, and the quality gain is ≈ 2%.
  - **Recommendation: drop IMDb.** It's for the owner to confirm (§6), and it isn't recorded in architecture §7 yet.
  - The committed reports contain no IMDb values; the IMDb file stays in the gitignored `data/` folder.
- **Critics and awards from Wikidata (CC0): a distinct signal, worth an internal `critic_score`.** Measured by [critics.py](../../spikes/16-recommendation/critics.py), result in [critics_report.json](../../spikes/16-recommendation/critics_report.json).
  - **Coverage on G7** (every G7 film with a Wikidata IMDb ID queried):
    - Rotten Tomatoes % 68.7%, Metacritic 47.5%, either one **69.8%**;
    - by era: pre-2000 92%, 2000–2019 83%, **2020+ only 40.4%**;
    - awards received 15.5%.
    - The first run had skipped films with fewer than 50 votes. The script now queries from 20 votes, which moved the totals by about 0.1 points.
  - **It's distinct from TMDB:** Spearman with TMDB WR is **0.58–0.59** for the two critics scores (Metacritic 0.58, RT 0.59), against 0.84 for IMDb. That's the separation `acclaim_preference` needs:
    - critics' darlings with lukewarm audiences (66): *It Follows*, *EO*, *The Babadook*, *The Green Knight*;
    - crowd-pleasers critics rated low (54; Metacritic ≤ 45 and TMDB WR in the top 20%): *The Super Mario Galaxy Movie*, *The Tomorrow War*, *Meet Joe Black*.
  - **Recommendation:**
    - Store `critic_score` (0–100: Metacritic, else Rotten Tomatoes %) and `awards_count`, refreshed rarely.
    - Use them internally for ranking only. Don't display the RT or Metacritic brand names; that's a trademark caution, my judgement, not legal advice.
    - When missing, as for most 2020+ films, fall back to TMDB WR.
  - **Q2's question on licensing terms for "Wikidata/OMDb if used":** Wikidata structured data is CC0. OMDb wasn't needed.
- **Transient TMDB reviews: no improvement, at +35% tokens. Recommend against.** Measured by [ab_eval.py](../../spikes/16-recommendation/ab_eval.py), result in [ab_report.json](../../spikes/16-recommendation/ab_report.json).
  - **Setup:** 50 well-known films, each with at least 2 English reviews. `gpt-6-luna` profiled them from TMDB data only, and again with up to 3 review excerpts of ≤ 500 chars. Both were compared with a reference from `gpt-6.1-terra` (TMDB data plus its own film knowledge).

    | Agreement with reference | Base (TMDB only) | + reviews |
    |---|---|---|
    | pacing / viewing_effort | 0.96 / 0.82 | 0.94 / 0.82 |
    | ending_feel / humor_style | **0.74** / 0.74 | 0.68 / 0.78 |
    | intensity exact / within 1 | **0.86** / 1.00 | 0.74 / 1.00 |
    | tone / content_warnings (Jaccard) | 0.76 / 0.73 | 0.74 / 0.71 |
    | input tokens per movie | 770 | 1,039 |

  - **Where reviews changed `ending_feel`** (12 films), base matched the reference 7 times and the reviews version 4 times.
  - **Caveats; "no reviews" is provisional:**
    - **The reference is biased towards the base variant by construction.** It saw the same input as base (TMDB data without reviews), plus its own film knowledge.
    - It's a stronger model, not ground truth.
    - These are well-known films, where model knowledge is strongest.
    - The +35% token cost and the TMDB-terms risk stand regardless.
    - Re-check with the owner-rated sample planned for the profile feature (architecture §4).

### Q3. Mirror schema v1 (`QueryIntent` ↔ `movies` / `movies.profile`)

- **Finding: the v1 schema below worked end to end.**
  - **400/400 profiles** were schema-valid with 0 errors.
  - **12/12 intents** were schema-valid, and their filters match each request on inspection (there was no formal expected list):
    - "kids 7 and 10" → `audience=kids` + `max_intensity=2`;
    - "Korean thriller" → `original_languages=["ko"]`;
    - "90s neo-noir" → 1990–1999 + `classic_or_any_era`;
    - "I don't mind subtitles" → *no* language filter;
    - "hidden gem" → `acclaim_preference=hidden_gem`;
    - the Spanish request → an English intent.
  - Code: [schemas_v1.py](../../spikes/16-recommendation/schemas_v1.py), [rank_details.json](../../spikes/16-recommendation/rank_details.json).
- **Proposed v1 schema:**

  | Channel | `QueryIntent` (step 2) | Mirrored movie field | Applied |
  |---|---|---|---|
  | 1. Hard pre-filters | `max_runtime_minutes`, `max_intensity` (1–5), `avoid` (12 content warnings), `year_min`/`year_max`, `audience` (kids/teens), `original_languages` | `runtime`, `profile.intensity`, `profile.content_warnings`, `year`, **`certification_us`** (kids = G/PG, teens ≤ PG-13, from TMDB `release_dates`), **`original_language`** | `$vectorSearch.filter`, re-checked in step 4 (P3) |
  | 2. Semantic | `tone`, `pacing`, `viewing_effort`, `ending_feel`, `humor_style`, `themes`, `semantic_description` | `profile.tone`, `profile.pacing`, `profile.viewing_effort`, `profile.ending_feel`, `profile.humor_style`, `profile.themes`, `profile.summary` | Movies embed the template `Tone: … \| Pacing: … \| … \| Summary: …`. Queries embed only `semantic_description`; the other intent fields go to step 5 as context (see below) |
  | 3. Ranking controls | `specificity`, `era_mode`, `acclaim_preference` | `quality_score` (TMDB WR), `critic_score`, `popularity`, `year`, `collection_id` | Step 4 hybrid score (Q4) |

  - **Other movie fields:** `title`, `original_title`, `genres`, `keywords` (drop `*stinger`), `directors`, `cast[:5]`, `tagline`, `overview`, `poster_path`, `tmdb_vote_average`, `tmdb_vote_count`, `awards_count`, `streamable`, `availability_updated_at`, `embedding`, `embedding_model`, `prompt_version`, `source_hash`, `updated_at`.
  - **Not stored:** reviews and IMDb data (Q2).
  - **Closed vocabularies, v1** (as tested in [schemas_v1.py](../../spikes/16-recommendation/schemas_v1.py)):
    - `tone` (1–3): light, funny, heartwarming, romantic, uplifting, cozy, whimsical, thoughtful, melancholic, dark, gritty, tense, scary, exciting, epic, weird, satirical.
    - `pacing`: slow, medium, fast.
    - `intensity`: 1–5.
    - `viewing_effort`: comfort_background, easy, engaging, demanding.
    - `ending_feel`: uplifting, warm_resolved, bittersweet, tense_cathartic, bleak_or_ambiguous.
    - `humor_style`: none, witty_dry, warm_gentle, absurd_satirical, broad_slapstick, dark_humor.
    - `content_warnings`: violence, gore, sexual_content, nudity, strong_language, drug_use, self_harm, animal_harm, child_harm, sexual_violence, horror_scares, flashing_lights.
    - Free text: `themes` (1–5 short phrases) and `summary` (≤ 400 chars, how it feels to watch, no spoilers).
    - Intent only: `specificity` broad / medium / specific; `era_mode` modern_default / classic_or_any_era; `acclaim_preference` crowd_pleaser / critically_acclaimed / hidden_gem / any; `audience` kids / teens / null.
  - **What the channel-2 intent fields are for in v1:**
    - Queries embed `semantic_description` only, and direct field matching didn't help (below). So `tone`, `pacing`, `viewing_effort`, `ending_feel`, `humor_style` and `themes` are **passed to step 5** with the candidates' profile fields, as context for picking and pitching.
    - They stay in the schema for the golden-set revisit of field matching.
    - So the draft's `preferred_viewing_effort` and `preferred_ending_feel` are **not step-4 controls in v1**: the one field-match test lowered relevance.
  - **Value distribution of the 300 base profiles** ([followups_report.json](../../spikes/16-recommendation/followups_report.json)) is input for the profile feature:
    - `viewing_effort` is almost binary: engaging 152, easy 140, demanding 7, comfort_background 1.
    - `cozy` was used once; `intensity` sits mostly at 3–4 (212 of 300).
    - The enrichment prompt needs anchored definitions (examples per value) before those fields can carry weight.
  - **Age certification coverage, a spec gap (P3/P7, owner decision):**
    - Only **63%** of Pool B films have a usable US certification (not empty, not `NR`). That's 29 of the 101 non-English films. ES certification covers 33%; either covers 70%; 30% have neither.
    - So an `audience=kids` hard filter on `certification_us` keeps 55/300 films and silently drops uncertified ones.
    - Fallbacks: US, else ES (`A`, `Ai`, `7`, `7i` from TMDB's ES list) keeps 56/300; adding "else profile `intensity ≤ 2` and no adult warnings" keeps 68/300.
    - **Proposal:** store `certification_us` and `certification_es` as the first non-empty, non-`NR` certification in that country's `release_dates` (as `followups.py` does; `enrich.py` kept `NR`). Then apply, for `audience`:
      - `kids`: US G/PG, else ES `A`/`Ai`/`7`/`7i`, else profile `intensity ≤ 2` and none of the adult warnings.
        - The tested set of adult warnings was violence, gore, sexual_content, nudity, sexual_violence, horror_scares, drug_use, strong_language (68/300 kept).
        - It should also include self_harm, child_harm and animal_harm (untested; the count can only go down).
      - `teens` (untested): US ≤ PG-13, else ES up to `12`, else profile `intensity ≤ 3` and none of sexual_content, nudity, sexual_violence, gore.
      - The owner decides whether the profile fallback is acceptable under P3.
  - **Untested:** embedding `profile.summary` alone on the movie side, against the full template.
- **Embedding format,** blind LLM judge, relevance 0–2 at top-5 over 12 queries on the 300 enriched movies:

  | Movie vectors | Query vector | Relevance @5 |
  |---|---|---|
  | **template(profile)** | `semantic_description` | **1.30** |
  | template(profile) | raw user text | 1.30 |
  | template(profile) | template(intent) | 1.26 |
  | TMDB text (title, genres, overview) | `semantic_description` | 1.12 |

  - **The profile is the lever:** +0.14–0.18 over TMDB text. That's the largest gap measured, but still only about 8–10 points out of 57 judged items.
  - **The symmetric template on the query side shows no gain:** 1.26 vs 1.30 is 2 points out of 57, within judge noise. Use `semantic_description`: it's already English for non-English input, and simpler.
  - **Judge noise:** the same 57 (query, movie) pairs were judged twice, in `rank_details.json` `rel_B_description` and `match_report.json` `embedding`. The two runs **disagreed on 15 of 57 items (26%)**, even though the means differ only by 0.02 because the flips cancel. Differences under about 0.1 are not evidence.
- **Matching fields directly (not supported):** boosting candidates whose profile fields equal the intent's (0.6 cosine + 0.4 field match) **lowered** relevance from 1.32 to 1.23 ([match_report.json](../../spikes/16-recommendation/match_report.json)).
  - It fixed "exhausted, light and easy" (a 0-rated pick replaced by a 2) but displaced better semantic matches elsewhere.
  - Revisit it with the golden query set, not 12 queries.

### Q4. Hybrid ranking and retrieval depth

- **Finding:**
  - **Retrieve K = 150**, then re-score deterministically in step 4, dedupe franchises by `collection_id`, and pass the top 25 to step 5.
  - **The hybrid's effect on relevance is directional only, within judge noise.**
    - It scored 77 vs 73 points over 60 judged items. 8 of 12 queries tied, one got worse (neo-noir, 8 → 7), and the "critically acclaimed" query alone gave +3 of the net +4.
    - Its clearer effect is on quality: the mean WR of the top 5 went from 6.61 to 6.89.
  - **The corpus gate (Q1) does most of the work on the 1984 problem**, and the movie profile (Q3) matters more than the ranking formula.
  - **One failure mode of the formula** is below ("exhausted").
- **Formula tested** in [rank_eval.py](../../spikes/16-recommendation/rank_eval.py):

  `score = w_sem·sim + w_qual·qual + w_era·era + w_pop·pop`, where:
  - `sim` = cosine, min-max normalised over the K candidates;
  - `qual = clip((WR − 5)/3)`, blended 50/50 with `critic_score` when `acclaim_preference = critically_acclaimed`;
  - `pop = log1p(popularity)/max`, inverted for `hidden_gem`;
  - `era = 1` unless `modern_default` and the film is more than 20 years old, in which case `0.6 + 0.4·qual`, so good classics keep their weight;
  - weights by `specificity`: broad (.45/.30/.10/.15), medium (.60/.20/.10/.10), specific (.80/.10/.05/.05), with +0.10 on `pop` for `crowd_pleaser`.
- **Pool A results:** all 14,478 G7 movies, embedded from TMDB text in 17.2 min at 14.1 docs/s on this laptop; same 12 queries and blind judge.

  This table was measured at **K = 100**; the recommendation is K = 150 (depth table below). Only the **top 5** was judged, not the top-25 pool that step 5 receives. Only one hand-set formula was tried.

  | Measure, top-5 | Pure vector | Hybrid (K = 100) |
  |---|---|---|
  | Judged relevance (0–2) | 1.22 | **1.28** |
  | Mean TMDB WR | 6.61 | **6.89** |
  | Mean TMDB votes | 1,970 | 2,318 |
  | Pre-2000 films with WR < 6.8 when no era was asked | 1 | 1 |

- **Retrieval depth:** recall of the hybrid top 25 computed within K, against within K = 300 ([depth_report.json](../../spikes/16-recommendation/depth_report.json)):

  | Specificity | K = 50 | K = 100 | K = 150 | Deepest vector rank needed |
  |---|---|---|---|---|
  | broad (4) | 0.85 | 0.91 | **0.94** | 50–114 |
  | medium (5) | 0.91 | 0.94 | 0.94 | 36–74 |
  | specific (3) | 0.96 | 0.96 | 0.96 | 28–38 |

  - Broad queries pull good, popular films from deep in the vector ranking, so K = 150 covers every rank observed.
  - Recall stays below 1 even when the needed rank is inside K, because `sim` is min-max normalised over the candidates (design note below).
  - These numbers include the critic blend for the "critically acclaimed" query. The first version of `depth_by_query.py` omitted it; with it, that query's deepest rank fell from 82 to 50.
  - feat-009 measured `$vectorSearch` latency at smaller K, so the latency of K = 150 is measured in the slice.
- **Side by side,** from [rank_details.json](../../spikes/16-recommendation/rank_details.json):
  - **"Tense submarine or single-location thriller":** both methods return *Below*, *The Abyss*, *Open Water* (judged 2/2/1).
  - **"Exhausted, something light and easy": the hybrid made this query worse in rank order** (the top pick went from one judged 2 to one judged 0), though it tied on points (3 vs 3).
    - Pure vector already had *A Brighter Summer Day* (1991, a nearly 4-hour drama, judged 0) at rank 2, because TMDB text matched words, not mood.
    - The hybrid moved it to rank 1 and added *High and Low* (1963, judged 0).
    - Cause: for highly rated old films, `era = 0.6 + 0.4·qual` comes out at about 1, and broad queries put 0.30 on quality. So the formula **pushes demanding acclaimed classics into "easy" requests**.
    - Fix direction: broad "easy" intents need an effort or runtime signal, and profile embeddings, which Pool A lacks. Field matching on `viewing_effort` improved this query on **Pool B** (5 → 7 points), but it wasn't re-run on Pool A.
  - **The kids query:** Pool A has no certification, so it lets *Old Dogs* (judged 0) through. On Pool B, the mirror filters (`certification_us` G/PG plus the intent's `max_intensity=2`) left 30 eligible films; G/PG alone keeps 54–55, depending on whether `NR` counts.
- **Design notes for feat-012:**
  - Normalise `sim` on a fixed scale, not min-max over K. Min-max made scores depend on K: recall moved even when the needed rank was inside K.
  - **Franchise duplicates are rare in practice.** Measured by fetching `belongs_to_collection` for all 309 movies in the 12 queries' top-25 lists (`followups_report.json`, M1). 48 of the 309 belong to a collection.
    - Pure vector top-25s had **1 duplicate slot** in total (1 query); hybrid top-25s and every top 5 had **none**.
    - Dedupe by `collection_id` is cheap insurance, not a measured quality gain. (The spike's `dedupe_collections` was never called in the ranking run.)
- **Caveats:**
  - 12 queries is a small sample.
  - The judge is `gpt-6-luna` judging blind but within the same model family.
  - Weights are hand-set, not tuned. Tune them against the 30–50 owner-labelled golden queries (architecture §6).

## 6. Summary for `feat-012` (owner review)

1. **Corpus (Q1):**
   - Admit with gate **G7** (≈ 14.5k movies, 20% of M0).
   - Keep enriched movies that leave streaming (`streamable: []`), evicting those unstreamable for over 12 months once the collection passes 60% of M0.
   - No theatrical buffer until the rent/buy feature.
   - Measure real churn in **feat-017**.
2. **Signals (Q2):**
   - `quality_score` from TMDB WR.
   - `critic_score` and `awards_count` from Wikidata (CC0), internal only.
   - **No IMDb** (licence; +2% coverage) and **no reviews** in enrichment (no measured gain, +35% tokens, provisional).
3. **Schema (Q3):** the v1 mirror schema and vocabularies above.
   - Additions over the draft: `certification_us` and `certification_es` ↔ `audience`, `original_language` ↔ `original_languages`, `critic_score`.
   - The channel-2 intent fields go to step 5 as context; there are no `preferred_*` step-4 controls in v1.
   - The profile feature must anchor the `viewing_effort` and `tone` definitions.
4. **Embedding (Q3):** movies embed `template(profile)`; queries embed `semantic_description`.
5. **Ranking (Q4):**
   - K = 150, then the hybrid formula above with a fixed-scale `sim`, then `collection_id` dedupe, then the top 25 to step 5.
   - Fix the "easy request → demanding classic" failure before relying on the quality weight for broad queries.
   - Tune the weights on the owner-labelled golden set in the eval feature.
6. **Cost:** one-time enrichment of G7 ≈ **$1.03** via Batch (`gpt-6-luna`), within the approved spend (Q6).

**Changes to `docs/architecture.md`** (for feat-012 to apply):

| Section | Change | From |
|---|---|---|
| §3 step 2 | Intent = `QueryIntent` v1 with its 3 channels | Q3 |
| §3 step 3 | `$vectorSearch` returns **K = 150** (was "top 30–50"); the pre-filter adds `year`, `original_language`, and the certification or profile fallback for `audience` | Q3, Q4 |
| §3 step 4 | Re-check the new filters as well (`year`, `original_language`, `audience`; P3); add the deterministic hybrid re-score and `collection_id` dedupe; pass the top 25 to step 5 | Q3, Q4 |
| §3 step 5 | The re-rank prompt also gets the intent's channel-2 fields and each candidate's profile fields | Q3 |
| §3 step 6 | The *Results without pitches* fallback orders by hybrid score (was "search score") | Q4 |
| §4 | Corpus gate G7, applied at admission by the daily crawl; keep-on-churn plus eviction; enrichment inputs are TMDB only (no reviews); **the daily `/discover` crawl also refreshes `popularity`, `vote_average`, `vote_count` and `quality_score`**. These are no longer "ingested once", and the crawl returns them at no extra cost | Q1, Q2 |
| §5 | Drop `review_snippets`. Profile per v1. Add filter-indexed `year`, `original_language`, `certification_us`, `certification_es`, plus `collection_id`, `quality_score`, `critic_score`, `awards_count`, the TMDB vote and popularity fields, and `unstreamable_since` (set when `streamable` becomes empty, cleared when it refills; needed by the eviction rule) | Q1, Q2, Q3 |
| §1, §5 | `profile.evidence` ("with the evidence it used", §1 Enrich) **was not tested** in this spike. The profile feature decides whether to keep it | — |
| §7 | New decisions for the owner (below) | — |

**Owner decisions needed:**
- (a) drop IMDb;
- (b) drop reviews from enrichment;
- (c) the `audience` fallback when a film has no certification (profile-based, under P3);
- (d) the retention eviction threshold, after feat-017.
