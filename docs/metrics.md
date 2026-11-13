# Metrics

**What this file is:** the product, system, eval and process metrics for `watch-tonight` — where each number comes from, what its target is, and the per-feature `/handoff` log (`feat-006`).
**Related docs:** [docs/product.md](product.md) (rules P1–P7, response states, MVP DoD), [docs/architecture.md](architecture.md) (query `trace`, `ingestion_runs`, `eval_runs`, open questions Q1–Q13), [docs/harness-log.md](harness-log.md) (agent/harness failures).

---

## 1. Product, System & Eval Metrics

### 1.1 Online query metrics
Raw data comes from the per-response `trace` returned by `SearchMovies` ([docs/architecture.md](architecture.md) §3 step 7 and §6).

| Metric | Source in `trace` | Target / Budget | Notes |
|---|---|---|---|
| **End-to-end latency (`p50` / `p95`, ms)** | `trace.total_ms` | Initial guess `p95 < 10,000 ms` ([docs/product.md](product.md) §6); confirmed after spikes and measured in the first end-to-end slice (`Q7`) | Includes validation, LLM intent, query embedding, Atlas `$vectorSearch`, deterministic filter check, and LLM re-rank + pitch |
| **Stage latency (`p50` / `p95`, ms)** | `trace.stages.{understand,embed,retrieve,rerank_and_pitch}_ms` | Component baselines measured in `feat-009` Q5 (`retrieve`), `feat-010` Q2 (`embed`), `feat-011` Q4 (`understand`, `rerank_and_pitch`) | Pinpoints bottlenecks and decides whether the 2 LLM calls stay separate |
| **Response state distribution (`%`)** | `response.state` | Track share of `Success`, `Partial`, `Results without pitches`, `Invalid input`, and `Service unavailable` ([docs/product.md](product.md) §4) | Distinguishes thin catalogue coverage (`Partial`) from step-6 LLM failures (`Results without pitches`, `Q8`) and step-2/infra failures (`Service unavailable`) |
| **LLM retry rate** | `trace.retries.{understand,rerank_and_pitch}` | Baseline measured in `feat-011` Q3 | Counts how often structured output or deterministic validation (step 2 or step 6) triggers a retry |
| **Tokens & estimated cost per query (`USD`)** | `trace.tokens.{input,output}`, `trace.estimated_cost_usd` | **$0 by default** ([docs/product.md](product.md) §1); any paid service or recurring cost requires owner approval | Sum of both online LLM calls + query embedding; reported in README ([docs/product.md](product.md) §7) |

### 1.2 Offline pipeline metrics
Raw data comes from the `ingestion_runs` collection in MongoDB ([docs/architecture.md](architecture.md) §4–§5).

| Metric | Source | Target / Budget | Notes |
|---|---|---|---|
| **Job counts & duration (`ingest`, `refresh`, `enrich`, `embed`)** | `ingestion_runs.{job,processed,skipped,failed,duration_s}` | Bounded by TMDB rate limits (`feat-008` Q3), laptop/host CPU (`feat-010` Q4), and LLM rate limits (`feat-011` Q1) | `skipped` verifies idempotency (`source_hash`, `prompt_version`, `embedding_model`) |
| **Enrichment cost per 1,000 profiles (`USD` & tokens)** | `ingestion_runs` (`enrich` job) | Measured in `feat-011` Q1; must fit zero-cost / owner-approved small spend for 5–20k movies | Recorded before running full-corpus enrichment |
| **Catalogue coverage & poster completeness** | `movies` collection / `feat-008` Q5–Q6 | ES, US and BO flat-rate movie counts per provider; `%` with English overview, keywords, reviews, and `poster_path` | Answers whether BO launches (`Q2`) and how to handle missing posters (`Q13`) |
| **Availability freshness & daily churn** | `movies.availability_updated_at` / `feat-008` Q7 | Refreshed daily ([docs/product.md](product.md) §6); every result shows its `availability_updated_at` (P6) | Daily titles added/removed in `feat-008` Q7 set the re-ingest schedule (`Q12`) |

### 1.3 Eval & quality metrics
Raw data comes from `evals/` (protected by the `tests-approved` PR gate) and `eval_runs` ([docs/product.md](product.md) §3 & §7, [docs/architecture.md](architecture.md) §6).

| Eval suite | What it checks | Gate / Target | When it runs |
|---|---|---|---|
| **Deterministic product-rule evals** | P1 (streamable flat-rate in country/provider), P3 on constraints as applied (runtime, max intensity, avoid), P4 (prompt ≤ 500 chars), P2 pitch length (≤ 350 chars), real catalogue IDs (no invented movies), valid output schema | **100% pass in CI** ([docs/product.md](product.md) §7) | Every CI run once the end-to-end slice exists |
| **Constraint extraction eval (P3)** | How accurately step 2 extracts structured filters over the closed vocabulary (`Q11`) from free text, including non-English prompts (`Q9`), on golden queries | Recorded baseline; tracked on prompt/model changes | Offline eval (`evals/`) |
| **Retrieval `precision@5`** | Relevance of top candidates on 30–50 owner-labelled mood queries | Recorded baseline; tracked on profile/embedding changes | Offline eval (`evals/`) |
| **Pitch quality eval (P2, ADR 0001)** | LLM-as-judge calibrated against owner labels: facts grounded in movie data, about the movie never the user, no spoilers, ≤ 350 chars | Recorded baseline; tracked on prompt/model changes | Offline eval (`evals/`) |
| **Emotional profile quality** | Owner-rated sample of enriched movie profiles ([docs/architecture.md](architecture.md) §4) | Checked in the profile design feature (`feat-012`) before enriching the full corpus | Offline sample review |

