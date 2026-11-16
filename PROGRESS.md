# Progress

## Now
- **Active feature:** `feat-012` (Architecture refinement and MVP backlog slicing), branch `chore/architecture-v1`. Done; its PR waits for the owner's merge.
- **State:**
  - `docs/architecture.md` is now v1, with ADRs 0005–0008.
  - The MVP is sliced, skeleton first. `feature_list.json` is the active window (feat-017, feat-018, feat-019); later items (feat-020 to feat-025) are in `docs/backlog.md`.
  - Sizes are guides, not caps: relevance and priority first (owner).
  - Owner decisions this session are recorded as architecture §7 Q15–Q18 and in `docs/product.md` (with consent).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-16 15:50 CET, Windows.
- **Next step:** after the merge:
  - `feat-017` (churn re-crawl), runnable after 2026-11-17 10:41 UTC (TMDB only, $0);
  - then `/spec` for `feat-018` (walking skeleton) with the owner. It has no spec yet; start rule 3b applies.
  - Start Docker Desktop before feat-018: its integration tests answer Q4 on Windows.
- **Waiting on owner:**
  - Merge the `feat-012` PR.
  - Be available for the feat-018 `/spec` interview.
- **Unverified:**
  - The items under "Unverified" in `docs/handoffs/feat-012.md`: the extra pre-filters, `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, and Q4 on Windows.
  - CI on the PR.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
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
