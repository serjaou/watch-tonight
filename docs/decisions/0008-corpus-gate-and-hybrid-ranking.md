# 0008. Corpus gate G7, TMDB-only quality signals and a hybrid re-score

- **Date:** 2026-11-16
- **Status:** Accepted (owner decisions Q15 and Q17; evidence in feat-016). The hybrid weights are provisional.
- **Context:**
  - **The catalogue:** 51,527 films are on flat-rate in ES, US and BO (≥ 10 TMDB votes). Most are low-engagement filler, the "1984 problem": pure cosine similarity can't tell a forgotten TV movie from a beloved classic.
  - **The gate (feat-016):** an age-aware gate (G7) keeps 14,478 films: 17% pre-2000 and 3,203 from the last 3 years, with no notorious filler, at ≈ 20% of M0.
  - **IMDb** adds 2% and its licence bars building a database. **Reviews** add no measured profile quality. A **Wikidata critic score** (CC0) is a distinct signal (Spearman 0.58–0.59 with audience quality).
  - **Retrieval depth:** broad queries need candidates down to vector rank 114, so K = 150.
  - **The hybrid re-score** raised the top-5 quality (mean WR 6.61 → 6.89). Its relevance gain was within judge noise, and it can push demanding classics into "easy" requests.
- **Decision:**
  1. **Admission gate G7:**
     - TMDB votes ≥ 20 / 60 / 120 / 200 for films ≤ 1 / ≤ 3 / ≤ 10 / > 10 years old;
     - Bayesian WR ≥ 5.0 (`WR = v/(v+m)·R + m/(v+m)·C`). `C` and `m` are **pinned** at `C = 6.08` (catalogue mean) and `m = 50` (median votes) from the 2026-11-16 catalogue, and recomputed only on purpose;
     - WR ≥ 6.3 when the film is more than 25 years old;
     - the admission data checks: overview, poster, `runtime > 0`, at least one genre.
     - It applies at admission only. Films that leave streaming are kept (Q17).
  2. **Signals:** `quality_score` = TMDB WR, refreshed daily. `critic_score` and `awards_count` come from Wikidata and are used internally only. No IMDb, no reviews (Q15).
  3. **Ranking:**
     - `$vectorSearch` with K = 150, then a deterministic step-4 score:
       `w_sem·sim + w_qual·qual + w_era·era + w_pop·pop`, weighted by `specificity`, with `era_mode` switching the era term and `acclaim_preference` adjusting quality and popularity, and `sim` on a fixed scale (not min-max over K);
     - then one film per `collection_id`, and the top 25 to step 5.
     - The starting weights are the ones in spike 16 §5 Q4. They were set with min-max similarity, so feat-022 sets the fixed scale and re-tunes the weights together.
     - When `critic_score` is missing (60% of 2020+ films), the critic blend falls back to TMDB WR.
- **Consequences:**
  - The weights are hand-set. The ranking and evals feature tunes them on 30–50 owner-labelled queries, and must fix the "easy request → demanding classic" failure (an effort or runtime signal) before relying on the quality weight for broad queries.
  - The daily `/discover` crawl both admits new films and refreshes the popularity and vote fields, so the ranking inputs stay current without extra calls.
  - The `numCandidates` value and the `$vectorSearch` latency at K = 150 need the full corpus on M0, so they're measured in feat-021. The skeleton's 300 films are too few.
