# Progress

## Now
- **Active feature:** `feat-018` (Walking skeleton: search end to end) — `/spec` draft on branch `docs/feat-018-spec-draft` (`feat-017` is merged to `main`).
- **State:**
  - Interviewed the owner for `feat-018` (`/spec`) and wrote the draft spec in `docs/specs/18-walking-skeleton.md` (`status: draft`).
  - Agreed on a 3-way split of the walking skeleton (Checkpoint Finding 7):
    - **Slice A (`feat-018`, in `docs/specs/18-walking-skeleton.md`):** end-to-end `POST /search` across `domain`, `application`, `infra` (`mongodb/mongodb-atlas-local:8.0`) and `api` (FastAPI) with deterministic fake `LanguageModel` and `Embedder` ports, all 5 response states (HTTP 200/422/503), step-4 deterministic checks + `collection_id` dedupe, the 6 deterministic CI evals, and Atlas pre-filter + index lifecycle verification.
    - **Slice B (`feat-028`, in `docs/backlog.md` Proposed):** real `fastembed` (`BAAI/bge-small-en-v1.5`) `Embedder` adapter, verifying `query_embed` instruction prefixing, embedding the ~300 spike-16 seed profiles with `template(profile)`, and measuring cold/warm query-embedding latency.
    - **Slice C (`feat-029`, in `docs/backlog.md` Proposed):** real Pydantic AI + OpenAI `gpt-6-luna` `LanguageModel` adapter, verifying `ModelRetry` on the live model, live token/cost tracking in `trace`, and first end-to-end latency numbers (Q7).
  - Owner learning decision (Checkpoint Finding 4): agent writes the slice first, followed by a `/defend` session and owner refactoring/extension.
  - Active window in `feature_list.json`: `feat-018`, `feat-027`, `feat-026`, `feat-019`.
- **Last check:** `uv run poe check` green (ruff, format, pyright 0 errors, lint-imports 2/2, pytest 26 passed), 2026-11-22 23:53 CET, Mac.
- **Next step:**
  - On the Windows laptop: review and approve `docs/specs/18-walking-skeleton.md` (`status: approved`), decide whether to promote `feat-028` and `feat-029` from `docs/backlog.md` (Proposed) into `feature_list.json` / Ordered, authorize writing `tests/acceptance/test_walking_skeleton.py`, and build `feat-018`.
  - Start Docker Desktop before running `feat-018` integration tests (`uv run poe test-all` answers Q4 on Windows).
- **Waiting on owner:**
  - Refine `feat-018`: review and approve `docs/specs/18-walking-skeleton.md` and confirm ordering of the proposed split slices (`feat-028`, `feat-029`).
- **Unverified:**
  - The items under "Unverified" in `docs/handoffs/feat-012.md` and `docs/handoffs/feat-017.md`: extra pre-filters, `ModelRetry` on the real model, Batch support, K = 150 latency, aliasing safety, Q4 on Windows, and multi-month churn rates.
  - CI on the pushed `docs/feat-018-spec-draft` branch.

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
