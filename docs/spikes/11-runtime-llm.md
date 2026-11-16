---
id: feat-011
type: spike
status: answered   # questions ready -> answered
timebox: 2 sessions
---
# Spike: runtime LLM (provider, cost, structured output, framework)

## Why
The product calls an LLM twice per query (understand, re-rank + pitch) and once per movie offline (emotional profile). The provider and model decide quality, cost per query, the cost of enriching 5–20k movies, and latency. Budget: zero cost by default, a small spend when it clearly improves quality (product.md §1). The framework choice shapes the `LanguageModel` adapter. Architecture open question Q6. This was on the inception brief's Week 1 checklist but had no backlog item.

## Questions
Each answer: the finding, plus evidence (docs link and date, command and output, measurements).

1. **Limits and cost.** Compare at least two candidates: Gemini on its free tier, and a low-cost OpenAI model (e.g. a "mini" tier).
   - For each: rate limits (requests and tokens per minute and per day) and price per million input and output tokens.
   - Cost per query (2 calls) and per 1,000 profiles. Can enrichment of 20k movies stay within a small budget, and how many days does it take?
   - *Changes:* provider and model, corpus size, enrichment batching, eval budget.
2. **Data use.** What do each candidate's terms say about using prompts and outputs (the user's mood text is sent to the model)?
   - *Changes:* privacy note in the UI or README, possibly the provider.
3. **Structured output.** Does the model reliably return JSON matching a Pydantic schema for:
   - the query intent, including filters from a closed vocabulary and an English summary for non-English input (architecture Q9, Q11);
   - the re-rank with pitches (≤ 350 chars, about the movie only)?

   Try 10 queries, at least 3 of them not in English.
   - *Changes:* the retries in query steps 2 and 6 (architecture.md), prompt design.
4. **Latency.** p50/p95 for each of the two online calls.
   - *Changes:* p95 latency target (open question Q7), whether to merge the two calls.
5. **Framework.** For two structured calls, what does Pydantic AI add over the providers' plain SDKs (retries, validation, testing with fakes, switching provider)?
   - *Changes:* the `infra` adapter and a new dependency (needs an ADR).
6. **Fallback.** If the chosen provider's quota or budget runs out, which provider could replace it behind the same port?
   - *Changes:* the *Service unavailable* state, configuration.

