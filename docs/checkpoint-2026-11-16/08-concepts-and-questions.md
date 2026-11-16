# Part 8 · Concepts to master, and questions to challenge

**Reading time:** use it as a reference · [Back to the index](README.md) · Previous: [Part 7](07-inside-the-code.md)

> [!NOTE]
> **How to use this part**
> - **Section A** explains the AI-engineering concepts that came up in this stage, in plain words, with where each one lives in the project. These are the curriculum topics that [LEARNING.md](../../LEARNING.md) doesn't cover yet: so far it only covers harness Python (encodings, fixtures, `Final`, `TypedDict`).
> - **Section B** is a question bank. Try to answer a question out loud or in writing *before* you look at the source. That's the "ask before telling" method from the brief, and it's what `/defend` does.

---

## A. Concepts

### Vectors and search

| Concept | In plain words | Where in the project |
|---|---|---|
| **Embedding** | A list of numbers (here 384) that represents the meaning of a text. Texts with similar meaning get similar lists. | Every movie profile and every request is embedded ([Part 4, spike 10](04-spikes-foundations.md#5-spike-10--embeddings-which-model-and-how-heavy)) |
| **Cosine similarity** | A number from −1 to 1 that says how close two vectors point in the same direction. 1 = same meaning. | The `score` returned by vector search |
| **Vector index (ANN, HNSW)** | Comparing a query with every movie is slow at scale. An index builds a graph of neighbours (HNSW = "hierarchical navigable small world") and walks it to find *approximately* the nearest ones. Fast, but not guaranteed exact. | Atlas `vectorSearch` index ([Part 7, example 5](07-inside-the-code.md#5-filtered-vector-search)) |
| **`numCandidates` and `limit` (K)** | How many neighbours the index explores, and how many it returns. More explored = more accurate and slower. | K = 150 ([Part 6](06-spike-recommendation-quality.md#6-question-4--ranking-how-many-candidates-and-what-formula)) |
| **Pre-filter vs post-filter** | Apply the rules *during* the search (all results obey them) or *after* (you may lose most results). | All hard rules are pre-filters, then re-checked in code |
| **RAG** (retrieval-augmented generation) | Retrieve relevant data first, then give it to an LLM to generate an answer grounded in that data. | Steps 3 to 5 of a search: retrieve candidates, then the LLM picks and pitches from them only |
| **Recall at K** | Of the items you *should* find, what share is inside your top K? | The depth table in spike 16 (0.94 at K = 150 for broad requests) |
| **Min-max normalisation** | Rescale numbers so the smallest becomes 0 and the largest 1. Simple, but the result depends on which items you included. | The hybrid score's similarity ([Part 7, example 6](07-inside-the-code.md#6-the-hybrid-score)) |

### LLMs inside a product

| Concept | In plain words | Where in the project |
|---|---|---|
| **Structured output** | The provider forces the model's answer to match a JSON Schema, so you always get parseable JSON with the right fields. It does **not** guarantee the content is right. | Both LLM calls and the profile job ([Part 5](05-spike-llm.md)) |
| **Closed vocabulary** | A fixed list of allowed values (an enum). The model must pick from it; it can't invent new values. | Tones, content warnings, etc. ([Part 6](06-spike-recommendation-quality.md#5-question-3--the-profile-and-the-mirror-schema)) |
| **Mirror schema** | Every field the LLM extracts from the request has a matching stored field on the movie, so it can be applied as a filter. | [Decision record 0005](../decisions/0005-closed-vocabulary-mirror-schema.md) |
| **Validation retry with feedback** | When the answer is valid JSON but wrong (an invented ID), send the error back and ask once more. A plain retry tends to repeat the mistake. | `output_validator` + `ModelRetry` ([Part 7, example 4](07-inside-the-code.md#4-structured-output-with-a-validator-and-a-retry)) |
| **Tokens and cost** | Providers charge per token (≈ ¾ of a word) of input and output. Input is usually cheaper. Most of a "pick and pitch" call is input: the candidates. | $0.00067 per search ([Part 5](05-spike-llm.md#3-the-results)) |
| **Reasoning effort** | Newer models can "think" before answering, which costs tokens and time. For simple extraction, `reasoning_effort="none"` was enough. | The `gpt-6-luna` setting |
| **Batch API** | Send many requests as one job, get results within 24 hours, pay half price. Good for offline work. | Profiling ~14,500 movies for about $1 |
| **Data retention** | How long the provider keeps your prompts, and whether it trains on them. A product decision, not only a technical one. | The privacy note; Gemini's free tier ruled out |

### Measuring quality

| Concept | In plain words | Where in the project |
|---|---|---|
| **Eval** | A repeatable measurement of AI quality, like a test suite for behaviour that isn't simply right or wrong. | `evals/` (protected by the PR gate; not created yet) |
| **Deterministic eval** | A yes/no check code can do: every result is streamable, every pitch ≤ 350 characters. Must pass 100%. | The walking skeleton adds the first ones |
| **Golden set** | A fixed set of requests with answers labelled by a human (you). The reference everything is tuned against. | 30–50 requests planned in the ranking-and-evals task |
| **LLM-as-judge** | Using an LLM to score outputs (e.g. relevance 0–2). Cheap and fast, but it has its own errors and biases. | The blind judge in spike 16 |
| **Judge agreement / noise** | How often a judge agrees with itself or with a human. Sets the smallest difference you can trust. | 26% self-disagreement → ignore differences under ~0.1 |
| **Precision at 5** | Of the top 5 results, how many are acceptable? | The main retrieval metric planned in [metrics.md](../metrics.md) |
| **Bayesian average** | Mix an item's own average with the global average, weighted by how many votes it has. Protects against "3 votes, all 10/10". | The quality score ([Part 7, example 2](07-inside-the-code.md#2-the-bayesian-quality-score-and-the-gate)) |
| **Spearman correlation** | Do two lists rank items in the same order? 1 = identical order, 0 = unrelated. | TMDB vs IMDb (0.83: mostly the same), TMDB vs critics (0.58: a different signal) |
| **p50 / p95** | The median, and the value 95% of measurements are below. p95 shows the slow cases users notice. With only 20 measurements, p95 is basically the second-slowest one. | All latency numbers |

### Engineering habits that showed up

| Concept | In plain words | Where in the project |
|---|---|---|
| **Idempotent job** | Running it twice gives the same result as running it once. | `source_hash` + `prompt_version` + `embedding_model` decide whether a movie is re-processed |
| **Ports and adapters** | The core code depends on interfaces; the outside world plugs in behind them. | [Part 3, section 3](03-the-architecture.md#3-layers-and-ports-the-clean-architecture-part) |
| **Pinning versions** | Use exact versions of models, libraries and images, never "latest". A silent upgrade changes behaviour. | `uv.lock`; model IDs; *not yet* the local MongoDB image |
| **Cold start, RSS** | Time to start a process and load the model; memory the process really uses. They decide which free hosting tiers fit. | Spike 10 |

---

## B. Question bank

Each question says where to check your answer. They're grouped by part, so you can do one group per sitting. The ones marked ★ are good interview material.

### The product and the harness

1. ★ Why are rules about constraints applied by the database and code, and never by the LLM? → [Decision record 0005](../decisions/0005-closed-vocabulary-mirror-schema.md)
2. Why is the pitch length a code check and not just an instruction in the prompt? → [Spike 11, gotcha 2](../spikes/11-runtime-llm.md#3-structured-output)
3. ★ What are the three strengths of gate in this harness? Give one example of each. → [Part 2, section 4](02-the-harness.md#4-three-strengths-of-gate)
4. Why does the reviewer compare against `origin/main` and not `HEAD`? → [Harness log entry](../harness-log/2026-11-12-feat-004-reviewer-diff-target.md)
5. What happens, step by step, when the Stop hook fails three times in a row? → [stop_gate.py](../../scripts/hooks/stop_gate.py)
6. Why is `.claude/` made of stubs instead of copies of `.agents/`? What was rejected and why? → [Decision record 0003](../decisions/0003-support-antigravity-and-claude-code.md)

### The architecture

7. ★ Walk through the 7 steps of a search for *"something scary but not gory, in Korean, under 2 hours"*. Which fields does the intent get? → [Part 3](03-the-architecture.md#2-one-search-step-by-step)
8. Why two LLM calls per search and not one? → [Part 3](03-the-architecture.md#why-two-llm-calls-and-not-one)
9. What does the user see if the first LLM call fails? And the second? Why are they different? → [Product document, response states](../product.md#4-response-states)
10. How does `source_hash` make enrichment idempotent? What would trigger a re-enrichment? → [Architecture §4](../architecture.md#4-offline-pipeline)
11. Why keep movies that leave streaming? What is the cost, and what is the plan if storage grows? → [Spike 16, Q1](../spikes/16-recommendation-signals-and-ranking.md#q1-corpus-selection-the-1984-problem-retention)

### The spikes

12. ★ What is the `/discover` trap, and which product rule would it have broken? → [Spike 08, Q4](../spikes/08-tmdb-and-providers.md#4-flat-rate-vs-rentbuy)
13. Why must every filter field be declared in the vector index? What error do you get otherwise? → [Spike 09, Q2](../spikes/09-atlas-vector-search.md#2-pre-filters)
14. Spike 09 used random vectors. Which of its conclusions still hold for real embeddings, and which need re-checking? → [Part 4, section 4](04-spikes-foundations.md#4-spike-09--mongodb-atlas-free-tier-and-vector-search)
15. Why was `fastembed` chosen over PyTorch? Which of the reasons are measured, and which are estimates? → [Part 4, section 5](04-spikes-foundations.md#5-spike-10--embeddings-which-model-and-how-heavy)
16. ★ Why was the Gemini free tier ruled out, even though it costs $0? → [Part 5, section 4](05-spike-llm.md#4-the-terms-of-service-mattered-as-much-as-quality)
17. ★ What is a "retry with feedback", and what evidence showed a plain retry isn't enough? → [Part 5, section 5](05-spike-llm.md#5-what-the-spike-learned-about-retries)
18. ★ Explain the "1984 problem" and how gate G7 solves most of it. → [Part 6, section 3](06-spike-recommendation-quality.md#3-question-1--which-movies-to-store-the-gate)
19. Why was IMDb dropped? Give both reasons. → [Part 6, section 4](06-spike-recommendation-quality.md#4-question-2--which-outside-data-helps)
20. ★ The judge disagreed with itself on 26% of items. What does that mean for every other number in the spike? → [Part 6, section 5](06-spike-recommendation-quality.md#measuring-the-measuring-tool)
21. Why did the hybrid formula push a 4-hour drama into an "easy" request? → [Part 7, example 6](07-inside-the-code.md#6-the-hybrid-score)
22. Why is K = 150 and not 50? → [Spike 16, Q4](../spikes/16-recommendation-signals-and-ranking.md#q4-hybrid-ranking-and-retrieval-depth)

### Challenge questions (no single right answer)

23. Is G7 the right gate for users in Spain and Bolivia, given that Spanish-language films pass it half as often? What evidence would change your mind?
24. The project uses an LLM judge from the same model family that wrote the profiles. What bias could that create? How would you test for it?
25. TMDB data may be stored for 6 months at most. What does that mean for the ingest schedule, and what does it cost in TMDB calls? → [Review, finding 1](review.md#finding-1-the-tmdb-spike-took-its-storage-rule-from-the-wrong-source)
26. Would you trust a recommendation system with relevance 1.3 out of 2 on its top 5? What would "good enough to ship" mean for you?
27. Which decision in this stage would be the most expensive to reverse in three months? Is its evidence strong enough?

### How to turn these into learning records

- For a `/defend` session on a spike, run `/defend feat-016` (or another task id): it finds that task's commits and asks you three questions.
- For a concept, run `/tutor <concept>`, e.g. `/tutor Bayesian average` or `/tutor HNSW`. It explains with a C# comparison and adds the concept to [LEARNING.md](../../LEARNING.md).
- Either way, the concept map in `LEARNING.md` is where your progress becomes visible (Seen → Practised → Can explain).

[Back to the index](README.md) · Previous: [Part 7](07-inside-the-code.md)
