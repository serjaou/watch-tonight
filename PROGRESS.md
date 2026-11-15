# Progress

## Now
- **Active feature:** `feat-008` (Spike: TMDB terms, rate limits and watch providers in `docs/spikes/08-tmdb-and-providers.md`), branch `spike/tmdb-and-providers` (`done`, waiting for owner PR merge).
- **State:** `feat-008` completed across 2 sessions (`status: answered` in `docs/spikes/08-tmdb-and-providers.md`): answered Q1–Q8, Q12, and Q13 (`25.2 req/s`, `0` `429`s, ES/US/BO flat-rate coverage, `0.0%` missing `poster_path`, and 24.5h provider churn across Popular 500: ES `2.2%`, US `2.6%`, BO `0.6%`; `1–3` brand-new flat-rate releases/day per country).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-15 16:23 CET, Mac.
- **Next step:** After the owner merges the `feat-008` PR to `main`, start `feat-010` (*Spike: query-time embedding runtime* in `docs/spikes/10-embedding-runtime.md`).
- **Waiting on owner:** Merge the `feat-008` PR to `main`. Before `feat-011`: put LLM API keys in local `.env`.
- **Unverified:** CI on the `feat-008` PR.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
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