## How
- Throwaway scripts in `spikes/11-llm/` with 10 sample queries.
- Build each re-rank prompt with 30–50 candidates (TMDB overviews or synthetic profiles), as in the real query flow, and record input and output tokens per call: candidates make up most of the prompt (questions 1 and 4).
- For enrichment, profile ~20 sample movies and record tokens per movie.
- Needs API keys in `.env` for the providers compared (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`; owner). Add any new key name to `.env.example`.

---

## Findings & Evidence

Measured on **2026-11-16** from the owner's Windows 11 laptop in Spain (Python `3.13.18`, `openai 3.51.0`, `google-genai 2.34.0`, `pydantic-ai-slim 2.68.0`), with throwaway scripts in [`spikes/11-llm/`](../../spikes/11-llm/):
- [probe_llm.py](../../spikes/11-llm/probe_llm.py) runs the real query flow: understand → embed `summary_en` with the feat-010 model (`fastembed` `bge-small-en-v1.5`) → top 40 of the 200 real TMDB movies from feat-010 → re-rank and pitch → the step-6 checks ([schemas.py](../../spikes/11-llm/schemas.py)).
- The same script then makes the profile call for 20 movies.
- It runs **2 rounds × [10 queries](../../spikes/11-llm/queries.json)**: 5 English, plus ES, FR, PT, DE and JA. Each query has the filters we expect it to produce.
- Prompts are in [prompts.py](../../spikes/11-llm/prompts.py). The closed vocabulary is a throwaway placeholder; the real one comes with the profile feature.
- Raw per-call logs are in `spikes/11-llm/runs/*.jsonl`, the summary is in [report.json](../../spikes/11-llm/report.json) (from [summarize.py](../../spikes/11-llm/summarize.py)), and the Pydantic AI runs are in [runs_pydantic_ai.json](../../spikes/11-llm/runs_pydantic_ai.json) (live) and [fallback_offline.json](../../spikes/11-llm/fallback_offline.json) (offline fakes).
- Facts labelled "from the research report" came from a desk-research subagent that cited the official URLs on 2026-11-16. Facts labelled "re-fetched" I read myself the same day.

**Candidates.** Model choice came from the models list endpoints ([models.json](../../spikes/11-llm/models.json)) and the pricing and deprecation pages, all checked 2026-11-16.

| Provider | Model | Why this one |
|---|---|---|
| Gemini | **`gemini-3.5-flash-lite`**, thinking `minimal` | Stable flash-lite with no shutdown date. Recommended for new projects. Has a free tier. |
| OpenAI | **`gpt-6-luna`**, `reasoning_effort="none"` | Cheapest current model with Structured Outputs. Replaces `gpt-5.4-nano`, which shuts down 2027-04-01, and `gpt-4o-mini`/`gpt-4.1-mini`, which shut down 2027-01-14. |

A 1-query smoke test of `gpt-5.4-nano` turned "not scary" into all 12 avoid values, so I dropped it.

**Spend for the whole spike:**
- OpenAI ≈ **$0.022**: `gpt-6-luna` ≈ 143k input and 11k output tokens, plus the nano smoke test.
- Gemini **$0**: the key is on the Free Tier (see Q1).

### 1. Limits and cost

- **Finding:**
  - On measured tokens, **`gpt-6-luna` costs `$0.00067` per query (≈ `$0.67` per 1,000 queries)** and **`$0.11` per 1,000 profiles**, or ≈ `$0.055` with the Batch API.
  - So **enriching 20k movies costs about `$1.10` once** with Batch. That is small, but not zero.
  - `gemini-3.5-flash-lite` on the paid tier costs about 4× more: `$0.0026` per query and `$0.45` per 1,000 profiles. Cost is the mean over calls that got a response, retries included.
  - On the free tier it costs `$0` but is capped at **15 RPM**. 20k profiles would take ≥ 22 h of calls, and the daily cap is unknown.
  - The free tier also can't be used for the online path (see Q2).
- **Measured tokens per call** (averages, `report.json`):

  | Call | `gpt-6-luna` in / out | `gemini-3.5-flash-lite` in / out |
  |---|---|---|
  | Understand | 613 / 67 | 382 / 103 |
  | Re-rank + 5 pitches (40 candidates) | 4,191 / 255 | 4,477 / 349 |
  | Profile (1 movie) | 580 / 103 | 359 / 135 |

  Reasoning and thinking tokens were 0 at these settings. OpenAI counts the strict JSON schema as input tokens.
- **Prices per 1M tokens:** from [prices.json](../../spikes/11-llm/prices.json), Standard / Batch.
  - `gpt-6-luna`: in `$0.10 / $0.05`, out `$0.50 / $0.25`, cached input `$0.01` ([OpenAI pricing](https://developers.openai.com/api/docs/pricing), re-fetched 2026-11-16).
  - `gemini-3.5-flash-lite` paid tier: in `$0.30 / $0.15`, out `$2.50 / $1.25` (thinking included). Free tier: "Free of charge" ([Gemini pricing](https://aistudio.google.com/docs/pricing); the `ai.google.dev` docs now redirect to `aistudio.google.com/docs`).
  - Not tested: `gemini-3.1-flash-lite` is cheaper at `$0.25 / $1.50`, but it shuts down 2027-05-07.
- **Rate limits:**
  - **Gemini free tier, measured.** Google doesn't publish the numbers: [rate-limits](https://aistudio.google.com/docs/rate-limits) says to look in AI Studio. One 429 in the run named the limit:
    `quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier, model: gemini-3.5-flash-lite, quotaValue: '15'`.
  - **Limits we could not get:**

    | Limit | Status |
    |---|---|
    | Gemini free TPM and RPD | **Not published.** No per-day 429 came up in about 85 requests. The owner can read them in AI Studio (https://ai.dev/rate-limit, the link in the 429 body). |
    | Gemini paid Tier 1 RPM, TPM and RPD | **Not published.** The page gives only a batch limit of 10M enqueued tokens for flash-lite. |

  - **Gemini free-tier availability, measured.** In the benchmark, **9 of 68 attempts (13%) failed with `503 UNAVAILABLE: "This model is currently experiencing high demand"`**. In the Pydantic AI run, 4 of 6 Gemini query runs hit one. OpenAI had 0 API errors in 61 benchmark attempts and 13 successful Pydantic AI requests (2 of the 61 benchmark attempts failed our step-6 checks; see Q3). Not counted: two deliberate bad-key requests that got a 401 in the fallback demo.
  - **OpenAI, from the docs, not measured** ([rate limits](https://developers.openai.com/api/docs/guides/rate-limits), re-fetched 2026-11-16):
    - The paid tiers are Build, Launch and Grow. Build needs "$5 in total credit purchases".
    - The "Luna" group gets **5,000 RPM and 2,000,000 TPM** on Build. I'm assuming `gpt-6-luna` is in that group; the page doesn't name models.
    - RPD and TPD exist as limit types, but **no per-day limit is listed for any paid tier**.
    - The Free tier lists no rate limits, only a "$100 / month" usage limit.
    - There are no free credits. The opt-in free-tokens program is covered in Q2.
- **Days to enrich 20k:**
  - OpenAI: well under a day. At 5,000 RPM it is minutes, and the Batch API finishes within 24 h at half price.
  - Gemini free: at least 1,333 min (22 h) of calls at 15 RPM. The real number of days can't be calculated without the unpublished RPD.
- **Eval budget:** one run of 50 golden queries (100 calls) costs ≈ `$0.03` on `gpt-6-luna`.

### 2. Data use

- **Finding: the Gemini free tier is ruled out for the online calls.**
  - Its [terms](https://aistudio.google.com/docs/terms) (effective 2026-03-23, re-fetched 2026-11-16) say: *"You may use only Paid Services when making API Clients available to users in the European Economic Area, Switzerland, or the United Kingdom."* **ES is a launch country.**
  - On the free tier, *"Google uses the content you submit … and any generated responses to provide, improve, and develop"* its products, and *"human reviewers may read, annotate, and process your API input and output."*
- **Minors: an owner decision on both providers.**
  - The Gemini terms' "Age Requirements" section covers **paid and unpaid** use:
    - *"You must be 18 years of age or older to use the APIs."* This applies to the developer.
    - *"You also will not use the Services as part of a website, application, or other service that is directed towards or is likely to be accessed by individuals under the age of 18."*
  - A public movie recommender, with queries like q04 "movie night with my kids", could count as *likely to be accessed* by minors. That puts Gemini at risk even as a paid fallback.
  - OpenAI's [Services Agreement](https://openai.com/policies/services-agreement/) (effective 2026-01-01, §3.3, re-fetched 2026-11-16) only bars letting *"minors … use OpenAI Services without consent from their parent or guardian"*.
  - So the product may need an age note (e.g. "18+, or with a parent's consent") whichever provider is used.
- **Gemini paid tier:**
  - Prompts are not used to improve products. They are logged for 55 days for abuse detection only ([usage policies](https://aistudio.google.com/docs/usage-policies), from the research report).
  - [Logs policy](https://aistudio.google.com/docs/logs-policy), re-fetched 2026-11-16: *"Logging is on by default … for Generate Content API calls in projects created on or after October 26, 2026"*. It applies only to billing-enabled projects and keeps logs up to 55 days by default.
  - The opt-out is a project setting, not an API parameter: *"you can turn logging on or off at any time from the Logs and Datasets page in AI Studio."*
- **OpenAI API** ([your data](https://developers.openai.com/api/docs/guides/your-data), from the research report):
  - API data is *"not used to train or improve OpenAI models"* unless you opt in.
  - Abuse logs are kept for up to 30 days, and flagged content may get human review.
  - The Responses API stores data for 30 days unless `store:false`. The spike used Chat Completions.
- **OpenAI's opt-in data-sharing program** ([help article](https://help.openai.com/en/articles/10306912-sharing-feedback-evaluation-and-fine-tuning-data-and-api-inputs-and-outputs-with-openai), re-fetched 2026-11-16):
  - It gives free daily tokens: on Build, 250K per day for one model group and 2.5M per day for the other.
  - The shared data is used *"to help identify usage patterns, measure model quality"* and to inform future training.
  - **Don't opt in**: it would share our users' mood text.
- **Privacy note to add to the UI and README** (proposal):
  > "Your mood text is sent to our language-model provider (<provider>) to understand it. It isn't used to train their models and is kept up to <retention> for abuse monitoring. Don't include personal details."

  `<retention>` depends on the provider: **30 days** on OpenAI, **55 days** on paid Gemini. If a fallback provider can answer, the note must name both providers and use the longer retention.

  The offline profile job sends only TMDB movie data, never user text.

### 3. Structured output

- **Finding: both models return schema-valid JSON every time.**
  - That's **0 schema errors in 120 benchmark responses** (59 Gemini, 61 OpenAI), because both providers constrain the output to the JSON schema.
  - **Every failure was semantic** (our step-2 and step-6 checks) **or a 503/429**.
  - **Non-English intent extraction:**
    - Both models got the runtime and the expected avoid values right in **10/10 non-English runs**, and every `summary_en` was in English.
    - With "no extra values" also required, `gpt-6-luna` scored 10/10 and Gemini 9/10: for "keine Action" (DE, round 2) Gemini added `violence` and `max_intensity: 2`.
  - `gpt-6-luna` was the more accurate and reliable of the two.

  | Measure (2 rounds) | `gpt-6-luna` | `gemini-3.5-flash-lite` |
  |---|---|---|
  | Understand valid, 1st try → after 1 retry | **20/20 → 20/20** | 17/20 → 18/20. Returned 4 tones (cap is 3): q01 once, fixed by the retry; q04 in both rounds, where both attempts failed. |
  | Re-rank valid, 1st try → after retry | 19/20 → 19/20. q10 round 2 repeated an ID 4 times. The plain retry still repeated one. | 13/18 → 17/18. **All 5 failures were 503s.** |
  | Profile valid | 20/20 | 19/20 (503s) |
  | `max_runtime` extracted exactly | 20/20 | 18/18 |
  | Expected `avoid` present / no extra values | 20/20 / **20/20** | 18/18 / 17/18: "keine Action" became `violence` |
  | `max_intensity` as expected: ≤ 3 for q01 "not too dramatic" and q04 "kids", null for q05 "anything" | 6/6 (q01, q04, q05) | 4/4 (q01 and q05 only; q04's understand failed) |
  | Pitches ≤ 350 chars / max / mean | 95/95 / 242 / 194 | 85/85 / 280 / 205 |
  | P2 heuristic flags (you, your, mood, tonight, perfect for, …) | 0 | 0 |

- **Example:**
  - Input (JA): "今夜は怖くない、心温まるアニメ映画が見たいです。2時間以内でお願いします。"
  - `gpt-6-luna` output: `{"input_language":"ja","summary_en":"A heartwarming animated movie with a gentle, non-scary tone…","max_runtime_minutes":120,"avoid":["horror_scares"],"max_intensity":1}`
  - The pitches read as facts about the film, mostly a premise plus tone/genre. For example, *Back to the Future*: "An eighties teenager is accidentally sent back to 1955 … This brisk adventure blends comedy, time travel, an eccentric inventor, and a race to return to 1985."
  - The pitch-quality eval (with owner labels) is still needed. These pitches lean on plot more than tone.
- **Gotchas found:**
  1. **google-genai's `response_schema` rejects integer enums** (`Literal[1, 2, 3, 4, 5]`) on the client side (`Input should be a valid string`). The fix is `response_json_schema=Model.model_json_schema()`.
  2. **Pitch length stays a deterministic check in our code.** It's a P2 rule, so code enforces it whatever the provider does. The spike never sent `maxLength`; with a 300-char target in the prompt, the longest pitch was 280 chars. The research report adds that Gemini strips `minLength`/`maxLength` ([structured output](https://aistudio.google.com/docs/structured-output)), but that wasn't tested here.
  3. **A plain retry, with no feedback, often brings back the same kind of error.**
     - OpenAI q10 round 2: the first attempt picked `[354912, 1084244×4]`; the retry `[354912, 4935, 1084244, 1187326, 1084244]` still repeated an ID.
     - Gemini q04: 4 tones on both attempts in both rounds. In q01, by contrast, the plain retry fixed it.
     - **Proposal for feat-012:** step-2 and step-6 retries send the check's error back to the model, as Pydantic AI's `ModelRetry` does (Q5). This was shown with a scripted `FunctionModel` only, **not yet on a real model**.
     - Fix deterministically only what is safe in step 2: truncate tones to 3.
     - A duplicate or invented pick in step 6 is not safe to fix: dropping it leaves fewer than 5 picks. It stays a step-6 failure: retry, then *Results without pitches* (architecture §3).
  4. TMDB's `duringcreditsstinger` keyword leaked into a smoke-test pitch, so ingest should drop `*stinger` keywords.
  5. For "nada de violencia", Gemini picked *Scary Movie*. The re-rank never sees the avoid filters, so this confirms that **step 4 must apply the avoid and intensity filters to profile fields before the re-rank** (architecture Q11).
  6. **Pin exact model IDs.** From the research report, 2026-11-16:
     - The `-latest` aliases are hot-swapped with every release ([models](https://aistudio.google.com/docs/models)).
     - `gemini-2.5-flash`/`-pro` route to newer models from 2026-12-01 ([deprecations](https://aistudio.google.com/docs/deprecations)).

### 4. Latency

- **Finding:**
  - **When it answers, `gemini-3.5-flash-lite` is about 1.7× faster.** Both models fit the `< 10 s` p95 guess for the whole query.
  - **Keep the two calls separate.** Step 4 (deterministic P1/P3 checks on the retrieved candidates) has to run between them, and retrieval needs the intent's `summary_en`. Merging them would mean the LLM sees unchecked candidates.
  - **Unmeasured hypothesis:** the re-rank is the slow call because it writes 255–349 output tokens of pitches, against 67–103 for understand. I didn't time the stages separately. If p95 matters later, a shorter pitch target or showing results progressively in the UI are the levers to try.

  | ms, first successful attempt | `gpt-6-luna` p50 / p95 (n) | `gemini-3.5-flash-lite` p50 / p95 (n) |
  |---|---|---|
  | Understand | 1,635 / 2,659 (20) | 957 / 1,503 (17) |
  | Re-rank + pitch (40 candidates) | 3,259 / 4,046 (19) | 1,672 / 2,508 (13) |
  | **Both LLM calls per query** (incl. retries) | **4,979 / 6,304** (19) | **2,940 / 4,673** (17)* |

  \* **Gemini's "incl. retries" is biased low.** The benchmark logged attempts that raised (the 503s) as 0 ms, and 429 back-off sleeps aren't counted. 4 of those 17 queries had a 503 round trip that isn't in the total. In production a 503 also costs a retry or a fallback. `providers.py` now times failed attempts too, for any re-run. OpenAI's numbers are unaffected: it had no API errors.

- **Estimated end-to-end p95** with embed (≈ 6 ms, feat-010) and `$vectorSearch` (121 ms on M0, feat-009): **≈ 6.4 s on OpenAI** (6,304 + 127 ms) and ≈ 4.8 s on Gemini.
- **Q7 stays open.** It should be measured from the hosting region in the first end-to-end slice. These numbers are from a laptop in Spain.

### 5. Framework (Pydantic AI 2.68.0 vs plain SDKs)

- **Finding: use `pydantic-ai-slim[openai,google]` in the `infra` adapter, with `NativeOutput`.** It needs an ADR in feat-012.
  - It replaces exactly what the spike had to write by hand in [providers.py](../../spikes/11-llm/providers.py), about 250 lines: two SDK adapters with different schema quirks, a retry loop, and usage mapping.
  - It also adds what the plain loop lacked.
  - The domain still owns its own `LanguageModel` `Protocol`, so application tests use our in-memory fake. Pydantic AI's fakes are for the infra adapter's tests.
- **Evidence:**
  - **Switching provider is one argument.** The same `Agent(output_type=Intent)` ran on `OpenAIChatModel("gpt-6-luna")` and `GoogleModel("gemini-3.5-flash-lite")` with no other change: 6/6 runs passed on OpenAI, while Gemini runs failed only on 503s.
  - **`@agent.output_validator` + `ModelRetry`** turns our step-6 checks into a retry *with the error sent back*. In the scripted `FunctionModel` test, the first reply invented `tmdb_id=999`, the validator rejected it, and the 2nd call returned a valid pick (`model_calls: 2`).
  - **The retry budget is 1 by default, matching the architecture.** This was measured offline in [fallback_offline.json](../../spikes/11-llm/fallback_offline.json) by [probe_fallback_offline.py](../../spikes/11-llm/probe_fallback_offline.py), using a model that always returns invalid output:

    | `Agent(retries=…)` | Model calls before `UnexpectedModelBehavior` |
    |---|---|
    | Not passed | 2 |
    | 0 | 1 |
    | 1 | 2 |
    | 2 | 3 |

  - **`FallbackModel(primary, secondary)`, live:**
    - With a bad-key primary (401), the same call was answered by `gpt-6-luna` in 3,075 ms.
    - `FallbackModel(gemini, openai)` answered 3/3 from Gemini, which didn't fail that time.
    - These rows come from a second run with `--fallback-only` added to the script. That run reloaded `runs_pydantic_ai.json` and replaced only its `fallback` rows, so the file's `args` are the first run's. The models and settings were the same: `gpt-6-luna`/`none`, `gemini-3.5-flash-lite`/`minimal`. The script now also records `fallback_args`.
    - The first run's fallback attempt, `FallbackModel(bad key, gemini)`, failed on both models with a `FallbackExceptionGroup`, and its sub-exceptions weren't recorded.
  - **`FallbackModel(primary, secondary)`, offline** ([fallback_offline.json](../../spikes/11-llm/fallback_offline.json)):
    - The recorded default is `fallback_on_default: ["ModelAPIError"]`.
    - A primary raising one of Pydantic AI's exception types was called once, and the secondary answered every time. The types tested were **503** (`ModelUnavailableError`, `ModelHTTPError(503)`), **429** (`ModelHTTPError(429)`), **timeout** (`ModelTimeoutError`) and **401**.
    - This shows how `FallbackModel` reacts to those types. It does **not** show that the real `OpenAIChatModel`/`GoogleModel` turn an SDK 429 or timeout into them.
    - Live, only **401** (OpenAI) and **503** (Gemini, `ModelUnavailableError`) were seen. Other 4xx codes, such as 400 and 413, weren't tested.
    - A primary returning **invalid output** was re-prompted once on the *same* model and then raised `UnexpectedModelBehavior`. It **never fell back**.
    - A single `GoogleModel` does not retry 503s by itself: 4 live Pydantic AI runs failed with `ModelUnavailableError: 503`.
  - **Testing:**
    - `TestModel` (like AutoFixture) generates schema-valid data from the type. Its default `max_runtime_minutes=0` was rejected by our validator, so validators apply to fakes too.
    - `TestModel(custom_output_args=…)` and `FunctionModel` script exact replies with no network and no keys.
  - **Watch out:**
    - The default *tool-call* output mode added input tokens to the same understand query: +85 on OpenAI (q02: 662 vs 577) and **+342 on Gemini** (q10: 724 vs 382). That's why the recommendation is `NativeOutput`.
    - v2 prints a banner to stdout unless `PYDANTIC_AI_NO_BANNER=1`.
    - It releases fast. `pydantic-ai-slim` 2.68.0 was uploaded 2026-11-12T02:30Z (PyPI JSON API, checked 2026-11-16), so pin it in `uv.lock`.

### 6. Fallback

- **Finding:**
  - **Primary: `gpt-6-luna`** (paid, most accurate, 0 errors).
  - **Fallback: `gemini-3.5-flash-lite` on the paid tier**, behind the same port through `FallbackModel`, configured as e.g. `LLM_MODEL=openai:gpt-6-luna` and `LLM_FALLBACK_MODEL=google:gemini-3.5-flash-lite` (empty = no fallback).
  - It's measured on the same harness: slightly worse extraction, but faster.
  - The paid tier is required for the online path (Q2). It costs nothing until used, but **the owner must enable billing on the Google project**.
  - **Caveat:** the Gemini terms' under-18 clause (Q2) applies to paid use too. If the owner judges the app *likely to be accessed* by minors, Gemini can't be the fallback. That leaves no fallback (the existing degraded states) or another provider whose terms allow it.
  - If both fail, the states we already have apply: *Service unavailable* in step 2, *Results without pitches* in step 6.
- **Zero-cost alternatives** (from the research report, 2026-11-16; not tested, no keys; none checked against the minors clause):
  - [Groq](https://console.groq.com/docs/rate-limits) free tier:
    - `gpt-oss-120b`, strict JSON schema ([structured outputs](https://console.groq.com/docs/structured-outputs)), OpenAI-compatible.
    - Its docs give 8K TPM, roughly one re-rank call per minute, and contradict themselves on plan names.
    - Emergency or dev use only.
  - [OpenRouter](https://openrouter.ai/docs/api-reference/limits) `:free` models: 20 RPM and 50 RPD.
  - [Cerebras](https://inference-docs.cerebras.ai/support/rate-limits): 30-day trial credits only.
  - Excluded:
    - Mistral's free plan has no API access ([usage limits](https://docs.mistral.ai/admin/billing-usage/usage-limits)).
    - GitHub Models was retired on 2026-07-30 ([GitHub docs](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models)).
- **Dev and evals** may use the Gemini free tier with synthetic prompts. That is not serving EEA users, but the prompts are used for training.

## Summary of architecture impact (for `feat-012`)

1. **Q6, decided by the evidence:**
   - `LanguageModel` = Pydantic AI (`pydantic-ai-slim[openai,google]`, `NativeOutput`, `output_validator` + `ModelRetry` for the step-2/6 checks).
   - Primary `gpt-6-luna` (`reasoning_effort="none"`), optional fallback `gemini-3.5-flash-lite` on the paid tier via `FallbackModel`.
   - Pin model IDs, and record `model` and `prompt_version` per profile (already in the §5 sketch).
2. **Budget, owner decision:** **zero cost is not possible for the online path in ES** (Q2). Measured cost is `≈ $0.67` per 1,000 queries plus `≈ $1.10` once for 20k profiles via Batch. Set a monthly hard budget on the OpenAI project.
3. **Query steps 2 and 6:**
   - Keep 2 calls.
   - Retry once *with the error fed back* (shown only with a scripted fake so far; check it on a real model in the slice).
   - Truncate tones deterministically.
   - Duplicate or invented picks stay step-6 failures.
   - Keep pitch length and IDs as code checks (P2).
   - Fall back on API errors via `FallbackModel`, whose default is `fallback_on=(ModelAPIError,)`. Verified live for 401 and 503. Verified offline, as exception types only, for 429 and timeout. Other 4xx codes weren't tested.
4. **Ingest:** drop `*stinger` keywords. **Step 4** must filter avoid and intensity before the re-rank (Gotcha 5).
5. **Privacy and age, owner decision:**
   - Add the privacy note to the UI and README (Q2 text). Its retention depends on the provider: 30 days on OpenAI, 55 on paid Gemini.
   - Turn off AI Studio logging on a paid Gemini project. On OpenAI, keep `store` off (Responses API).
   - Decide on the minors question (Q2). It may rule out Gemini, and it means adding an age or consent note.
6. **Q7:** LLM time p95 ≈ 6.3 s (OpenAI) from a laptop; measure from the host in the first slice.
