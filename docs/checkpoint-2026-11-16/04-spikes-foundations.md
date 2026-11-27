# Part 4 · Spikes on the foundations: data source, database, embeddings

**Reading time:** about 25 minutes · [Back to the index](README.md) · Previous: [Part 3](03-the-architecture.md) · Next: [Part 5 · The LLM spike](05-spike-llm.md)

> [!NOTE]
> **Key ideas in this part**
> - A spike is a short, timeboxed experiment that answers a design question with real evidence. Its code is thrown away; its answers stay.
> - A spike result is a chain: **question → method → raw output → number in the report → conclusion → decision**. Any link can break.
> - For this checkpoint, three independent checks re-traced these three spikes from the report back to the raw output files. Most numbers match. The weak links are in the **labels** ("measured" vs "estimated") and in **conclusions bigger than the data**.
> - Evidence has to come from the right source: a storage rule belongs to the terms, not to an HTTP header.

---

## 1. What a spike is, and why we ran five

The architecture draft (13 Nov) listed questions that nobody could answer from documentation alone: *Does TMDB have streaming data for Bolivia? Does MongoDB's free tier support the filters we need? Which LLM is accurate enough and cheap enough?* Each question could change the design, so each got a spike:

- **Timeboxed:** about 2 sessions each.
- **Questions first:** the question file is written before any experiment ([example](../spikes/09-atlas-vector-search.md#questions--findings)).
- **Throwaway code** in `spikes/`, never in `src/`.
- **Evidence:** the command, the raw output (usually a `report.json`), and what the answer changes in the architecture.

| Spike | Question in one line | Run on | Tool |
|---|---|---|---|
| [08 · TMDB and providers](../spikes/08-tmdb-and-providers.md) | Can we use TMDB, how fast, and does it cover ES, US and BO? | Mac | Antigravity |
| [09 · Atlas vector search](../spikes/09-atlas-vector-search.md) | Does the free database tier fit our data and our filters? | Mac | Antigravity |
| [10 · Embedding runtime](../spikes/10-embedding-runtime.md) | Which embedding model, and can it run inside a free container? | Mac | Antigravity |
| [11 · Runtime LLM](../spikes/11-runtime-llm.md) | Which LLM, how much, how reliable, which framework? | Windows | Claude Code |
| [16 · Recommendation quality](../spikes/16-recommendation-signals-and-ranking.md) | Which movies, which signals, which profile, which ranking? | Windows | Claude Code |

This part covers the first three. [Part 5](05-spike-llm.md) and [Part 6](06-spike-recommendation-quality.md) cover the other two.

## 2. How to read a spike critically

Use these six questions on any spike, ours or someone else's:

1. **What was the question, and what decision depends on it?**
2. **What data was it measured on?** Real or synthetic? How many items? Chosen how?
3. **Is the number in the report the same as in the raw output?** And is it labelled honestly: measured, estimated, or copied from a web page?
4. **Is the conclusion bigger than the evidence?** Watch for extrapolations ("× 7 for a week"), and for examples picked to support the conclusion.
5. **How reversible is the decision?** A wrong embedding model costs 20 minutes to re-run. A wrong reading of a licence can cost the whole data source.
6. **What later work re-checks it?** A shaky number that the next slice measures again is fine. A shaky number that nothing re-checks becomes a hidden assumption.

> [!TIP]
> This is the same discipline as a production root-cause analysis, which you already know: trust the logs, not the summary in the incident channel.

## 3. Spike 08 · TMDB: terms, rate limits and streaming coverage

**Why it mattered.** TMDB is the only free source of movie data *and* streaming availability (which comes from JustWatch through TMDB). If it doesn't cover Bolivia, or forbids what we want to do, the product changes.

**What it did.** A script ([probe_tmdb.py](../../spikes/08-tmdb/probe_tmdb.py)) called TMDB about 1,000 times: the 500 most popular movies with all their details, a deep sample of 480 streamable movies, the provider lists for each country, and two snapshots one day apart.

**Main results.**

| Topic | Result |
|---|---|
| One call per movie | `append_to_response` returns details, keywords, credits, reviews and providers for **all** countries in **one** request |
| Speed | 25 requests per second with 10 parallel workers, zero "too many requests" errors. About 14 minutes for 20,000 movies. |
| **A trap in the API** | The search endpoint (`/discover`) with "provider = Apple TV Store" and "type = subscription" returns movies that are on *some other* service by subscription and only *rentable* on Apple. The two conditions are not joined. Using it to decide "streamable on service X" would break the first product rule. Only the per-movie providers endpoint is safe. |
| Coverage | Of the 500 most popular movies, 73% are on a subscription in the US, 67% in Spain, 62% in Bolivia. **Bolivia is usable.** |
| Data quality | No sampled movie lacked a poster or an English overview; 95% had keywords. (Spike 16 later confirmed it at scale: 51,414 of 51,527 streamable movies have both.) |
| Change rate | In 24.5 hours, 2–3% of the popular 500 changed providers in Spain and the US, 0.6% in Bolivia |

**What it changed.** Read availability only from the per-movie endpoint. Keep all three countries. Drop movies without a poster. Never store user reviews.

**How sure are we?** (from the independent check)

| Claim | Verdict | Why |
|---|---|---|
| The `/discover` trap | **Solid** | 5 of 5 movies confirmed; pure rent/buy stores also show thousands of "subscription" results |
| Speed, data quality, popular-500 coverage | **Solid** | Numbers match the raw output |
| Per-service catalogue sizes (e.g. "Filmin 11,820") | **Weak** | They come from the very `/discover` query the spike itself showed is wrong. They are upper limits, not counts. The same numbers are copied in [metrics.md](../metrics.md). |
| "~10–15% stale within a week", "over 90% of additions are rotations", "1–5 new films a day" | **Not supported** | One 24-hour difference multiplied by 7. The "rotations" check compared a popularity top-100 list with the popular-500 list it was drawn from, which is nearly circular. Most "changes" were small services (one service, Tivify, was 7 of the 11 changes in Spain). The follow-up task re-measures churn properly. |
| "Storing metadata is allowed" (from a `Cache-Control` header) | **Wrong evidence** | See below. |

> [!WARNING]
> **The storage finding.** The spike used an HTTP caching header as evidence about storage rules. A header tells a browser how long to keep one response; it says nothing about what an app may store. The rules are in TMDB's [API terms](https://www.themoviedb.org/api-terms-of-use) (last updated 20 Oct 2023): section 1.C forbids caching *"for longer than 6 months, any information obtained through or from TMDB or the TMDB APIs"*, and section 3 gives the exact attribution notice. So the ingest must re-fetch metadata at least every 6 months, and the notice must use section 3's wording. The [review](review.md#finding-1-the-tmdb-spike-took-its-storage-rule-from-the-wrong-source) suggests what to do.

There's one more small lesson here: the committed script is not exactly the version that produced the saved output (the snapshot is missing a field the script writes, and the request counts differ). A spike's evidence is only reproducible if the code and the output come from the same run.

## 4. Spike 09 · MongoDB Atlas: free tier and vector search

**Why it mattered.** The free tier (called M0) has 512 MB of storage. Vector search needs filters ("only on Netflix Spain", "under 90 minutes", "not these IDs"). If the filters don't combine, or the data doesn't fit, the design changes.

**What it did.** A script ([probe_atlas.py](../../spikes/09-atlas/probe_atlas.py)) generated **20,000 synthetic movies** (fake data with random vectors), loaded them into a real free-tier cluster and into the local Docker image, built a vector index, and ran filtered searches.

**Main results.**

| Topic | Result |
|---|---|
| Storage | 20,000 movies with 384-number vectors use about 109 MB on disk: comfortable |
| Filters | All five filters (`streamable`, `runtime`, excluded IDs, `intensity`, `content_warnings`) work **together** in one search, and every result obeyed them |
| A rule to remember | Every field used in a filter must be declared in the index definition, or the query fails with an error |
| Excluded IDs | A "not in this list" filter worked with lists of up to 5,000 IDs |
| Local image | `mongodb-atlas-local` runs vector search on the Mac, with the same top results as the cloud |
| Speed | Median 61 ms and p95 121 ms per filtered search in the cloud, with 40 results |
| Driver | Use PyMongo's own async client; the older Motor library is deprecated |

**How sure are we?** The independent check rebuilt the same synthetic data offline (the script uses fixed random seeds) and computed the exact nearest neighbours. **Atlas's top 3 matched the exact answer**, and the filter check was not trivial (3 excluded IDs would otherwise have been in the top 40). So the core claims hold. The caveats:

| Claim | Verdict | Why |
|---|---|---|
| 384-d fits comfortably; filters combine | **Solid** | Measured and independently recomputed |
| The storage table for 768-d, 1024-d and compact "binary" vectors | **Weak** | Mixes measured values with estimates in one column. Four disk figures (~52, ~78, ~95, ~240 MB) appear nowhere in the raw output. The one measured 768-d value (292 MB, 57% of the limit) is left out. The vector index size is a formula, never measured. |
| "Bit-for-bit identical" cloud vs local | **Overstated** | Only the top 3 results were saved, not all 40. The error messages differ slightly. |
| Latency 61/121 ms | **Solid, but narrow** | Warm queries, 40 results (we now plan 150), random vectors. Two of the excluded-ID tests took 622 ms and 998 ms (probably cold queries) and were left out of the reported "72–138 ms" range. |
| "Indexes can be updated and dropped from code" | **Not shown** | Errors on drop were silenced; the updated index was never checked |
| Local image works on Windows | **Not tested** | Still an open question |

The local image was run with the `latest` tag (MongoDB 9.0) while the cloud runs 8.0. Pinning the image version would make tests repeatable.

## 5. Spike 10 · Embeddings: which model, and how heavy

**Why it mattered.** The API must turn your text into a vector at search time. Options: a big library (PyTorch), a light one (`fastembed`, which uses ONNX Runtime), or a paid API. The free hosting tiers have ~512 MB of memory.

**What it did.** A script ([probe_embedding.py](../../spikes/10-embedding/probe_embedding.py)) embedded 200 popular movies' TMDB text with each option and measured size, memory, start time and speed, and ran 10 mood queries.

**Main results.**

| Measure | `fastembed` (chosen) | PyTorch |
|---|---|---|
| Added size | ~212 MB | ~988 MB |
| Memory at query time | 279 MB | 509 MB |
| Time per query (median) | 5 ms | 10 ms |
| Same vectors? | Yes: cosine similarity 0.999999 between the two | |

Decision: `fastembed` with `BAAI/bge-small-en-v1.5` (384 numbers per vector), running inside the API process. A multilingual model was rejected; the LLM translates non-English requests instead.

**How sure are we?**

| Claim | Verdict | Why |
|---|---|---|
| `fastembed` is much lighter and gives the same vectors | **Solid** | Numbers match the raw output |
| "+212 MB image" | **Estimate** | It's the size of the installed packages plus the model on a Mac, not a built Linux container. No container was built. |
| "20,000 movies in 12 minutes" | **Extrapolated** | Computed from 200 movies. Spike 16 later **measured** 14,478 real movies in 17 minutes on Windows (about 24 minutes for 20,000). |
| "10 of 10 queries free of horror leakage" | **False** | The handoff says it, but the raw output has horror films in the top 5 of three queries |
| "The multilingual model is worse in English" | **Not supported** | Judged by eye on 3 of 10 queries. On another query the multilingual model looked better (Interstellar, Dune, Project Hail Mary, The Matrix). |
| The hosted Gemini option | **Never ran** | There was no API key; the numbers are copied from documentation |
| Free hosting fits | **Unsourced** | No quotes saved, nothing deployed |

Does this change the decision? **No**, for two reasons. The memory and size advantage is real and measured. And the decision is cheap to reverse: changing the model means re-embedding for about 20 minutes. But [decision record 0007](../decisions/0007-embeddings-fastembed-profile-template.md) repeats "worse on English" and "fits 512 MB" as facts, and those should be re-checked when the real container is built.

## 6. The pattern across the three spikes

These three spikes ran on the Mac with Antigravity. Each one's reviewer reported **"No findings"**. The independent checks found:

- **The raw numbers are mostly right.** When the report quotes a measured value, it usually matches the output file.
- **Labels are unreliable.** Estimates sit next to measurements in the same table with the same confidence. Some figures don't exist in any output.
- **Conclusions grow on the way to the summary.** The handoff and the metrics file restate the spike's claims more strongly than the spike does ("10/10", "verified").
- **Self-graded examples.** "5/5 relevant" was the agent grading its own results, by eye, without a rubric.
- **Not-run options presented as compared.**

And yet most **decisions** survived, because later work re-measured the important numbers (spike 16 re-measured embedding speed, the size of the catalogue and the corpus; the walking skeleton will test the database on Windows and the new filters). The exception is the storage rule, which nothing re-checks until the ingest design applies the 6-month limit.

The [review](review.md) turns this pattern into concrete advice.

---

### Questions to think about

- The `/discover` trap was a great finding. Why did the same spike then use `/discover` numbers for catalogue sizes? What would have caught it?
- Spike 09 used random vectors. Which of its conclusions does that weaken, and which does it not affect at all?
- Rank the five claims marked "weak" or "not supported" above by how much damage they could do if wrong. Use the "how reversible" question.
- How would you redesign the churn measurement so its result can't be circular?

[Back to the index](README.md) · Previous: [Part 3](03-the-architecture.md) · Next: [Part 5 · The LLM spike](05-spike-llm.md)
