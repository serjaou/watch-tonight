# Progress

## Now
- **Active feature:** `feat-011` (Spike: runtime LLM, `docs/spikes/11-runtime-llm.md`), branch `spike/runtime-llm`. Done; its PR waits for the owner's merge.
- **State:** `feat-011` is complete (`status: answered`).
  - **Recommended:** `gpt-6-luna` as primary, at `$0.00067` per query and ≈ `$1.10` for 20k profiles via Batch, with 0 schema errors. Framework: Pydantic AI `NativeOutput` + `FallbackModel`, with `gemini-3.5-flash-lite` paid as an optional fallback.
  - **Ruled out:** the Gemini free tier for the online path, because its terms forbid serving EEA users.
  - Spend: OpenAI ≈ `$0.022`, Gemini `$0`.
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-16 10:35 CET, Windows.
- **Next step:** after the `feat-011` PR merges, start `feat-016` (*Spike: corpus selection, signals, profile schema, hybrid ranking*, `docs/spikes/16-recommendation-signals-and-ranking.md`). It's ready: questions listed, all dependencies done. Keep paid LLM calls to cents; the owner's OpenAI credit is ~$10.
- **Waiting on owner:**
  - Merge the `feat-011` PR.
  - Decide before `feat-012`, using spike 11 §Q2 and §Q6:
    - (a) approve a small usage-based spend for the online LLM (≈ $0.67 per 1,000 queries) and set a monthly hard cap on the OpenAI project;
    - (b) the minors question: Gemini's terms bar services likely used by under-18s, and OpenAI needs a parent's or guardian's consent;
    - (c) whether to enable Gemini billing for a fallback.
  - Optional: read the Gemini free-tier RPD and TPM in AI Studio (https://ai.dev/rate-limit).
- **Unverified:**
  - CI on the `feat-011` PR.
  - The items under "Unverified" in `docs/handoffs/feat-011.md`, including retry-with-feedback on a real model and Gemini latency including 503s.

## Log (newest first, 1 line each; full details in `docs/handoffs/`)
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
