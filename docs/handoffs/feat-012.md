# Handoff: `feat-012` — Architecture refinement and MVP backlog slicing

- **Type:** `chore`
- **Date:** 2026-11-16
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (18 + 9)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- **`docs/architecture.md` v1:** applies spikes feat-008, 009, 010, 011 and 016 plus the owner decisions.
  - Components: a daily `/discover` crawl with G7 admission, Wikidata signals, Batch enrichment, profile-template embeddings.
  - Ports: `QualitySignals`, `AsyncMongoClient`, fastembed, Pydantic AI.
  - Query flow v1:
    - a three-channel `QueryIntent` plus `unmapped_constraints`;
    - `$vectorSearch` K = 150, with tested vs to-verify pre-filters and a step-4 fallback for `audience`;
    - step-4 re-checks plus the hybrid re-score and collection dedupe;
    - a step-6 pick-count check.
  - Offline pipeline: G7 with pinned WR constants and admission data checks, metadata freshness and re-fetch owned by feat-020, keep-on-churn.
  - Data model v1: filter paths including `_id`, `null` for missing certifications, a curated providers list.
  - §7: Q1, Q2, Q3, Q5 and Q11 moved to Decided; new Q18 for unmapped constraints; Q4, Q7 and Q12 stay open, each with an owning item.
- **ADRs:**
  - 0005: closed vocabulary and mirror schema (Q11, Q16, Q18).
  - 0006: OpenAI `gpt-6-luna` through Pydantic AI, using Chat Completions, with Batch and `ModelRetry` to be verified.
  - 0007: fastembed bge-small, movies embed `template(profile)`.
  - 0008: G7 gate, TMDB-only quality, hybrid re-score.
- **Backlog sliced** with the owner (skeleton first; the skeleton reuses the spike-16 data):
  - `feature_list.json` is now the **active window**: feat-017, feat-018 (walking skeleton) and feat-019 (profile design).
  - **New `docs/backlog.md`** holds feat-020 to feat-025 in an **Ordered** section with full detail and notes, plus a **Proposed** section that only the owner promotes.
- **Workflow changes** from the owner's feedback ("relevance over numeric caps"):
  - sizes are guides (about 1 page, about 10 acceptance tests ordered by relevance and priority), never caps that cut detail;
  - refill rules for the active window from the backlog;
  - backlog detail survives a move into `feature_list.json`;
  - `/spec` copies an item's backlog notes into its spec.
  - Files: `AGENTS.md`, `.agents/skills/spec`, `.agents/skills/handoff`, `docs/workflow.md`, `README.md`.
- **`docs/product.md`**, edited with the owner's consent: three "(verify)" markers removed (posters, BO, P5); the dead marker sentence deleted; the "couldn't apply" note added to §4.
- **Owner decisions this session:**
  - backlog order;
  - the skeleton reuses the spike-16 data;
  - sizing as guides, plus the backlog concept;
  - deterministic evals start in the skeleton, and the pitch-quality eval goes to feat-022;
  - unmapped constraints are reported to the user (Q18);
  - the `product.md` edits above.
- **Not done:**
  - **Q4 on Windows:** Docker Desktop wasn't running, and I didn't start it unasked. feat-018's integration tests will answer it.
  - **A harness test for `docs/backlog.md`** (ids unique across files) wasn't added. It's optional.

## Verification Evidence
```text
$ uv run poe check   (2026-11-16 15:50 CET, Windows)
Poe => ruff check src tests scripts · All checks passed!
Poe => ruff format --check · 14 files already formatted
Poe => pyright · 0 errors, 0 warnings, 0 informations
Poe => lint-imports · Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration' · 26 passed

feature_list.json: 48 lines (cap 120); AGENTS.md: 58 lines (cap 150)
Reviewer round 1: 18 findings (6 medium, 12 low), all addressed: 14 fixed, 4 settled by owner decisions.
Reviewer round 2: 9 findings (1 medium, 8 low), all fixed. Round 2 confirmed all round-1 items.
```

## Unverified
- The pre-filters `year`, `original_language`, certification and `audience` (feat-018).
- `ModelRetry` on the real model (feat-018).
- Batch API support (feat-021).
- K = 150 latency (feat-021).
- Provider aliasing safety (feat-020).
- Q4 on Windows (feat-018).
- CI on the PR.
