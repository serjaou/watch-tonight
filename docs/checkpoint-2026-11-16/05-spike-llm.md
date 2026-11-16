# Part 5 · The LLM spike: which model, how much, how reliable

**Reading time:** about 15 minutes · [Back to the index](README.md) · Previous: [Part 4](04-spikes-foundations.md) · Next: [Part 6 · The recommendation-quality spike](06-spike-recommendation-quality.md)

> [!NOTE]
> **Key ideas in this part**
> - The spike tested the **real query flow** (understand → search → pick and pitch), not a toy prompt.
> - "Structured output" means the provider forces the model's answer to match a JSON schema. Both providers produced **0 schema errors in 120 answers**. Every failure was about *meaning* (a repeated ID, too many tones), or an outage.
> - A retry **without feedback** often repeats the same mistake. A retry **with the error message sent back** is the fix, and Pydantic AI does it for you.
> - The decision (OpenAI only, about $0.67 per 1,000 searches) came as much from **terms of service** as from quality: Gemini's free tier may not serve users in the EU.

Full report: [docs/spikes/11-runtime-llm.md](../spikes/11-runtime-llm.md) · Decision: [record 0006](../decisions/0006-runtime-llm-openai-pydantic-ai.md)

---

## 1. The questions

1. **Limits and cost:** free Gemini vs a cheap OpenAI model. Cost per search, cost to profile 1,000 movies.
2. **Data use:** what happens to the user's mood text at the provider?
3. **Structured output:** does the model reliably return valid JSON for our schemas, including non-English input?
4. **Latency:** how long do the two calls take?
5. **Framework:** what does Pydantic AI add over the plain SDKs?
6. **Fallback:** if the main provider fails, what replaces it?

## 2. How it was tested

The script ([probe_llm.py](../../spikes/11-llm/probe_llm.py)) runs the real flow:

1. **Understand** a mood query into a typed intent.
2. **Embed** the English summary with the model from spike 10, and take the 40 nearest of 200 real TMDB movies.
3. **Pick 5 and pitch**, then run the step-6 checks from the architecture (real IDs, no duplicates, pitch length).

It ran **10 queries × 2 rounds** on each model: 5 in English, and one each in Spanish, French, Portuguese, German and Japanese. Each query has an **expected answer** for its filters (for example, "under 2 hours" must give `max_runtime_minutes = 120`), so extraction accuracy is measured, not eyeballed. The same script then profiled 20 movies.

Total spend: about $0.02.

## 3. The results

| Measure | `gpt-6-luna` (OpenAI) | `gemini-3.5-flash-lite` (Google) |
|---|---|---|
| Cost per search (2 calls) | **$0.00067** (≈ $0.67 per 1,000) | $0.0026 on the paid tier; $0 on the free tier |
| Cost per 1,000 profiles | $0.11 (half with the Batch API) | $0.45 |
| Valid "understand" answers | 20/20 | 17/20 → 18/20 after a retry |
| Valid "pick and pitch" answers | 19/20 | 13/18 → 17/18; **all failures were "503 overloaded"** |
| Filters extracted exactly | 20/20, including 10/10 non-English | Slightly worse ("keine Action" became "violence") |
| Server errors | 0 | 9 of 68 calls (13%) got "503 overloaded" |
| Both calls, p50 / p95 | 5.0 s / 6.3 s | 2.9 s / 4.7 s (biased low: failed attempts counted as 0 ms) |
| Pitches ≤ 350 characters | 95/95 | 85/85 |

A Japanese example. Input: *"今夜は怖くない、心温まるアニメ映画が見たいです。2時間以内でお願いします。"* ("Tonight I want a heartwarming animated film that isn't scary. Under 2 hours, please.") Output from `gpt-6-luna`:

```json
{"input_language": "ja",
 "summary_en": "A heartwarming animated movie with a gentle, non-scary tone…",
 "max_runtime_minutes": 120, "avoid": ["horror_scares"], "max_intensity": 1}
```

## 4. The terms of service mattered as much as quality

This is a good example of a non-technical constraint deciding a technical choice:

- Gemini's terms say: *"You may use only Paid Services when making API Clients available to users in the European Economic Area, Switzerland, or the United Kingdom."* Spain is a launch country, so **the free tier is out** for the online path.
- On the free tier, Google may use the prompts to improve its products, and humans may read them.
- Gemini's terms also bar services *"likely to be accessed by individuals under the age of 18"*, on paid use too. A movie app with "movie night with my kids" queries might count.
- OpenAI's API doesn't train on your data by default, keeps abuse logs up to 30 days, and requires parental consent for minors.

