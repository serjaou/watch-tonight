# Metrics

**What this file is:** the product, system, eval and process metrics for `watch-tonight` — where each number comes from, what its target is, and the per-feature `/handoff` index (`feat-006`, `feat-015`).
**Related docs:** [docs/product.md](product.md) (rules P1–P7, response states, MVP DoD), [docs/architecture.md](architecture.md) (query `trace`, `ingestion_runs`, `eval_runs`, open questions Q1–Q13), [docs/harness-log.md](harness-log.md) (agent/harness failures).

---

## 1. Product, System & Eval Metrics

### 1.1 Online query metrics
Raw data comes from the per-response `trace` returned by `SearchMovies` ([docs/architecture.md](architecture.md) §3 step 7 and §6).

| Metric | Source in `trace` | Target / Budget | Notes |
|---|---|---|---|
| **End-to-end latency (`p50` / `p95`, ms)** | Sum of `trace.timings_ms` (feat-018); measured end to end with the real LLM in feat-029 | Initial guess `p95 < 10,000 ms` ([docs/product.md](product.md) §6); confirmed after spikes and measured in the first end-to-end slice (`Q7`) | Includes validation, LLM intent, query embedding, Atlas `$vectorSearch`, deterministic filter check, and LLM re-rank + pitch |
| **Stage latency (`p50` / `p95`, ms)** | `trace.timings_ms.{understand,embed,retrieve,check,pick_and_pitch}` (feat-018) | Component baselines measured in `feat-009` Q5 (`retrieve`), `feat-010` Q2 (`embed`), `feat-011` Q4 (`understand`, `rerank_and_pitch`) | Pinpoints bottlenecks and decides whether the 2 LLM calls stay separate |
| **Response state distribution (`%`)** | `response.state` | Track share of `Success`, `Partial`, `Results without pitches`, `Invalid input`, and `Service unavailable` ([docs/product.md](product.md) §4) | Distinguishes thin catalogue coverage (`Partial`) from step-6 LLM failures (`Results without pitches`, `Q8`) and step-2/infra failures (`Service unavailable`) |
| **LLM retry rate** | Not in the trace yet: the retry lives in the LLM adapter (feat-029), which decides how it is reported | Baseline measured in `feat-011` Q3 | Counts how often structured output or deterministic validation (step 2 or step 6) triggers a retry |
| **Tokens & estimated cost per query (`USD`)** | `trace.tokens.{input,output}`, `trace.cost_usd` (feat-018; a rejected step-5 answer still counts) | **$0 by default** ([docs/product.md](product.md) §1); any paid service or recurring cost requires owner approval | Sum of both online LLM calls + query embedding; reported in README ([docs/product.md](product.md) §7) |

### 1.2 Offline pipeline metrics
Raw data comes from the `ingestion_runs` collection in MongoDB ([docs/architecture.md](architecture.md) §4–§5).

