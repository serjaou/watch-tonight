# Checkpoint review · 16 November 2026

**What this is:** an independent review of the project after its first six days, written by Claude Code (Opus 5.5) on the Windows laptop. It answers your two questions (can we trust the work done on the Mac, and what learning did we miss) and gives feedback and advice.
**Status:** frozen snapshot. It will not be updated; later decisions live in the usual places.
**Companion:** the [learning guide](README.md) explains everything this review refers to.

---

## Summary

- **Is our progress reliable?** Mostly yes. The decisions that shape the product rest on solid evidence, largely because the later spikes (run on Windows) re-measured the important numbers of the earlier ones (run on the Mac). The three Mac spikes have **mostly correct raw numbers, but unreliable labels and inflated conclusions**: estimates presented as measurements, a few figures that exist in no output file, and summaries stronger than the data.
- **The TMDB spike took its storage rule from the wrong source:** an HTTP cache header instead of the terms. The terms limit caching to 6 months and give an exact attribution notice. Both are small fixes, best made before the ingest pipeline is designed. ([Finding 1](#finding-1-the-tmdb-spike-took-its-storage-rule-from-the-wrong-source))
- **Re-reviewing everything done on the Mac is not worth it.** The risk sat in the spikes, and this review audited all three. The harness work is code covered by tests that run on both machines and in CI.
- **The reviewer agent is the weak gate.** On the Mac it reported "No findings" on all three spikes, and the audits found real problems in each. It reviews with the same model and with a code-oriented checklist. ([Finding 3](#finding-3-the-reviewer-cant-catch-spike-errors-and-reviews-with-the-same-model))
- **Learning:** the harness topics are well covered in your learning records; the AI-engineering topics (RAG, evals, structured output) are not covered at all, although that's where most of this stage's work was. ([Finding 4](#finding-4-the-learning-record-misses-the-ai-engineering-half))

**If you only do three things:**

1. Make the reviewer check spikes properly, and have spikes reviewed on the *other* machine's tool.
2. Spend one or two sessions with the [learning guide](README.md), then look at the spike-16 recommendations yourself and rate them.
3. Start the golden set: 30–50 realistic requests with the filters you expect.

---

## How this review was done

| What | How |
|---|---|
| Read | The brief, product, architecture, all 8 decision records, all 5 spike reports, the backlog, the harness files and skills, the handoffs, metrics and harness log |
| Independent audits of the three Mac spikes | Three separate read-only agents, one per spike (TMDB, Atlas, embeddings). Each re-traced the report's numbers to the raw output files and read the probe scripts. The Atlas audit rebuilt the synthetic data offline (the script uses fixed random seeds) to check the search results. The TMDB audit read TMDB's live terms pages. They were given the files, not my opinion. |
| Checked by me | The strongest audit claims, before using them: the TMDB terms text (read on the live page), the four invented storage figures, the omitted slow queries and the min/max mismatch (Atlas), the estimated image size, the extrapolated batch time, the unrun Gemini option, and the "no horror leakage" claim (embeddings) |
| Spot-checks of the Windows spikes | The LLM spike's headline numbers against its report (they match). The recommendation spike's gate, reproduced from its raw catalogue: **14,478 movies, exactly as reported** |
| New measurement | The language mix of the gated corpus ([Finding 6](#finding-6-the-corpus-gate-under-represents-spanish-language-cinema)) |
| Not done | No paid API calls, no Docker runs. The two Windows spikes were spot-checked, not fully audited. Antigravity itself was not re-run. |

---

## Part A · Can we trust the work done on the Mac?

### A.1 The reviewer numbers tell a story

| Machine · tool | Tasks | Reviewer rounds | Findings reported |
|---|---:|---:|---:|
| Mac · Antigravity | 9 | 8 | **2** (all in one task) |
| Windows · Claude Code | 6 | 10 | **87** |

Part of this gap is fair: the Windows tasks included the two largest design documents. But the audits found real problems in all three Mac spikes whose reviewer said "No findings". "The reviewer found nothing" did not mean "there was nothing to find".

### A.2 What the audits found

| Spike | Raw numbers vs output files | Problems | Does it change a decision? |
|---|---|---|---|
| **TMDB** | Match, except one table row (minor US services shown as "11–14/500"; real counts are 0–14) | Storage rule taken from an HTTP header instead of the terms (see Finding 1). Per-service catalogue sizes come from the `/discover` query the spike itself proved unreliable. Churn conclusions extrapolated from one day, with a near-circular "90% are rotations" check. The committed script is not quite the version that produced the output. | **Slightly**: the ingest must re-fetch metadata within 6 months, and the attribution wording changes. The rest is already being re-measured (churn) or unused (catalogue sizes). |
| **Atlas** | Match where measured, except the local min/max latency | Four storage figures appear in no output. The one measured 768-d value (57% of the free tier) is omitted. "Bit-for-bit parity" is shown on the top 3 only. Two slow queries (622 ms and 998 ms) are left out of the reported range. Updating and dropping the index were never verified. Local image unpinned (`latest` = MongoDB 9.0 vs 8.0 in the cloud). | No. The core claims (384-d fits, five filters combine, local image works on the Mac) held up, including an independent recomputation of the top results. |
| **Embeddings** | Match | "+212 MB image" is package size on a Mac, not a container. "20k in 12 minutes" is extrapolated (spike 16 measured ~24 minutes for 20k on Windows). The handoff's "10 of 10 queries free of horror leakage" is false. "The multilingual model is worse in English" rests on three hand-picked queries. The hosted Gemini option never ran (no key). | No: the choice is cheap to reverse and the memory advantage is measured. But decision record 0007 states two of the weak claims as facts. |

Detail for each spike, in plain words: [learning guide, Part 4](04-spikes-foundations.md).

### A.3 The pattern, and what it says about the tool

The Mac spikes have the same habits:

- **Estimates and measurements share one table** with the same confidence.
- **Conclusions grow as they are summarised.** The spike says "coherent neighbours"; the handoff says "10/10 free of leakage"; the metrics file copies the handoff.
- **Self-graded examples:** "5/5 relevant", judged by the agent that ran the experiment, without a rubric.
- **Confident tone throughout** (bold, "CRITICAL", "verified", "bit-for-bit"), which makes weak claims look as strong as strong ones.

The Windows spikes are not perfect either (both have small samples and an LLM judge), but they **label their own limits**, report their own bugs and failed ideas, and separate "measured" from "from the docs". That's the practical difference to look for, whichever tool you use.

### A.4 Should Opus re-review everything Argon did?

**No.** Here's the risk map of the Mac work:

| Mac work | Risk | Why | Action |
|---|---|---|---|
| Harness setup, dry run, metrics file, index/detail split, harness validation, Mac verification | Low | It's code and config that runs on both machines every session, and the harness tests check it in CI. Problems show up fast. | None |
| TMDB, Atlas and embedding spikes | Medium–High | Their conclusions feed decisions, and spikes are outside every automatic check | **Done in this review**; actions are in the findings below |
| The question section of the recommendation spike (written on the Mac) | Low | Its estimates (25–35k movies, IMDb as "prime candidate") were hypotheses, and measurement corrected them | None |

What *is* worth doing is changing the process so this doesn't need a special audit next time ([Finding 3](#finding-3-the-reviewer-cant-catch-spike-errors-and-reviews-with-the-same-model)).

---

## Part B · Findings

Each finding has a severity (High, Medium or Low), the evidence, and a suggested action. Findings 1–3 are about reliability, 4 about learning, 5–6 about the product, and 7–8 about the process.

### Finding 1: The TMDB spike took its storage rule from the wrong source

**Severity: Medium.** Small fixes, but the ingest design depends on them, and TMDB is the only free source of both movie data and streaming availability.

**Evidence.** The TMDB spike concluded that storing metadata is allowed, using an HTTP `Cache-Control` header as evidence. A cache header tells a client how long to keep one response; it isn't a rule about what an application may store. The rules are in TMDB's [API Terms of Use](https://www.themoviedb.org/api-terms-of-use) (last updated 20 October 2023), read for this review:

- Section 1.C, under "You must not": *"Cache, for longer than 6 months, any information obtained through or from TMDB or the TMDB APIs."*
- Section 3 requires the notice *"This [website, program, service, application, product] uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB."* The product and README use the shorter wording from TMDB's FAQ.

The architecture plans a daily availability refresh, but metadata is fetched once at admission and only re-fetched "periodically", with no upper bound.

**Suggested action.**

1. Use the section 3 wording for the attribution notice, in the product rules, the README and the API's attribution field.
2. Add "re-fetch all stored TMDB metadata at least every 6 months" to the ingest design (the re-fetch policy in the ingest task).
3. When a spike answers a question about terms or licences, quote the terms themselves, with a link and the date read ([Finding 3](#finding-3-the-reviewer-cant-catch-spike-errors-and-reviews-with-the-same-model) adds this to the reviewer's checklist).

### Finding 2: Some weak numbers became facts in the decision records

**Severity: Medium.** None of these is likely to be badly wrong, but each is written as settled.

| Statement | Where | Reality | Where to re-check |
|---|---|---|---|
| The embedder adds +212 MB to the image and needs 279 MB, so the API "fits 512 MB" | [Decision record 0007](../decisions/0007-embeddings-fastembed-profile-template.md), architecture §6 | Package size on a Mac; RSS of a bare process; full API never measured. Render Free is exactly 512 MB, so no margin. | When the container is first built: measure image size and memory under load on Linux |
| "The multilingual model was worse on English mood queries" | Decision record 0007 | Three hand-picked queries; one query went the other way | Keep the decision (memory, and the LLM translates), drop the quality claim |
| Query embedding ≈ 5 ms | Architecture §3 | Warm, in-process, 8-core Mac | End to end in the walking skeleton, and from the host |
| The corpus is ≈ 20% of the free tier | Architecture §4, decision record 0008 | Derived from a storage table that mixes measured and estimated values, on repetitive synthetic text | Read Atlas's own storage figure after the full load |
| Five filters verified together "including `$nin` on 5,000 IDs" | Architecture §3 | The large-list tests used only two filters | Low risk; re-run once with all filters in the skeleton's integration tests |
| Vector search p95 121 ms | Architecture §3 | Warm, 40 results, random vectors | Already planned at full scale (150 results) |
| Indexes can be updated and dropped from code | Spike 09 | Never verified (errors were silenced) | Integration test setup in the skeleton |

**Suggested action.** When writing the walking-skeleton spec, copy this table into its "verify" notes. Pin the local MongoDB image to a version.

### Finding 3: The reviewer can't catch spike errors, and reviews with the same model

**Severity: Medium–High** (it's how the other problems got through).

**Evidence.**

- The [reviewer's checklist](../../.agents/agents/reviewer.md) is for code: unmet acceptance tests, bugs, missing tests, layer violations, scope, product rules. Nothing asks "does every number match the raw output?" or "is this estimated or measured?"
- The reviewer runs with `model: inherit`, so a spike written by a model is reviewed by the same model.
- Spike scripts live in `spikes/`, outside `poe check`. Spike reports are documents. So for a spike, the reviewer is the **only** gate.

**Suggested action.**

1. **Add a spike section to the reviewer's checklist**, used when the active item is a spike or a design document:
   - every number in the report traces to a raw output file (name the JSON path);
   - each number is labelled measured, estimated, or from documentation (with a link and date);
   - extrapolations and sample sizes are stated next to the conclusion;
   - options that were not run are marked as not run;
   - claims about licences and terms quote the source;
   - the handoff and metrics summaries say no more than the report.
2. **Cross-review spikes and design documents on the other tool.** Before merging a spike done on the Mac, run `/review` on that branch from Claude Code on Windows (and the other way round). It costs one session, and it's the cheapest independent check you have.
3. **Consider using Claude Code on the Mac for spikes and design work**, if your subscription allows it. The harness already supports it; only the pairing hasn't been verified. Antigravity can stay for chores and harness work.
4. **Commit the exact script with its output** (the TMDB spike's committed script no longer reproduces its committed output).

### Finding 4: The learning record misses the AI-engineering half

**Severity: Medium** (it's one of the project's two goals).

**Evidence.**

- [LEARNING.md](../../LEARNING.md) has 14 concepts. All are tooling or harness Python: `uv`, ruff, pyright, `Final`, `TypedDict`, fixtures, encodings, `startswith(tuple)`.
- The three `/defend` sessions happened on 12–13 November, before the spikes.
- Nothing is recorded about embeddings, vector search, RAG, structured output, retries, LLM judges, evals, or the Bayesian average, though spikes 09 to 16 were all about them.
- You haven't written Python yourself yet. The spikes contain about 6,000 lines that agents wrote.
- [Decision record 0004](../decisions/0004-autonomous-task-runs-owner-gates.md) names this exact risk ("comprehension rot") and its own remedy: make `/defend`, or a lighter check, part of the merge gate again if you can't explain merged work.

**Suggested action.**

1. **Read the [learning guide](README.md)** over a few days, in its eight parts.
2. **Run three `/defend` sessions:** on the recommendation spike, the LLM spike and the architecture. Use the [question bank](08-concepts-and-questions.md#b-question-bank) as a warm-up.
3. **Be the judge once.** Open [rank_details.json](../../spikes/16-recommendation/rank_details.json) and look at the actual top 5 for each of the 12 requests. Would *you* watch them? Write down which are good and which aren't. It takes about 30 minutes, it teaches you more about the problem than any document, and it's the start of the golden set ([Finding 5](#finding-5-evaluation-is-the-real-bottleneck-start-the-golden-set-early)).
4. **Write some Python yourself in the walking skeleton.** A good candidate is the step-4 check (re-check the rules by value) with its unit tests: pure functions, no I/O, product-critical. Let the agent review *your* code. Defending code and writing it are different skills, and "Python at production level" is goal number one in the brief.
5. **Bring back the brief's light "defend it" gate for code PRs:** three short "why" answers in the PR description before you merge. It's cheaper than a full `/defend` session and keeps you close to the code.

### Finding 5: Evaluation is the real bottleneck; start the golden set early

**Severity: Medium.**

**Evidence.** Every quality claim so far rests on an LLM judge that disagreed with itself on 26% of items, over 12 requests. The relevance of the top 5 is about 1.3 out of 2, and the gains between methods are mostly within noise. The human-labelled golden set (30–50 requests) is planned in the ranking-and-evals task, which comes after enriching the full corpus.

Labelling takes **your** time, not agent time, and it can't be rushed at the end.

**Suggested action.** Start the golden set now, in small pieces: write 30–50 realistic requests (vague, specific, constrained, non-English, kids) with the filters you expect. That list alone powers the constraint-extraction eval, which the backlog already suggests moving right after the skeleton. Add "acceptable movies" labels later, once real profiles exist.

### Finding 6: The corpus gate under-represents Spanish-language cinema

**Severity: Low–Medium.** A product question, not a defect.

**Evidence** (reproduced from the recommendation spike's raw catalogue for this review; same gate, same constants):

| Movies available in… | Spanish-language films: share of catalogue | Share after the gate | Pass rate, Spanish-language | Pass rate, English-language |
|---|---:|---:|---:|---:|
| Spain | 8.8% (2,283) | 5.1% (508) | 22% | 44% |
| Bolivia | 7.8% (1,207) | 5.6% (383) | 32% | 51% |

TMDB votes come mostly from English-speaking users, so a vote-count gate favours English-language films. Two of the three launch countries are Spanish-speaking.

**Suggested action.** Decide whether this matters to you. If it does, options include a lower vote threshold for films in the country's own language, or letting Wikidata critic scores and awards admit films that miss the vote bar. Check a sample of the excluded Spanish-language films first: if they're mostly filler, the gate is doing its job.

### Finding 7: Keep the walking skeleton thin

**Severity: Medium.**

**Evidence.** The [walking skeleton's description](../../feature_list.json) lists about twelve things: intent via the real LLM, query embedding, vector search with unverified filters, the step-4 checks, re-rank and pitch, response states, exclusions, a trace with cost, a static provider list, six deterministic evals, first latency numbers, and the Windows database test. It will be the first real code and the first real test of the harness. A very large first PR is hard to review and hard to defend.

**Suggested action.** At `/spec` time, split it (the backlog already allows this). One possible cut:

1. The end-to-end path with **fake** LLM and embedder ports, real local database, all response states, and the first deterministic evals.
2. The real LLM adapter: Pydantic AI, retry with feedback verified on the real model, cost in the trace.
3. The real embedder and the first latency numbers.

### Finding 8: The same numbers live in too many places

**Severity: Low.** Easy to fix, and it will get worse as the project grows.

**Evidence.** A spike's numbers are copied into its handoff, the metrics file, the progress log, the architecture and a decision record. Copies have already drifted:

- [metrics.md](../metrics.md) §1.4 still lists the inflated per-service catalogue sizes and the extrapolated 20k embedding time; §1.3 says the profile design task is "feat-012" (it's now feat-019).
- The [README](../../README.md) says the LLM provider is "being evaluated" and that product work hasn't started in a way that hides how much was decided.
- The LLM spike's summary still recommends Gemini as a paid fallback (the owner later chose no second provider).
- The recommendation spike's context section still says "25,000–35,000 movies" and "30–50 candidates in ~60 ms".

Each task also touches about seven state files at handoff. That's fine for now, but watch it once code tasks start.

**Suggested action.** Apply the harness's own lesson, "one source per rule", to numbers: the spike report holds the number; summaries **link** to it instead of restating it. A small cleanup task could fix the stale lines above and reduce metrics §1.4 to links.

---

## Part C · What is going well

Feedback should include this, and it's real:

- **The gates are deterministic and live in the repo**, and the harness is tested by its own tests. The most important rule (agents don't edit acceptance tests) is enforced by CI, not by trust.
- **Spike reports cite the output files their numbers come from.** That's what made this audit possible at all. Keep doing it.
- **Decisions have dated records with their price**, and the open questions have owners. Six days in, you can already explain *why* almost everything is the way it is.
- **The product thinking is strong:** the pitch rule, the explicit response states, "never fail silently", and the "we couldn't apply: no spiders" note are the kind of details that make a portfolio project look like a product.
- **The recommendation spike is genuinely good work:** it measured its own measuring tool, reported its own failures, and dropped two attractive data sources on evidence.
- **Spend discipline:** about $0.15 of LLM spend for five spikes, all recorded.
- **Your own feedback improved the process** ("relevance over numeric caps", the backlog split). That is exactly the "human on the loop" role.

---

## Part D · Smaller notes

- **Layer rules:** nothing stops `mcp_server` or `jobs` from importing `api`, though the architecture says they must not depend on FastAPI. Add an import-linter contract when those packages get code ([conventions](../conventions.md#code) already notes the gap).
- **Model licences** for the embedding model aren't recorded anywhere. Note them in decision record 0007 before deploying.
- **The embedding spike embedded queries with `embed()`**, while the decision record prescribes `query_embed()` (which spike 16 used). Check in the skeleton that `query_embed` adds the model's query instruction.
- **Images and models:** pin the `mongodb-atlas-local` image version, as you already pin model IDs and packages.
- **PROGRESS.md** still says "Merge the feat-012 PR" under "Waiting on owner", but it's merged. The next `/start` will refresh it.

---

## Part E · Suggested next steps, in order

| # | Step | Who | Size |
|---|---|---|---|
| 1 | Apply the two TMDB fixes: the section 3 attribution notice now, the 6-month metadata re-fetch in the ingest design | You decide the wording; agent applies | 30 minutes |
| 2 | Read the learning guide; run three `/defend` sessions; rate the 12 requests' results | You, with the agent | 3–5 sessions |
| 3 | Add the spike checklist to the reviewer; adopt cross-tool review for spikes and design documents | Agent (a small harness task) | 1 session |
| 4 | Clean up the stale numbers and duplicated summaries | Agent (a small docs task) | 1 session |
| 5 | Measure catalogue churn (the next task, as planned) | Agent | 1 session |
| 6 | `/spec` the walking skeleton with an explicit split and the verification table from Finding 2; write part of step 4 yourself | You + agent | as planned |
| 7 | Start the golden set: 30–50 requests with expected filters | You | 1–2 sessions, spread out |

Items 3, 4 and 7 are recorded in the **Proposed** section of [docs/backlog.md](../backlog.md), so you can order them like any other work.
