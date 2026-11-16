# Backlog

**What this file is:** the later MVP items, in the owner's priority order, with full detail.
- `feature_list.json` holds only the active window: the item in progress and the next few `todo` items.
- **Moving an item into the window:**
  - Its JSON entry gets the same id, type, stories, dependencies and spec path, plus a one-paragraph description ending with `Detail: docs/backlog.md#<id>`.
  - Its section here **stays**, marked `→ in feature_list.json (<date>)`, until the item is done, so no detail is lost.
  - When `/spec` writes the spec, it copies the section's **Notes** into the spec's design notes or open questions.
- **Only the owner orders "Ordered".** Agent ideas and proposed splits go under **Proposed**. The refill (handoff) and the start rule never take items from Proposed.

**Why it exists** (owner, 2026-11-16): keep `feature_list.json` small and readable without losing detail just to meet a line limit. Detail and priority matter more than counts.

## Ordered (owner's priority; skeleton first, then deepen each stage, feat-012)

---

## feat-020 · Ingest and daily refresh
- **Type:** feature · **Stories:** US1 · **Depends on:** feat-018 · **Spec:** `docs/specs/20-ingest-refresh.md`
- **Description:**
  - The daily `/discover` crawl of ES/US/BO flat-rate films, with **G7 admission** (ADR 0008, pinned WR constants) and the admission data checks (overview, poster, `runtime > 0`, ≥ 1 genre).
  - One TMDB bundle per admitted film; Wikidata signals by TMDB ID.
  - Availability refresh with `unstreamable_since`; refresh of popularity, votes and `quality_score` from the crawl.
  - The curated provider list per country (spike 08 Q5).
  - `ingestion_runs` and idempotency.
- **Notes:**
  - **Likely split at `/spec` time:**
    - (a) the daily availability refresh over stored films, observable through P1/P6 in search;
    - (b) crawl + G7 admission + bundle fetch.
  - Confirm here whether "films missing from every region's crawl get `streamable: []`" holds against `/watch/providers` (architecture §4).
  - **Metadata re-fetch policy:** for recent films (keywords and certifications fill in after release), plus a **periodic full re-ingest**, as spike 08 Q1 expects (≈ 14.5k calls, ≈ 10 min at 25 req/s).
  - **Provider aliasing (P1 risk)** of ad tiers and channels onto a parent service (e.g. ES:119/ES:2100):
    - Aliases are applied only when writing `streamable`, and only if catalogue overlap is measured as near-identical: the share of films listed on the alias ID that also list the parent.
    - Otherwise, ask the owner (P7).
    - Spike 08 Q5 offered aliasing only as an option, without evidence.

## feat-021 · Enrich and embed the full corpus
- **Type:** feature · **Stories:** US1 · **Depends on:** feat-019, feat-020 · **Spec:** `docs/specs/21-enrich-embed.md`
- **Description:**
  - Enrich the ≈ 14.5k G7 films with the OpenAI Batch API (≈ $1.03) and embed `template(profile)` (ADR 0006, 0007).
  - Build the Atlas M0 vector index with every filter path declared.
  - Re-run only when `source_hash`, `prompt_version` or the model changes.
- **Notes:**
  - First run on M0 at full scale, so it **measures `$vectorSearch` latency at K = 150 and sets `numCandidates`** (Q7).
  - Check whether Pydantic AI supports the Batch API, or whether the batch job uses the `openai` SDK directly.

## feat-022 · Ranking and quality evals
- **Type:** feature · **Stories:** US1, US2 · **Depends on:** feat-021 · **Spec:** `docs/specs/22-ranking-evals.md`
- **Description:**
  - The hybrid step-4 re-score (ADR 0008), with a fixed-scale similarity and `collection_id` dedupe.
  - 30–50 owner-labelled golden queries to tune the weights and the scale.
  - Fix the "easy request → demanding classic" failure.
  - The constraint-extraction eval (P3).
  - The **pitch-quality eval**: an LLM judge calibrated on the owner's labels (owner, 2026-11-16).
- **Notes:**
  - **Likely split at `/spec` time:**
    - the extraction eval only needs step 2, so it can come earlier (after feat-018);
    - the hybrid score with the golden set;
    - the pitch-quality eval.
  - The judge disagreed with itself on 26% of items in feat-016, so measure judge agreement before trusting small differences.

## feat-023 · Web UI
- **Type:** feature · **Stories:** US1, US2, US3 · **Depends on:** feat-018 · **Spec:** `docs/specs/23-web-ui.md`
- **Description:**
  - A thin React client: mood form, country and services pickers (curated list), results with posters, pitches, services and availability date.
  - Attribution (P5); age and privacy notes (product §2, Q14).
  - The "couldn't apply" note for unmapped constraints; mobile-friendly.
- **Notes:** UI tooling and hosting are decided here (Q10).

## feat-024 · MCP server
- **Type:** feature · **Stories:** US4 · **Depends on:** feat-018 · **Spec:** `docs/specs/24-mcp-server.md`
- **Description:** an MCP tool over the `SearchMovies` use case. It returns the same structured results as the API, with links, notes and attribution.

## feat-025 · Deploy, README and demo
- **Type:** feature · **Stories:** — · **Depends on:** feat-022, feat-023, feat-024 · **Spec:** `docs/specs/25-deploy-readme.md`
- **Description:**
  - Deploy the API, the daily job and the UI on free tiers (Cloud Run or ACA), and measure Q7 p95 from the host.
  - README with the architecture diagram, eval results, cost per query and design decisions; a 3-minute demo (product §7).

---

## Proposed (not yet ordered by the owner)

Agent ideas and proposed splits wait here until the owner moves them into **Ordered**. Never built from here.

- **Second OpenAI model behind Pydantic AI `FallbackModel`** (from ADR 0006): it would cover a single-model outage without changing provider. It would also change the outage behaviour defined in Q8, so it needs an owner decision before any slice includes it.
