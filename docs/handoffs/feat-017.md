# Handoff: `feat-017` — Measure flat-rate catalogue churn (spike 16 follow-up)

- **Type:** `chore`
- **Date:** 2026-11-21
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (6 + 2)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- **Method:** two complete `/discover` flat-rate crawls of ES, US and BO (≥ 10 votes), 5.31 days apart (2026-11-16 10:41 → 2026-11-21 18:10 UTC), compared by set difference. Unlike spike 08's Popular-500 comparison, this isn't circular: every flat-rate film is in both snapshots.
- **Checked against TMDB's per-movie answer** (`/movie/{id}?append_to_response=watch/providers`, the source of `streamable`) on seeded samples, so the result doesn't rest on `/discover` alone.
- **Results** (spike 16 Q1, "Retention"):
  - **G7 corpus:** 32 of 14,478 films left all launch countries (**6.0 a day**, 4.1–8.5 within counting noise); 133 more left one or two countries. **130 admissions (24.5 a day**, 20.4–29.1). 105 of them are from 2023 or earlier (median 450 votes), and 84 of those newly reached flat-rate. So most admissions are older films entering a service, not new releases.
  - **Whole crawl:** 183 of 51,527 left all launch countries (34.5 a day); 540 arrived (101.7 a day).
  - **Verification:** leavers 321/325 have no flat-rate offer now (2 fell below 10 votes, 2 were `/discover` misses); arrivals 378/379 confirmed; control 300/300; all 32 G7 films that left everywhere have no flat-rate offer in any launch country.
- **What it sets:**
  - **Schedule (architecture Q12):** keep the daily crawl, availability refresh and admission (≈ 31 G7 films a day lost flat-rate in at least one country; admission costs ≈ 25 bundle calls and ≈ $0.002 of Batch profiling a day).
  - **Retention (architecture Q17):** the owner's decision stands (keep leavers, no eviction job in the MVP). Extrapolated, storage grows ≈ 63 MiB a year from admissions, about 4× the rate films leave, so 60% of M0 is about 3 years away (2.7–3.9) and the gate, not eviction, is the storage lever.
  - **"Missing from every crawl → `streamable: []` without a call":** confirmed (32/32). A `/discover` miss hides a streamable film; it never shows one that isn't.
- **Files:**
  - Scripts: `spikes/16-recommendation/churn.py` (rewritten: per country, combined, G7, admissions by year, counting-noise ranges, completeness guard, window-named outputs), new `churn_verify.py`, `catalog.py --dated`.
  - Outputs (committed): `churn_report_2026-11-16_2026-11-21.json`, `churn_verify_report_2026-11-16_2026-11-21.json`, `catalog_stats_2026-11-21.json`. Local (gitignored): `catalog_ids_2026-11-21.json.gz` (ids per region plus G7 ids, for a longer-window re-measure).
  - Docs: spike 16 Q1 and §6 summary, `docs/architecture.md` §4 and Q12, `docs/backlog.md` (feat-020 notes), `docs/metrics.md` (churn row), spike 26 (growth input and *The Anacondas* note), spike 08 (superseded note on its one-day estimate).
- **Spike 16's own files are unchanged:** `data/catalog.jsonl` and `catalog_stats.json` are still the 2026-11-16 crawl, so its scripts reproduce its tables. The new raw rows are `data/catalog_2026-11-21.jsonl` (gitignored, Windows laptop only).

