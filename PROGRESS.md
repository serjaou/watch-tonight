# Progress

## Now
- **Active feature:** `feat-016` (Spike: corpus selection, external signals, profile schema, hybrid ranking), branch `spike/recommendation-signals`. Done; its PR waits for the owner's merge.
- **State:** `feat-016` is complete (`status: answered`; §5 findings, §6 summary and architecture-change table).
  - Gate G7 gives 14,478 films. IMDb and reviews are recommended against. Wikidata `critic_score` stays internal.
  - The v1 mirror schema is set, and retrieval uses K = 150 with a hybrid re-score.
  - Spend ≈ $0.13: `gpt-6-luna`, plus ≈ $0.07 on `gpt-6.1-terra` for the reference labels.
  - Owner decisions Q6 and Q14 are recorded in `docs/architecture.md` §7.
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-16 12:43 CET, Windows.
- **Next step:** after the merge, `feat-012` (architecture refinement and MVP backlog slicing). It's a chore, so it's ready. It applies the spike 16 §6 table and the decisions below. `feat-017` (churn re-crawl) can run any time after 2026-11-17 10:41 UTC.
- **Waiting on owner:**
  - Merge the `feat-016` PR. The spike 16 decisions are recorded as `docs/architecture.md` §7 Q15–Q17: no IMDb, no reviews, the `audience` fallback, keep-on-churn with no eviction job.
  - Optional: add the age-note line (Q14) and the `audience` fallback interpretation of P3 (Q16) to `docs/product.md`.
- **Unverified:**
  - The items under "Unverified" in `docs/handoffs/feat-016.md`, including corpus-scale profile retrieval, hybrid weights without a golden set, and K = 150 latency.
  - CI on the PR.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
- 2026-11-16 · Windows · Claude Code · `feat-016`: answered recommendation spike Q1–Q4 (G7 gate 14,478 films, no IMDb/reviews, v1 mirror schema, K=150 hybrid; $0.13) → [feat-016.md](docs/handoffs/feat-016.md)
- 2026-11-16 · Windows · Claude Code · `feat-011`: answered runtime LLM spike Q1–Q6 (`gpt-6-luna` `$0.00067`/query, 0 schema errors; Gemini free tier not usable for EEA users) → [feat-011.md](docs/handoffs/feat-011.md)
- 2026-11-15 · Mac · Antigravity · `feat-010`: answered embedding runtime spike Q1–Q6 (`fastembed` `bge-small-en-v1.5` 384-d: `p50=5.04ms`, `279MB` RSS, `212MB` disk) → [feat-010.md](docs/handoffs/feat-010.md)
- 2026-11-15 · Mac · Antigravity · `feat-008`: answered TMDB terms, rate limits (25.2 req/s), ES/US/BO coverage, and 24.5h provider churn → [feat-008.md](docs/handoffs/feat-008.md)
- 2026-11-15 · Mac · Antigravity · `feat-009`: answered Atlas M0 + `atlas-local` vector search spike Q1–Q5 (`p50=60.5ms`/`p95=120.8ms`, 5-way pre-filter, 20k storage) → [feat-009.md](docs/handoffs/feat-009.md)
- 2026-11-14 · Mac · Antigravity · `feat-015`: split state/log docs into slim index files + per-entry files in `docs/{handoffs,learning,harness-log}/` → [feat-015.md](docs/handoffs/feat-015.md)
- 2026-11-13 · Mac · Antigravity · `feat-006`: added `docs/metrics.md` and `/handoff` process tracking → [feat-006.md](docs/handoffs/feat-006.md)
- 2026-11-13 · Mac · Antigravity · `feat-014`: validated harness with `validate-harness.mjs` (`60/100` → `92/100`) → [feat-014.md](docs/handoffs/feat-014.md)
- 2026-11-13 · Windows · Claude Code · `feat-013`: recorded owner decisions Q8–Q11, posters, zero-cost budget → [feat-013.md](docs/handoffs/feat-013.md)
- 2026-11-13 · Windows · Claude Code · `feat-005`: wrote `docs/architecture.md` v0 and spike question files `08`–`11` → [feat-005.md](docs/handoffs/feat-005.md)
- 2026-11-12 · Mac · Antigravity · `feat-007`: verified `feat-004` Stop hook and native reviewer on the Mac → [feat-007.md](docs/handoffs/feat-007.md)
- 2026-11-12 · Windows · Claude Code · `feat-004`: first Windows session, Claude Code support (ADR 0003), autonomous runs (ADR 0004) → [feat-004.md](docs/handoffs/feat-004.md)
- 2026-11-12 · Mac · Antigravity · `feat-000`: end-to-end harness dry run (mood prompt validator P4) → [feat-000.md](docs/handoffs/feat-000.md)
- 2026-11-11 · Mac · Antigravity · `feat-001`: repo skeleton, `pyproject.toml`, layers, CI, and core harness v0 → [feat-001.md](docs/handoffs/feat-001.md)
