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

## feat-018 · Walking skeleton: search end to end → in feature_list.json (2026-11-16)
- **Type:** feature · **Stories:** US1, US2, US3 · **Depends on:** feat-012, feat-016 · **Spec:** `docs/specs/18-walking-skeleton.md`
- **Description:** in `feature_list.json`. This section holds notes for `/spec`, added after the [2026-11-16 checkpoint](checkpoint-2026-11-16/review.md) (owner, 2026-11-21).
- **Notes:**
  - **Split it** ([review, finding 7](checkpoint-2026-11-16/review.md#finding-7-keep-the-walking-skeleton-thin)). One possible cut:
    - (a) the end-to-end path with fake LLM and embedder ports, the real local database, all response states, and the first deterministic evals;
    - (b) the real LLM adapter: Pydantic AI, the retry with the error fed back verified on the real model, cost in the trace;
    - (c) the real embedder and the first latency numbers.
    - **Decided** (owner, 2026-11-22 on the Mac, 2026-11-24 on Windows): four parts, in this order: part 1 in-memory (`feat-018`), part 2 local Atlas (`feat-030`), part 3 real embedder (`feat-028`), part 4 real LLM (`feat-029`).
  - **The owner writes part of it** ([review, finding 4](checkpoint-2026-11-16/review.md#finding-4-the-learning-record-misses-the-ai-engineering-half)): for example the step-4 checks (re-check every rule by value) with their unit tests. The agent reviews that code.
    - **Changed** (owner, 2026-11-22): the agent writes the slice; then a `/defend` session, and the owner refactors or extends a module.
  - **Verify, don't assume** ([review, finding 2](checkpoint-2026-11-16/review.md#finding-2-some-weak-numbers-became-facts-in-the-decision-records)):
    - query-embedding time end to end (the 5 ms figure is a warm, in-process number from the Mac);
    - the five tested filters together with a large exclusion list, plus the new ones (`year`, `original_language`, the age ratings, and the audience rule with its null case);
    - creating, updating and dropping the search index from code (spike 09 never verified update and drop);
    - that `query_embed` adds BGE's query instruction (spike 10 embedded queries with `embed`).
  - **Pin the `mongodb-atlas-local` image** to a version close to the cloud's (M0 runs MongoDB 8.0; spike 09 used `latest`, which was 9.0).
  - **Start from the v1 intent.** Genre, people and content fields will be added after spike feat-026 (question 7) decides how (owner, 2026-11-24: the list is not frozen); don't add them here.
  - The seed uses spike 16's ~300 movies in a local database, so the skeleton doesn't wait for the ingest task.

## feat-030 · Walking skeleton, part 2: search on local Atlas → in feature_list.json (2026-11-24)
- **Type:** feature · **Stories:** US1, US2, US3 · **Depends on:** feat-018 · **Spec:** `docs/specs/30-atlas-local-search.md` (draft)
- **Description:** in `feature_list.json`; the detail is in the draft spec. It takes over the database half of the original feat-018: the verification list above (filters, index lifecycle, image pin), the seed of spike 16's 300 films, and Q4 on Windows.

## feat-028 · Walking skeleton, part 3: real embedder → in feature_list.json (2026-11-24)
- **Type:** feature · **Stories:** US1 · **Depends on:** feat-030 · **Spec:** `docs/specs/28-real-embedder.md` (not written yet)
- **Description:** the in-process `fastembed` (`BAAI/bge-small-en-v1.5`, 384-d) `Embedder` adapter in `infra`.
- **Notes** (from the Mac `/spec` draft, 2026-11-22):
  - Verify that `query_embed` adds BGE's query instruction ([checkpoint, Part D](checkpoint-2026-11-16/review.md#part-d--smaller-notes)).
  - Embed the 300 seeded profiles with `template(profile)` (ADR 0007), replacing part 2's fake vectors.
  - Measure cold-start and warm query-embedding time end to end; the 5 ms figure is warm and in-process on the Mac ([checkpoint, finding 2](checkpoint-2026-11-16/review.md#finding-2-some-weak-numbers-became-facts-in-the-decision-records)).

## feat-029 · Walking skeleton, part 4: real LLM → in feature_list.json (2026-11-24)
- **Type:** feature · **Stories:** US1, US2 · **Depends on:** feat-028 · **Spec:** `docs/specs/29-real-llm.md` (not written yet)
- **Description:** the `LanguageModel` adapter in `infra` with Pydantic AI (`OpenAIChatModel`, `gpt-6-luna`, `NativeOutput`, `reasoning_effort="none"`; ADR 0006).
- **Notes** (from the Mac `/spec` draft, 2026-11-22, and the Windows review, 2026-11-24):
  - The step-2 and step-6 check functions from part 1 (`domain`) run as output validators raising `ModelRetry`: one retry with the error fed back, verified on the real model.
  - Real token counts and cost in the `trace`; the deterministic evals from part 1 re-run on the real model.
  - The first end-to-end latency numbers (architecture Q7).
  - A small paid spend (cents), reported in the handoff.

## feat-031 · Content limits in the search → in feature_list.json (2026-11-24)
- **Type:** feature · **Stories:** US2 · **Depends on:** feat-026, feat-029 · **Spec:** `docs/specs/31-content-limits.md` (not written yet)
- **Description:** in `feature_list.json`; placed right after `feat-026` (owner, 2026-11-24). The detail is in the Proposed entry it came from, below.

## feat-020 · Ingest and daily refresh
- **Type:** feature · **Stories:** US1 · **Depends on:** feat-030, feat-026 (the corpus gate may change) · **Spec:** `docs/specs/20-ingest-refresh.md`
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
  - "Films missing from every region's crawl get `streamable: []`" was checked against `/watch/providers` in feat-017 (spike 16 Q1): it held for all 32 G7 leavers, and 2 of 325 sampled leavers were `/discover` misses (a hidden film, never a wrong one). Decide at `/spec` whether a periodic `/watch/providers` re-check of `streamable: []` films is worth its calls.
  - Record admitted and departed counts per run in `ingestion_runs`: feat-017's rates (≈ 24.5 admissions and ≈ 6 departures a day for G7) come from one 5.3-day window.
  - **Metadata re-fetch policy:** for recent films (keywords and certifications fill in after release), plus a **periodic full re-ingest**, as spike 08 Q1 expects (≈ 14.5k calls, ≈ 10 min at 25 req/s).
  - **Provider aliasing (P1 risk)** of ad tiers and channels onto a parent service (e.g. ES:119/ES:2100):
    - Aliases are applied only when writing `streamable`, and only if catalogue overlap is measured as near-identical: the share of films listed on the alias ID that also list the parent.
    - Otherwise, ask the owner (P7).
    - Spike 08 Q5 offered aliasing only as an option, without evidence.

## feat-021 · Enrich and embed the full corpus
- **Type:** feature · **Stories:** US1 · **Depends on:** feat-019, feat-020 · **Spec:** `docs/specs/21-enrich-embed.md`
- **Description:**
  - Enrich the films the corpus gate admits (≈ 14.5k with G7; spike feat-026 may change the gate) with `gpt-6-luna`, through the Batch API or normal calls (see Notes), and embed `template(profile)` (ADR 0006, 0007).
  - Build the Atlas M0 vector index with every filter path declared.
  - Re-run only when `source_hash`, `prompt_version` or the model changes.
- **Notes:**
  - First run on M0 at full scale, so it **measures `$vectorSearch` latency at K = 150 and sets `numCandidates`** (Q7).
  - Check whether Pydantic AI supports the Batch API, or whether the batch job uses the `openai` SDK directly.
  - **Batch or not** (owner concern, 2026-11-19): Batch fits the request/response `LanguageModel` port badly, and each provider's batch API works differently (OpenAI, Anthropic and Google all discount batch jobs by about 50%). Options:
    - (a) **skip Batch in the MVP:** normal calls through the same port, about $1 more, once, for 14.5k films (agent's recommendation);
    - (b) give enrichment **its own port** ("write profiles for these movies"), with a direct adapter and a batch adapter.
    - Decide at `/spec`. Profiling is paid again for every film each time the profile prompt changes, so the corpus size multiplies every prompt iteration.
  - **Exact vs approximate search** (checkpoint discussion, 2026-11-20): measure `exact: true` against approximate search at K = 150, especially with strict filters (for example one Bolivian service plus kids). At about 15k films, exact search may be fast enough and never misses. Also measure the approximate index's recall against exact.

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
    - the extraction eval only needs step 2, so it can come earlier (after feat-029, the real LLM);
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
- **Spike checklist for the reviewer, and cross-tool review** (chore, from the [2026-11-16 checkpoint review](checkpoint-2026-11-16/review.md#finding-3-the-reviewer-cant-catch-spike-errors-and-reviews-with-the-same-model)): add a spike/design-doc section to `.agents/agents/reviewer.md` (every number traced to a raw output, measured/estimated/documented labels, extrapolations and not-run options marked, terms claims quoted, handoff says no more than the report), and a rule that spikes and design documents are reviewed with the other machine's tool before merge. **→ in `feature_list.json` as `feat-027` (owner, 2026-11-21).**
  - Evidence from feat-017: the reviewer got this checklist in its prompt (trace each number to an output file, re-check derived arithmetic, labels and sample sizes, script logic). It recomputed every figure from the raw data and found 8 real issues, including one that contradicted an owner decision. The prompt is quoted in `docs/handoffs/feat-017.md`.
- **Clean up stale and duplicated numbers** (chore, from the [checkpoint review, finding 8](checkpoint-2026-11-16/review.md#finding-8-the-same-numbers-live-in-too-many-places)): fix the stale lines it lists (`docs/metrics.md` §1.3–§1.4, README stack and status, spike 11 and 16 summaries), and reduce `docs/metrics.md` §1.4 to links to the spike reports. **→ in `feature_list.json` as `feat-027` (owner, 2026-11-21).**
- **"5 more" reuses the first intent** (checkpoint discussion, 2026-11-19): asking again for more results (US3) currently repeats both LLM calls (about $0.0007 and 5–6 s). Sending the first `QueryIntent` back with the request, or caching it briefly, skips LLM call 1 and roughly halves the time and cost. It changes the API contract slightly; a candidate for the web UI task or a later slice.
- **Golden set of 30–50 requests with expected filters** (owner work, from the [checkpoint review, finding 5](checkpoint-2026-11-16/review.md#finding-5-evaluation-is-the-real-bottleneck-start-the-golden-set-early)): start early, because it needs the owner's time; it feeds the constraint-extraction eval right after the walking skeleton, and later the ranking evals.
- **Walking skeleton Slice B (`feat-028`): real `fastembed` `Embedder` adapter and seed embeddings** (proposed split from `feat-018` `/spec`, 2026-11-22): implement the in-process `fastembed` (`BAAI/bge-small-en-v1.5`, 384-d) `Embedder` adapter in `infra`, verify that `query_embed` prefixes BGE's query instruction (Checkpoint Part D), embed the ~300 spike-16 seed profiles using `template(profile)` (ADR 0007), and measure cold-start and warm query-embedding latency end to end (Checkpoint Finding 2). Depends on `feat-018`. **→ in `feature_list.json` as `feat-028`, part 3, after `feat-030` (owner, 2026-11-24).**
- **Walking skeleton Slice C (`feat-029`): real Pydantic AI `gpt-6-luna` `LanguageModel` adapter and end-to-end live search** (proposed split from `feat-018` `/spec`, 2026-11-22): implement the `LanguageModel` adapter in `infra` with Pydantic AI (`OpenAIChatModel`, `gpt-6-luna`, `NativeOutput`, `reasoning_effort="none"`, ADR 0006), verify `ModelRetry` with validation error feedback on the live model for steps 2 and 6, populate real token counts and USD cost in `trace`, and measure the first end-to-end search latency numbers (architecture Q7). Depends on `feat-018`, `feat-028`. **→ in `feature_list.json` as `feat-029`, part 4 (owner, 2026-11-24).**
- **Content limits in the search: genre, director, main cast, keyword flags** (owner requirement, 2026-11-24: "those additional constraints are added"; the v1 list is not frozen, [ADR 0005](decisions/0005-closed-vocabulary-mirror-schema.md)): build what spike feat-026 question 7 recommends.
  - New `QueryIntent` fields and intent-prompt rules (including when a genre is *required*, "only horror", and when only *preferred*, "an action movie"); the mirror fields (`genres` and `credits` are already in the data model, §5); their pre-filter paths and step-4 checks; content in the vector text if the spike recommends it.
  - Extend the deterministic evals, and add the content requests to the extraction eval.
  - Suggested position: right after `feat-026`, since it needs the spike's answer and the real LLM (`feat-029`). Depends on `feat-026`, `feat-029`. **→ in `feature_list.json` as `feat-031`, right after `feat-026` (owner, 2026-11-24).**
- **References in specs are links, and the query steps get headings** (from the owner's feat-018 spec review, 2026-11-24): the owner couldn't find "the deterministic step-4 checks" in `docs/architecture.md`. They are there (§3, step 4, *Check and rank candidates*), but the steps are a numbered list with no headings, and the spec used a different name. Proposal: (1) give each query step its own heading in architecture §3, so links can point to it and GitHub's outline lists it; (2) a `/spec` rule: link every reference to another document to its section on first use, using the name that document uses; (3) keep one source per fact (architecture for how, product for rules); learning guides and specs link to it, never copy it. **→ in `feature_list.json` as part (4) of `feat-027` (owner, 2026-11-24).**
