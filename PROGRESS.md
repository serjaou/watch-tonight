# Progress

## Now
- **Active feature:** `feat-018` (walking skeleton, part 1), `in_progress` on branch `feat-018-walking-skeleton`. Its spec is approved and merged (PR #18, 2026-11-24).
- **State:**
  - 2026-11-22 (Mac, Antigravity): `/spec` interview and first draft of `docs/specs/18-walking-skeleton.md`.
  - 2026-11-24 (Windows, Claude Code): cross-tool review of that draft; the owner accepted every recommendation:
    - The walking skeleton is split in four, in this order: part 1 in-memory, no Docker (`feat-018`); part 2 local Atlas (`feat-030`, draft spec `docs/specs/30-atlas-local-search.md`); part 3 real embedder (`feat-028`); part 4 real LLM (`feat-029`). Parts 3 and 4 have no spec yet; their notes are in `docs/backlog.md`.
    - Tests use committed fictional fixture films; spike 16's 300 films become a seed script in part 2 (they share no collection, and the local file lacks posters, Spanish ratings and availability).
    - The step-4 and step-6 check functions live in `domain`; the retry with the error fed back lives in the part-4 LLM adapter (architecture steps 5–6 updated).
    - Zero candidates → *Partial* with an empty list and no re-rank call. Response contract, input limits (`exclude_ids` ≤ 5,000, `avoid` from the vocabulary) and new dependencies are in the specs.
    - The P5 attribution notice now uses the wording from section 3 of TMDB's terms (`product.md`, README).
    - The query-flow sequence diagram now lives in architecture §3 (the checkpoint guide keeps a dated copy).
    - The v1 list of hard limits is not frozen: content limits (genre, director, main cast, keyword flags) will be added after spike feat-026 question 7 decides how (ADR 0005); that work is `feat-031`, right after `feat-026` (owner, 2026-11-24).
    - Step headings in architecture §3 and a "link every reference" `/spec` rule join `feat-027` as part (4) (owner, 2026-11-24).
  - Owner learning decision (2026-11-22, kept): the agent writes the code; then `/defend`, and the owner refactors or extends a module.
  - Active window in `feature_list.json`: `feat-018`, `feat-030`, `feat-028`, `feat-029`, `feat-027`, `feat-026`, `feat-031`, `feat-019`.
  - Raw crawl rows (gitignored, Windows laptop only): `spikes/16-recommendation/data/catalog.jsonl` (2026-11-16) and `data/catalog_2026-11-21.jsonl`; also `data/pool_b_movies.jsonl` (spike 16's 300 films, no posters, Spanish ratings or availability).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-24 17:24 CET, Windows.
- **Next step:**
  - Build `feat-018`: acceptance tests and fixtures first (`tests/acceptance/test_walking_skeleton.py`, once the owner authorizes it in the session), then domain → application → infra (in-memory) → api → evals. No Docker needed for part 1.
  - Start Docker Desktop before part 2 (`feat-030`): its integration tests answer Q4 on Windows.
- **Waiting on owner:**
  - Review the part 2 draft spec (`docs/specs/30-atlas-local-search.md`) before `feat-030`.
- **Unverified:**
  - The items under "Unverified" in `docs/handoffs/feat-012.md` and `docs/handoffs/feat-017.md`: extra pre-filters, `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, Q4 on Windows, and multi-month churn rates.
  - CI on this branch: it runs only on PRs and `main`; no PR yet.

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