**Owner decisions that followed:** OpenAI only, a small usage-based spend approved and capped by the prepaid balance; the UI shows an age note and a privacy note. ([Product document, audience row](../product.md#2-the-one-task-mvp).)

## 5. What the spike learned about retries

The most transferable lesson:

- When OpenAI repeated a movie ID 4 times in its 5 picks, a **plain retry** (same prompt again) still repeated one ID.
- When Gemini returned 4 tones (the limit is 3), a plain retry returned 4 tones again.

So the proposal is: **retry once, and send the error back** ("you picked ID 1084244 twice; pick 5 different IDs from the list"). Pydantic AI does exactly this with an `output_validator` that raises `ModelRetry`. [Part 7](07-inside-the-code.md#4-structured-output-with-a-validator-and-a-retry) shows the code.

And a design rule came out of it: **fix in code only what is safe to fix.** Too many tones? Keep the first 3, no LLM call needed. A duplicated or invented movie? Not safe to "fix" (dropping it leaves 4 picks), so it stays a failure: retry, then "results without pitches".

## 6. Pydantic AI: what a framework adds

The spike first wrote both providers by hand ([providers.py](../../spikes/11-llm/providers.py), about 250 lines), then rewrote the calls with Pydantic AI ([probe_pydantic_ai.py](../../spikes/11-llm/probe_pydantic_ai.py)):

| Feature | Plain SDKs | Pydantic AI |
|---|---|---|
| Switch provider | Two adapters with different schema quirks | One argument: `OpenAIChatModel(...)` or `GoogleModel(...)` |
| Retry with feedback | Write it yourself | `@agent.output_validator` + `raise ModelRetry("…")` |
| Fakes for tests | Write them yourself | `TestModel` (generates valid data from the type) and `FunctionModel` (you script the reply) |
| Fallback to another model | Write it yourself | `FallbackModel(primary, secondary)` |

One measured detail: the default "tool call" output mode cost +85 input tokens per call on OpenAI and +342 on Gemini, compared with "native" structured output (`NativeOutput`). Small per call, but it's ~14% of an "understand" call, so the decision record picks `NativeOutput`.

> [!TIP]
> **C# comparison.** Pydantic AI is roughly "Semantic Kernel or Microsoft.Extensions.AI, plus FluentValidation, plus a Polly retry policy that passes the validation errors back to the model". `TestModel` is like AutoFixture building a valid object from a type; `FunctionModel` is like a Moq setup that returns scripted replies.

## 7. How sure are we?

This spike was run on Windows with Claude Code and was not part of the independent audit in this checkpoint. A spot-check of its headline numbers against [report.json](../../spikes/11-llm/report.json) matched (cost per search 0.000668, both calls p50 4,979 ms and p95 6,304 ms). Its reviewer found 15 issues across two rounds, and the report labels its own limits. The ones to remember:

- **Small samples.** Latency p95 comes from 19–20 values. With 20 values, the p95 is essentially the second-largest one: one slow call moves it a lot.
- **A simpler prompt than the real one.** It sent 40 candidates with TMDB overviews and a placeholder vocabulary. The real design sends 25 candidates with profile fields.
- **Retry-with-feedback was shown only with a scripted fake,** not on the real model. The walking skeleton checks it.
- **Measured from a laptop in Spain,** not from the hosting region.
- **The Batch API path was never exercised.** Costs for enrichment come from the price list.
- The spike's own summary recommends Gemini as a paid fallback. The **owner later decided "no second provider"**, so read the [decision record](../decisions/0006-runtime-llm-openai-pydantic-ai.md), not the spike summary, for the current decision.

---

### Questions to think about

- Why does "0 schema errors" not mean "0 errors"? Give two examples of answers that were valid JSON but wrong.
- The spike chose to keep two LLM calls although one call would be faster. Could you argue for one call? What would you have to give up?
- If OpenAI is down, users get "Service unavailable". Is that acceptable for a portfolio project? What would change if real users depended on it?
- What is the difference between a filter extracted *wrongly* and a filter *not applied*? Which one does the product rule about constraints guarantee against, and which one is only measured?

[Back to the index](README.md) · Previous: [Part 4](04-spikes-foundations.md) · Next: [Part 6 · The recommendation-quality spike](06-spike-recommendation-quality.md)
