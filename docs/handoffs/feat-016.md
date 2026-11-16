# Handoff: `feat-016` — Spike: corpus selection, external signals, profile schema and hybrid ranking

- **Type:** `spike`
- **Date:** 2026-11-16
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (14 + 7)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
Q1–Q4 in `docs/spikes/16-recommendation-signals-and-ranking.md` are answered (`status: answered`). §5 has the findings and §6 has the summary, the list of `docs/architecture.md` changes and the owner decisions. Throwaway scripts and evidence are in `spikes/16-recommendation/`; the raw data is in the gitignored `data/` folder.

**Spend:**
- Paid LLM ≈ **$0.13**:
  - `gpt-6-luna`: 300 base profiles, 50 with reviews, 12 intents, judges.
  - `gpt-6.1-terra`: 50 reference labels, ≈ $0.07. This deviates from the "luna only" plan.
- TMDB and Wikidata: about 5,800 calls, $0.

**Answers:**
- **Q1, corpus:**
  - The catalogue is **51,527** flat-rate movies (≥ 10 votes) across ES/US/BO.
  - **Gate G7** keeps **14,478**: age-aware TMDB votes, WR ≥ 5.0, and WR ≥ 6.3 if older than 25 years. That's 17.4% pre-2000, 3,203 from the last 3 years, and no notorious filler.
  - **Retention:** keep films that leave streaming (`streamable: []`), with an eviction rule (over 12 months unstreamable, once past 60% of M0). No theatrical buffer.
  - Real churn is the new todo **feat-017**. G7 ≈ 102 MiB (20% of M0). Enriching G7 ≈ $1.03 once via Batch.
- **Q2, signals:**
  - **IMDb:** a 90.7% join via Wikidata, but it mostly duplicates TMDB (WR Spearman 0.83). It would add only 291 films (2%), and its licence bars building a movie database. Recommendation: drop it.
  - **Critics and awards from Wikidata (CC0):** 69.8% coverage (40.4% for 2020+), with Spearman 0.58–0.59 vs TMDB WR, so a distinct signal. Keep it as an internal `critic_score`.
  - **Transient TMDB reviews:** no gain against the reference (ending_feel 0.74 → 0.68, intensity 0.86 → 0.74) at +35% tokens. Recommendation: drop, provisionally; the reference is biased toward the base variant.
- **Q3, mirror schema v1:**
  - 400/400 profiles valid; 12/12 intents sensible.
  - New mirror fields: `certification_us`/`certification_es` ↔ `audience` (US cert covers 63% of films, hence a fallback proposal), and `original_language`.
  - Movie profile embeddings beat TMDB-text embeddings (74 vs 64 judged points). The query-side template and field matching show no gain.
  - Judge noise: 26% item-level disagreement.
  - `viewing_effort` is near-binary in practice.
- **Q4, ranking:**
  - Retrieve **K = 150**: broad queries reach vector rank 114; recall 0.94.
  - The hybrid re-score is directional (77 vs 73 points, 8/12 ties). It raises top-5 quality (WR 6.61 → 6.89) and has a failure mode: it pushes acclaimed demanding classics into "easy" requests.
  - Franchise duplicates are rare (1 slot in 12 top-25 lists).

**Other changes:**
- Owner decisions recorded in `docs/architecture.md` §7: Q6 is OpenAI only with spend approved; Q14 is the age note.
- New todo chore `feat-017` (churn) in `feature_list.json`.

**Review:**
- **Round 1** (14 findings), all fixed:
  - dedupe measured;
  - judge noise and hybrid claims corrected;
  - enums listed;
  - certification gap;
  - A/B bias caveat;
  - hybrid failure mode;
  - architecture-change table;
  - IMDb wording and values removed;
  - Wikidata threshold;
  - depth critic blend;
  - retention and eviction;
  - profile distribution;
  - provenance;
  - terra price.
- **Round 2** (7 low findings), all fixed in wording, docstrings, `churn.py` interval and the feat-017 description.

## Verification Evidence
```text
$ uv run --no-project --python 3.13 python spikes/16-recommendation/catalog.py
[ES] 25 slices, 1319 pages, 26110 rows · [US] 25 slices, 2114 pages, 42062 rows · [BO] 25 slices, 782 pages, 15432 rows
union_movies 51527, tmdb_calls 4290 (all 200), 255.9 s

$ ... corpus.py   -> corpus_report.json
G7: kept 14478 (ES 9952, US 11961, BO 6835), pre-2000 17.4%, last 3 y 3203
imdb_join 46647/51414 (90.7%); spearman ratings 0.811; imdb_rescue_over_G7 291 (2%)

$ ... wikidata_signals.py ; critics.py   -> critics_report.json
rt_or_mc 10110/14478 (69.8%); 2020+ 40.4%; spearman vs TMDB WR: MC 0.58, RT 0.588

$ ... enrich.py      profiles: 400 rows, 0 errors, est. spend $0.1223
$ ... ab_eval.py     base vs reviews vs reference (50 films): ending_feel 0.74 vs 0.68, intensity exact 0.86 vs 0.74, input tokens 770 vs 1039
$ ... embed_pool.py  embedded 14478 in 1029.0s (14.1 docs/s)
$ ... rank_eval.py   pool A relevance@5 1.217 -> 1.283, WR@5 6.613 -> 6.893; pool B template 1.263, description 1.298, raw 1.298, tmdb-text 1.123
$ ... depth_by_query.py   broad K50/K100/K150 0.85/0.91/0.94; specific 0.96/0.96/0.96
$ ... structured_match.py relevance@5 embedding 1.316 vs embedding+match 1.228
$ ... followups.py   dup slots top-25: base 1, hybrid 0; cert US 190/300, ES 100/300, either 209/300; kids kept 55/56/68

$ uv run poe check   (2026-11-16 12:43 CET, Windows)
All checks passed! · 14 files already formatted · pyright 0 errors · Contracts: 2 kept, 0 broken · 26 passed
```

## Unverified
- The catalogue churn rate: feat-017, needs a re-crawl at least 24 h later.
- Retrieval with real profile embeddings at corpus scale. Pool A used TMDB-text embeddings; only 300 movies have profiles.
- The hybrid weights: hand-set and judged by an LLM on 12 queries. They need the owner-labelled golden set.
- `$vectorSearch` latency at K = 150.
- The `audience` fallback rule and the `teens` mapping, which are untested proposals.
- Whether a stored movie missing from the daily `/discover` lists reliably means `streamable: []`.
- CI on the PR.