| Metric | Source | Target / Budget | Notes |
|---|---|---|---|
| **Job counts & duration (`ingest`, `refresh`, `enrich`, `embed`)** | `ingestion_runs.{job,processed,skipped,failed,duration_s}` | Bounded by TMDB rate limits (`feat-008` Q3), laptop/host CPU (`feat-010` Q4), and LLM rate limits (`feat-011` Q1) | `skipped` verifies idempotency (`source_hash`, `prompt_version`, `embedding_model`) |
| **Enrichment cost per 1,000 profiles (`USD` & tokens)** | `ingestion_runs` (`enrich` job) | Measured in `feat-011` Q1; must fit zero-cost / owner-approved small spend for 5–20k movies | Recorded before running full-corpus enrichment |
| **Catalogue coverage & poster completeness** | `movies` collection / `feat-008` Q5–Q6 | ES, US and BO flat-rate movie counts per provider; `%` with English overview, keywords, reviews, and `poster_path` | Answers whether BO launches (`Q2`) and how to handle missing posters (`Q13`) |
| **Availability freshness & daily churn** | `movies.availability_updated_at`, `ingestion_runs` / `feat-017` | Refreshed daily ([docs/product.md](product.md) §6); every result shows its `availability_updated_at` (P6) | Baseline from `feat-017` (two complete crawls 5.3 days apart): G7 films leave all launch countries ≈ 6/day and are admitted ≈ 24.5/day; the whole ≥ 10-vote crawl ≈ 34.5 left and ≈ 101.7 arrived per day ([spike 16 Q1](spikes/16-recommendation-signals-and-ranking.md#q1-corpus-selection-the-1984-problem-retention)). Replaces the one-day estimate of `feat-008` Q7 (`Q12`) |

### 1.3 Eval & quality metrics
Raw data comes from `evals/` (protected by the `tests-approved` PR gate) and `eval_runs` ([docs/product.md](product.md) §3 & §7, [docs/architecture.md](architecture.md) §6).

| Eval suite | What it checks | Gate / Target | When it runs |
|---|---|---|---|
| **Deterministic product-rule evals** | P1 (streamable flat-rate in country/provider), P3 on constraints as applied (runtime, max intensity, avoid), P4 (prompt ≤ 500 chars), P2 pitch length (≤ 350 chars), real catalogue IDs (no invented movies), valid output schema | **100% pass in CI** ([docs/product.md](product.md) §7) | Every CI run once the end-to-end slice exists |
| **Constraint extraction eval (P3)** | How accurately step 2 extracts structured filters over the closed vocabulary (`Q11`) from free text, including non-English prompts (`Q9`), on golden queries | Recorded baseline; tracked on prompt/model changes | Offline eval (`evals/`) |
| **Retrieval `precision@5`** | Relevance of top candidates on 30–50 owner-labelled mood queries | Recorded baseline; tracked on profile/embedding changes | Offline eval (`evals/`) |
| **Pitch quality eval (P2, ADR 0001)** | LLM-as-judge calibrated against owner labels: facts grounded in movie data, about the movie never the user, no spoilers, ≤ 350 chars | Recorded baseline; tracked on prompt/model changes | Offline eval (`evals/`) |
| **Emotional profile quality** | Owner-rated sample of enriched movie profiles ([docs/architecture.md](architecture.md) §4) | Checked in the profile design feature (`feat-012`) before enriching the full corpus | Offline sample review |

### 1.4 Spike baselines (`feat-008`…`011`)
Each spike records its full measurements in `docs/spikes/NN-slug.md` and updates the summary row below at `/handoff`, so `feat-012` (architecture refinement) and the README have all numbers in one place.

| Spike | Key metrics to record | Measured value |
|---|---|---|
| `feat-008` (TMDB & providers) | Rate limit (req/s), time to ingest 20k movies, flat-rate movie count per provider in ES / US / BO, `%` missing `poster_path`, daily provider churn | Soft limit ~40–50 req/s; measured **25.2 req/s** (`10` workers, `p50=176.6 ms`, `p95=1,073.1 ms`, `0` `429`s); **~14 min** to ingest 20k movies via `append_to_response`; Popular 500 flat-rate coverage: **ES 67.0%** (`335/500`; Prime `8,715`, Netflix `6,744`, Movistar+ `6,215`, Disney+ `2,510`, Filmin `11,820`), **US 73.2%** (`366/500`; Netflix `4,805`, HBO Max `2,060`, Disney+ `1,731`, Hulu `1,348`, Peacock `1,216`, Paramount+ `1,198`), **BO 62.4%** (`312/500`; Prime `6,872`, Netflix `4,894`, Disney+ `2,265`, HBO Max `2,087` — **BO usable**); **`0.0%` missing `poster_path`** (`0/500` popular, `0/480` deep pages `1..500`); **24.5h provider churn (Popular 500):** ES `11/500` (`2.2%`, `+9/-6` pairs), US `13/500` (`2.6%`, `+14/-10` pairs), BO `3/500` (`0.6%`, `+3/-0` pairs); brand-new flat-rate releases: `1–3/day` per country ([08-tmdb-and-providers.md](spikes/08-tmdb-and-providers.md)) |
| `feat-009` (Atlas vector search) | Free-tier storage for 20k docs (384-d vs 768/1024-d), pre-filter support (`streamable` + `runtime` + `_id` + `intensity` + `content_warnings`), `$vectorSearch` `p50` / `p95` ms, index ready time in `atlas-local` | **20k docs on M0 (512 MiB limit):** 384-d = `120.85 MiB` logical (`108.76 MiB` disk, `~27.6%` w/ HNSW; `~17.4%` with `FLOAT32` binary vectors), 768-d = `216.05 MiB` logical (`~54.2%` w/ HNSW; `~28.9%` binary), 1024-d = `279.72 MiB` logical (`~70.5%` w/ HNSW; `~36.5%` binary). **Pre-filters:** all 5 combine in 1 `$vectorSearch` (`40/40` valid, `0` violations; `_id` `$nin` verified up to `5,000` IDs; bit-for-bit identical on M0 and `atlas-local`). **Latency (M0, 20k docs):** `p50 = 60.5 ms`, `p95 = 120.8 ms` (`atlas-local` Mac ARM: `p50 = 15.35 ms`, `p95 = 20.98 ms`). **Index ready time:** `atlas-local` = **`4.64 s`** (50-doc fixture) / **`9.23 s`** (20k docs); M0 = `50.83 s` (20k docs) ([09-atlas-vector-search.md](spikes/09-atlas-vector-search.md)) |
| `feat-010` (Embedding runtime) | Candidate models & dimensions, image size (MB), RAM (MB), cold start (s), query `p50` / `p95` ms, time to embed 20k profiles on CPU, viable free host tier | **Chosen:** **`BAAI/bge-small-en-v1.5` (`384-d`) via `fastembed` (ONNX CPU)** — added image **`+212.2 MB`** (`148.2 MB` packages + `64.1 MB` weights; vs **`+988.4 MB`** PyTorch `sentence-transformers`), query-time RSS **`279.1 MB`** (vs **`509.4 MB`** PyTorch and **`546.7 MB`** `paraphrase-multilingual-MiniLM-L12-v2`), cold start **`0.58 s`** (`0.41 s` import + `0.17 s` load; vs `4.15 s` PyTorch), single-query latency **`p50 = 5.04 ms` / `p95 = 5.88 ms`** (vs `10.38 ms` / `11.58 ms` PyTorch; `0.999999` cosine parity, `4.9/5` top-5 overlap), **20k CPU batch = `11.77 min`** (`706 s`, `28.33 docs/s`; `$0` cost). **Free host tiers:** **Cloud Run** & **Azure Container Apps** (`180k vCPU-s`, `360k GiB-s`, free cron jobs) or **Render Free** (`512 MB`) + GitHub Actions cron ([10-embedding-runtime.md](spikes/10-embedding-runtime.md)) |
| `feat-011` (Runtime LLM) | Provider & model comparison (Gemini free tier vs low-cost OpenAI), rate limits (RPM/TPM/RPD), tokens & USD per query (2 calls) and per 1,000 profiles, structured-output pass/retry rate on 10 queries (≥3 non-English), call `p50` / `p95` ms | **Recommended: `gpt-6-luna`** (`reasoning_effort=none`) — **`$0.00067`/query** (`$0.67`/1,000), **`$0.11`/1,000 profiles** (≈ `$1.10` for 20k via Batch); tokens in/out: understand `613/67`, re-rank (40 candidates) `4,191/255`, profile `580/103`; valid: understand `20/20`, re-rank `19/20`, profile `20/20`; extraction `20/20` exact (non-English `10/10`); latency understand `p50 1,635 / p95 2,659 ms`, re-rank `3,259 / 4,046 ms`, both calls `4,979 / 6,304 ms`; Build tier `5,000 RPM / 2M TPM`, no RPD listed. **`gemini-3.5-flash-lite`** (thinking `minimal`): paid `$0.0026`/query, `$0.45`/1,000 profiles; Free Tier **`15 RPM`** (429 `quotaValue`), RPD/TPM not published; **`9/68` attempts `503`**; understand `p50 957 / p95 1,503 ms`, re-rank `1,672 / 2,508 ms`. **0 schema errors in 120 responses.** Free tier can't serve EEA users (ES launch); Gemini terms bar services likely used by under-18s. Framework: Pydantic AI `2.68.0` + `NativeOutput` + `FallbackModel` ([11-runtime-llm.md](spikes/11-runtime-llm.md)) |
| `feat-016` (Recommendation signals & ranking) | Corpus admission gate counts, `%` IMDb TSV `imdb_id` join coverage, profile schema v1 (`viewing_effort`, `ending_feel`, etc.), pure vector vs hybrid ranking (`similarity + Bayesian WR + era/popularity + specificity`) across 10–12 mood queries | **Catalogue:** `51,527` flat-rate movies (≥ 10 votes) across ES/US/BO. **Gate G7** (age-aware TMDB votes, WR ≥ 5.0, WR ≥ 6.3 if > 25 y) keeps **`14,478`** (ES 9,952 / US 11,961 / BO 6,835; 17.4% pre-2000; 3,203 from the last 3 y; ≈ 102 MiB = 20% of M0; enrichment ≈ **$1.03** Batch). **IMDb join** `90.7%` via Wikidata, but it adds only `291` films (2%) and the licence bars it, so it's dropped. **Wikidata critics** coverage `69.8%` (2020+ `40.4%`), Spearman vs TMDB WR `0.58–0.59`. **Reviews A/B:** no gain, +35% tokens. **Ranking:** profile vs TMDB-text embeddings `74 vs 64` judged points; hybrid vs vector relevance@5 `1.28 vs 1.22` (directional; judge item disagreement 26%), WR@5 `6.89 vs 6.61`; **K = 150** (broad recall `0.94`, deepest rank 114) ([16-recommendation-signals-and-ranking.md](spikes/16-recommendation-signals-and-ranking.md)) |

---

## 2. Process & Harness Metrics (`/handoff` Index)

Tracks whether the harness catches issues before they reach the owner and how each task went (ADR 0004). Full outcome notes and command outputs for each finished task live in `docs/handoffs/<feat-id>.md`.
- **Rule:** when a task reaches `status: "done"` at `/handoff`, create `docs/handoffs/<feat-id>.md`, move the item from `feature_list.json` to `docs/handoffs/done_features.json`, and add a compact index row at the top of the table below (newest first). `tests/harness/test_harness.py` checks that every `done` item in `docs/handoffs/done_features.json` has both a row here and its `docs/handoffs/<feat-id>.md` detail file.
- **Columns:** **Stop-gate blocks** (times `stop_gate.py` blocked a turn), **Reviewer (rounds / findings)** (e.g. `2 (12 + 2)` or `1 (0)`), **Escaped / owner fixes** (issues found after `/handoff` or in PR review).

| ID | Type | Date | Machine · Tool | Stop-gate blocks | Reviewer (rounds / findings) | Escaped / owner fixes | Handoff Details |
|---|---|---|---|---:|---|---:|---|
| `feat-018` | `feature` | 2026-11-25 | Windows · Claude Code | 0 | 2 (13 + 3) | 0 | [feat-018.md](handoffs/feat-018.md) |
| `feat-017` | `chore` | 2026-11-21 | Windows · Claude Code | 0 | 2 (6 + 2) | 0 | [feat-017.md](handoffs/feat-017.md) |
| `feat-012` | `chore` | 2026-11-16 | Windows · Claude Code | 0 | 2 (18 + 9) | 0 | [feat-012.md](handoffs/feat-012.md) |
| `feat-016` | `spike` | 2026-11-16 | Windows · Claude Code | 0 | 2 (14 + 7) | 0 | [feat-016.md](handoffs/feat-016.md) |
| `feat-011` | `spike` | 2026-11-16 | Windows · Claude Code | 0 | 2 (9 + 6) | 0 | [feat-011.md](handoffs/feat-011.md) |
| `feat-010` | `spike` | 2026-11-15 | Mac · Antigravity | 0 | 1 (0) | 0 | [feat-010.md](handoffs/feat-010.md) |
| `feat-008` | `spike` | 2026-11-15 | Mac · Antigravity | 0 | 1 (0) | 0 | [feat-008.md](handoffs/feat-008.md) |
| `feat-009` | `spike` | 2026-11-15 | Mac · Antigravity | 0 | 1 (0) | 0 | [feat-009.md](handoffs/feat-009.md) |
| `feat-015` | `chore` | 2026-11-14 | Mac · Antigravity | 0 | 1 (0) | 0 | [feat-015.md](handoffs/feat-015.md) |
| `feat-006` | `chore` | 2026-11-13 | Mac · Antigravity | 0 | 1 (0) | 0 | [feat-006.md](handoffs/feat-006.md) |
| `feat-014` | `chore` | 2026-11-13 | Mac · Antigravity | 0 | 2 (2 + 0) | 0 | [feat-014.md](handoffs/feat-014.md) |
| `feat-013` | `chore` | 2026-11-13 | Windows · Claude Code | 0 | 2 (7 + 3) | 0 | [feat-013.md](handoffs/feat-013.md) |
| `feat-005` | `chore` | 2026-11-13 | Windows · Claude Code | 0 | 2 (12 + 2) | 0 | [feat-005.md](handoffs/feat-005.md) |
| `feat-007` | `chore` | 2026-11-12 | Mac · Antigravity | 1 *(intentional test)* | 1 (0) | 0 | [feat-007.md](handoffs/feat-007.md) |
| `feat-004` | `chore` | 2026-11-12 | Windows · Claude Code | 1 *(intentional test)* | n/a *(fixed reviewer diff)* | 1 *(piped commit slip)* | [feat-004.md](handoffs/feat-004.md) |
| `feat-000` | `feature` | 2026-11-12 | Mac · Antigravity | 0 | 1 (0) | 0 | [feat-000.md](handoffs/feat-000.md) |
| `feat-001` | `chore` | 2026-11-11 | Mac · Antigravity | 0 | n/a *(bootstrap)* | 3 *(see harness-log.md)* | [feat-001.md](handoffs/feat-001.md) |
