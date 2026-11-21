# Progress

## Now
- **Active feature:** none in progress. `feat-017` (catalogue churn) is done on branch `feat-017-churn`, with a PR to `main` waiting for the owner's merge.
- **State:**
  - feat-017 measured churn from two complete crawls 5.3 days apart, checked film by film against `/watch/providers`. G7 films leave all launch countries at ≈ 6 a day and are admitted at ≈ 24.5 a day, mostly older films entering a service. The daily crawl, refresh and admission stay; the owner's "no eviction job in the MVP" stands. Detail: spike 16 Q1, [feat-017.md](docs/handoffs/feat-017.md).
  - `docs/architecture.md` is v1, with ADRs 0005–0008. Q12 now has measured rates; still open for the rates over months (feat-020).
  - Active window: feat-018 (walking skeleton), feat-027 (reviewer spike checklist + stale-number cleanup), feat-026 (quality signals and corpus gate spike), feat-019 (profile design); later items (feat-020 to feat-025) are in `docs/backlog.md`.
  - Owner decisions 2026-11-21 (`docs/product.md`, with consent): an English-language bias in the corpus is accepted; audio and subtitle languages are not considered.
  - Raw crawl rows (gitignored, Windows laptop only): `spikes/16-recommendation/data/catalog.jsonl` (2026-11-16, spike 16's tables) and `data/catalog_2026-11-21.jsonl` (feat-017). The committed `catalog_ids_2026-11-21.json.gz` lets either machine measure a longer churn window.
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-21 19:39 CET, Windows.
- **Next step:**
  - After the merge: `/spec` for `feat-018` (walking skeleton) with the owner. It has no spec yet; start rule 3b applies. Its notes (split, verification list, owner-written part) are in `docs/backlog.md`, feat-018 section.
  - Start Docker Desktop before feat-018: its integration tests answer Q4 on Windows.
- **Waiting on owner:**
  - Merge the feat-017 PR.
  - Refine feat-018: be available for its `/spec` interview.
  - Optional: review the feat-017 PR with Antigravity on the Mac (the checkpoint's cross-tool review advice; the rule itself comes with feat-027).
- **Unverified:**
  - feat-017: rates over months (one 5.3-day window, extrapolated linearly); provider swaps within a country; films that left and came back inside the window.
  - The items under "Unverified" in `docs/handoffs/feat-012.md`: the extra pre-filters, `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, and Q4 on Windows.
  - CI on the PR.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
- 2026-11-21 · Windows · Claude Code · `feat-017`: churn from two full crawls 5.3 days apart, verified against `/watch/providers` (G7: ≈ 6 leave/day, ≈ 24.5 admitted/day); daily schedule kept → [feat-017.md](docs/handoffs/feat-017.md)
- 2026-11-16 · Windows · Claude Code · `feat-012`: architecture v1 + ADRs 0005–0008, MVP sliced skeleton-first (active window + `docs/backlog.md`), sizing as guides → [feat-012.md](docs/handoffs/feat-012.md)
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