## Verification Evidence
```text
$ uv run --no-project --python 3.13 python spikes/16-recommendation/catalog.py   (2026-11-21 18:10 UTC; later renamed to the --dated file names)
[ES] 25 slices, 1324 pages, 26214 rows
[US] 25 slices, 2136 pages, 42470 rows
[BO] 25 slices, 785 pages, 15486 rows
"union_movies": 51884, "tmdb_calls": 4320, "tmdb_status": {"200": 4320}, "seconds": 225.3

$ uv run --no-project --python 3.13 python spikes/16-recommendation/churn.py --old 2026-11-16 --new 2026-11-21
"days_between_crawls": 5.31
"regions": BO left 25 / arrived 79; ES left 178 / arrived 282; US left 211 / arrived 619
"combined": left_all_launch_regions 183 (34.5/day), arrived_new_to_all_regions 540 (101.7/day)
  arrived_split: released_in_last_90_days 12, older_and_under_20_votes 182, older_and_established 346
"g7_corpus": old 14478, new 14572, left_all_launch_regions 32 (6.0/day, noise [4.1, 8.5]),
  left_some_but_not_all_regions 133, lost_flat_rate_in_at_least_one_region_per_day 31.1,
  admissions_new_to_g7 130 (24.5/day, noise [20.4, 29.1]),
  admissions_by_release_year: 2026 10+4 (median 42.5), 2025 5+2 (42), 2024 3+1 (223),
                              2023_or_older 84+21 (median 450)   [not_in_old_crawl + in_old_crawl_below_g7]

$ uv run --no-project --python 3.13 python spikes/16-recommendation/churn_verify.py   (2026-11-21 18:17 UTC)
ES.left {no flat-rate: 147, flatrate_but_under_10_votes: 2, flatrate: 1}   (150 of 178)
US.left {no flat-rate: 149, flatrate: 1}                                   (150 of 211)
BO.left {no flat-rate: 25}                                                 (25 of 25)
ES.arrived {flatrate: 149, buy+rent: 1}; US.arrived {flatrate: 150}; BO.arrived {flatrate: 79}
ES/US/BO.stayed {flatrate: 100} each
g7_left_all {no_flatrate_in_any_launch_region: 32}
disagreements: A Costume for Nicolas (20 votes), No Ordinary Heist (19) still on Prime Video;
  Feral (9), Mostro (0) under 10 votes; David (209) listed by /discover without flat-rate
"tmdb_calls": 964, "tmdb_status": {"200": 964}

After the review fixes, churn.py was re-run offline (window-named outputs):
report same, sets same, snapshot same: True True True

$ uv run poe check   (2026-11-21 19:39 CET, Windows)
Poe => ruff check src tests scripts · All checks passed!
Poe => ruff format --check · 14 files already formatted
Poe => pyright · 0 errors, 0 warnings, 0 informations
Poe => lint-imports · Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration' · 26 passed

Reviewer round 1: 6 findings (2 medium, 1 low-medium, 3 low), all fixed. It traced every number and
  found G7 with pinned constants identical to corpus.py's G7 on both crawls (0 differences).
Reviewer round 2: confirmed the 6 fixes; 2 low findings (a dangling cross-reference; re-runs would
  overwrite the evidence), both fixed without a third round (ADR 0004: at most 2 rounds).
Cost: TMDB only, $0 (4,320 crawl calls + 3 verify runs × 964 + 5 single-film lookups).
```

## Reviewer prompt (measurement checklist, input for feat-027)
Added to the standard reviewer instructions for this measurement task:
```text
- every number written in the changed docs traces to a committed output file or is correctly
  derived from one; check the arithmetic of derived figures (per-day rates, yearly
  extrapolations, MiB, % of the 512 MiB tier, years to 60%);
- each number is labelled honestly as measured vs extrapolated/estimated, with sample sizes and
  the single-window limitation stated; summaries don't claim more than the reports;
- correctness of the scripts' logic (set arithmetic, the gate vs the original script's gate,
  sampling and classification), and whether any conclusion depends on a bug;
- scope creep beyond the item.
Read-only Python over the gitignored raw data was allowed; re-running the TMDB scripts was not.
```

## Unverified
- **Rates over months:** all rates come from one 5.3-day window in November; the yearly figures are linear extrapolations. `ingestion_runs` (feat-020) or a later `churn.py --old 2026-11-21` run can confirm them.
- **Provider swaps within a country** (Netflix → Prime Video) aren't visible to a region-level crawl; spike 08 Q7 is still the only measurement.
- **Films that left and came back, or arrived and left, inside the window** are invisible to a two-snapshot diff.
- **Cross-tool review:** the checkpoint review suggests reviewing measurement work with the other machine's tool (the rule arrives with feat-027); this was reviewed with Claude Code only.
- CI on the PR.