### 1.4 Spike baselines (`feat-008`…`011`)
Each spike records its measurements in `docs/spikes/NN-slug.md` and updates the summary row below at `/handoff`, so `feat-012` (architecture refinement) and the README have all numbers in one place.

| Spike | Key metrics to record | Measured value |
|---|---|---|
| `feat-008` (TMDB & providers) | Rate limit (req/s), time to ingest 20k movies, flat-rate movie count per provider in ES / US / BO, `%` missing `poster_path`, daily provider churn | *Pending `feat-008`* |
| `feat-009` (Atlas vector search) | Free-tier storage for 20k docs (384-d vs 768/1024-d), pre-filter support (`streamable` + `runtime` + `_id` + `intensity` + `content_warnings`), `$vectorSearch` `p50` / `p95` ms, index ready time in `atlas-local` | *Pending `feat-009`* |
| `feat-010` (Embedding runtime) | Candidate models & dimensions, image size (MB), RAM (MB), cold start (s), query `p50` / `p95` ms, time to embed 20k profiles on CPU, viable free host tier | *Pending `feat-010`* |
| `feat-011` (Runtime LLM) | Provider & model comparison (Gemini free tier vs low-cost OpenAI), rate limits (RPM/TPM/RPD), tokens & USD per query (2 calls) and per 1,000 profiles, structured-output pass/retry rate on 10 queries (≥3 non-English), call `p50` / `p95` ms | *Pending `feat-011`* |

---

## 2. Process & Harness Metrics (`/handoff` Log)

Tracks whether the harness catches issues before they reach the owner and how each task went (ADR 0004).
- **Rule:** when a task reaches `status: "done"` at `/handoff`, add its row at the top of the table below (newest first). `tests/harness/test_harness.py` checks that every `done` item in `feature_list.json` has a row here.
- **Columns:**
  - **Stop-gate blocks:** times `stop_gate.py` blocked a turn during the task (`0` when `uv run poe check` passed before stopping).
  - **Reviewer (rounds / findings):** reviewer rounds run and findings per round (e.g. `2 (12 + 2)` = 12 in round 1, 2 in round 2; `1 (0)` = clean on round 1).
  - **Escaped / owner fixes:** issues found after `/handoff` or during owner PR review (`0` when merged without fixes; owner may also note review time).

| ID | Type | Date | Machine · Tool | Stop-gate blocks | Reviewer (rounds / findings) | Escaped / owner fixes | Outcome & notes |
|---|---|---|---|---:|---|---:|---|
| `feat-006` | `chore` | 2026-11-13 | Mac · Antigravity | 0 | 1 (0) | 0 | Added `docs/metrics.md` (online, offline, eval, spike baseline and `/handoff` process metrics), wired `/handoff` + `AGENTS.md` + `docs/workflow.md`, and enforced per-feature rows in `tests/harness/test_harness.py`. |
| `feat-014` | `chore` | 2026-11-13 | Mac · Antigravity | 0 | 2 (2 + 0) | 0 | Validated harness with `validate-harness.mjs` (`60/100` → `92/100`); added `init.sh`, `feature_list.json` `description` check, and aligned `AGENTS.md` headings. |
| `feat-013` | `chore` | 2026-11-13 | Windows · Claude Code | 0 | 2 (7 + 3) | 0 | Recorded owner decisions Q8–Q11, posters, zero-cost budget, and provider-neutral LLM spike across product, architecture and spike docs. |
| `feat-005` | `chore` | 2026-11-13 | Windows · Claude Code | 0 | 2 (12 + 2) | 0 | Wrote `docs/architecture.md` v0 and spike question files `08`–`11`; added `feat-011` (`feat-012` is refinement). |
| `feat-007` | `chore` | 2026-11-12 | Mac · Antigravity | 1 *(intentional test)* | 1 (0) | 0 | Verified `feat-004` harness changes on Mac (live Stop hook block/allow, counter cleanup on revert, native `reviewer` subagent). |
| `feat-004` | `chore` | 2026-11-12 | Windows · Claude Code | 1 *(intentional test)* | n/a *(fixed reviewer diff)* | 1 *(piped commit slip, fixed in session)* | First Windows session: fixed CI git-state test, Windows UTF-8/BOM hook bugs, pre-commit ruff pin, and reviewer diff target; added Claude Code support (ADR 0003) and autonomous flow (ADR 0004). |
| `feat-000` | `feature` | 2026-11-12 | Mac · Antigravity | 0 | 1 (0) | 0 | End-to-end harness dry run: `/spec`, `prompt_validation.py` (P4), unit + acceptance tests, `/review`, `/defend` (`LEARNING.md`), ADRs `0001`–`0002`. |
| `feat-001` | `chore` | 2026-11-11 | Mac · Antigravity | 0 | n/a *(bootstrap)* | 3 *(caught in `feat-001`/`004`, logged in `harness-log.md`)* | Repo skeleton, `pyproject.toml`, layers, `poe check`, pre-commit, CI, core harness files (`AGENTS.md`, skills, `stop_gate.py`, `test_harness.py`). |
