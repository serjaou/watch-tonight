# 0006. Runtime LLM: OpenAI `gpt-6-luna` through Pydantic AI

- **Date:** 2026-11-16
- **Status:** Accepted (owner decisions Q6 and Q14; evidence in feat-011).
- **Context:**
  - The product needs structured output for three calls: understand, re-rank + pitch, and the offline profile. The budget is zero by default (product §1).
  - feat-011 compared the Gemini free tier with low-cost OpenAI models on the real query flow.
  - **`gpt-6-luna`:** 0 schema errors, exact filter extraction on 20/20 runs (10/10 non-English), ≈ $0.00067 per query, p95 ≈ 6.3 s for both calls.
  - **Gemini free tier:** 13% `503` errors and 15 RPM. Its terms bar serving EEA users (ES is a launch country) and, on paid use too, services likely used by under-18s.
  - **Pydantic AI 2.68** replaced about 250 lines of hand-written adapters. It adds validation retries that feed the error back (`ModelRetry`), provider switching by one argument, and offline fakes (`TestModel`, `FunctionModel`).
- **Decision:**
  1. `LanguageModel` is implemented with **Pydantic AI** (`pydantic-ai-slim[openai]`, pinned in `uv.lock`) and **`NativeOutput`**. The default tool-call output mode cost +85 input tokens per call.
     - It uses OpenAI **Chat Completions** (`OpenAIChatModel`, as in the spike), not the Responses API, which stores data for 30 days by default. If the Responses API is ever used, set `store=False`. The privacy note relies on this.
  2. **Model: OpenAI `gpt-6-luna`** with `reasoning_effort="none"`, for the online calls and for enrichment through the **Batch API**. Pin the model ID; never use `-latest` aliases.
     - The Batch path was not exercised in the spikes. Whether it goes through Pydantic AI or the `openai` SDK directly is checked in feat-021.
  3. The step-2 and step-6 checks run as `output_validator`s that raise `ModelRetry`. That gives **one retry with the error fed back**, which matches Q8.
     - This was shown only with a scripted `FunctionModel` (feat-011), so feat-029 (the walking skeleton's real-LLM part; feat-018 was split on 2026-11-24) verifies it on the real model.
     - Purely cosmetic problems are fixed deterministically instead (e.g. truncate tones to 3).
  4. **No second provider.** An OpenAI outage maps to *Service unavailable* (step 2) or *Results without pitches* (step 6). A second OpenAI model behind `FallbackModel` is only a proposal (`docs/backlog.md`, Proposed), because it would change Q8.
  5. Spend is usage-based (≈ $0.67 per 1,000 queries, ≈ $1.03 once for the corpus) and capped by the prepaid balance with auto-recharge off (owner approval, Q6). Never opt in to OpenAI's data-sharing programme.
- **Consequences:**
  - The domain keeps its own `LanguageModel` `Protocol`; Pydantic AI stays in `infra`. Application tests use in-memory fakes; the infra adapter tests use `TestModel` and `FunctionModel`.
  - Set `PYDANTIC_AI_NO_BANNER=1` in services, because v2 prints a banner to stdout.
  - The privacy note names OpenAI (30-day abuse-monitoring retention, no training) and goes with the age note (product §2).
