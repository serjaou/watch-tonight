---
id: feat-009
type: spike
status: questions ready   # questions ready -> answered
timebox: 2 sessions
---
# Spike: Atlas free tier, vector-search pre-filters and the atlas-local image

## Why
Query step 3 (filtered vector search), the shape of `streamable`, the corpus size and the integration tests all depend on what Atlas supports for free. Architecture open questions Q3 and Q4.

## Questions
Each answer: the finding, plus evidence (docs link, command and output, or measurements).

1. **Free tier limits.** Storage, number of search/vector indexes, maximum vector dimensions. Does a 20k-movie corpus (document + one vector) fit, and with how much headroom?
   - *Changes:* corpus size.
2. **Pre-filters.** Can one `$vectorSearch` pre-filter combine:
   - "array field `streamable` contains any of a list of strings";
   - `runtime ≤ N`;
   - `_id` not in a list of up to ~50 IDs?

   How must those fields be indexed? Is there a limit on list sizes?
   - *Changes:* the `streamable` design, query step 3, US3 (`exclude_ids`).
3. **Local image.** Does the `mongodb/mongodb-atlas-local` Docker image run `$vectorSearch` with the same filters on the Mac (ARM) and on Windows (x86, Docker Desktop)? How long does a search index take to become queryable after creation?
   - *Changes:* integration tests (`poe test-all`), test setup and teardown.
4. **Python driver.** Is PyMongo's async API the current recommendation (vs Motor)? Can search indexes be created and updated from code?
   - *Changes:* the `infra` MongoDB adapter, index setup in the ingest job.
5. **Latency.** p50/p95 of one filtered vector search over ~20k documents on the free tier.
   - *Changes:* the p95 latency budget (open question Q7).

## How
- Throwaway script in `spikes/09-atlas/`: load 1–2k synthetic documents (random 384-d vectors, realistic `streamable` and `runtime`) into atlas-local and into a free-tier cluster, then run the filtered queries.
- Needs a free MongoDB Atlas account (owner) and `MONGODB_URI` in `.env`.
