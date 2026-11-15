# Progress

## Now
- **Active feature:** `feat-010` (Spike: query-time embedding runtime in `docs/spikes/10-embedding-runtime.md`), branch `spike/embedding-runtime` (`done`, waiting for owner PR merge).
- **State:** `feat-010` completed (`status: answered` in `docs/spikes/10-embedding-runtime.md`): answered Q1–Q6 choosing `BAAI/bge-small-en-v1.5` (`384-d`) via `fastembed` (ONNX Runtime CPU) (`p50=5.04ms`, `p95=5.88ms`, `279.1 MB` query-time RSS, `+212.2 MB` added image size, `0.58s` cold start, `11.77 min` for 20k profiles on CPU, `0.999999` cosine parity with PyTorch).
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-15 17:39 CET, Mac.
- **Next step:** After the owner merges the `feat-010` PR to `main` and puts LLM API keys (`GEMINI_API_KEY` and/or `OPENAI_API_KEY`) in `.env`, start `feat-011` (*Spike: runtime LLM* in `docs/spikes/11-runtime-llm.md`).
- **Waiting on owner:** Merge the `feat-010` PR to `main`; put LLM API keys in local `.env` before starting `feat-011`.
- **Unverified:** CI on the `feat-010` PR.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
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
