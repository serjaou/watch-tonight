# Handoff: `feat-011` — Spike: runtime LLM

- **Type:** `spike`
- **Date:** 2026-11-16
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (9 + 6)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
All six questions in `docs/spikes/11-runtime-llm.md` are answered (`status: answered`). Throwaway scripts live in `spikes/11-llm/`.

**Run setup:**
- 2 rounds × 10 queries: 5 English, plus ES, FR, PT, DE and JA.
- Each query runs the real flow: understand → `fastembed` retrieval of the top 40 from the 200 feat-010 TMDB movies → re-rank and pitch → the step-6 checks.
- Plus 20 profile calls.

**Candidates** (from the models lists and pricing/deprecation pages): `gpt-6-luna` (`reasoning_effort=none`) and `gemini-3.5-flash-lite` (thinking `minimal`). `gpt-5.4-nano` over-extracted avoid values in its smoke test and is being deprecated, so it was dropped.

**Spend:** OpenAI ≈ **$0.022**; Gemini $0 (Free Tier). The owner's OpenAI budget is ~$10.

**Answers:**
- **Q1, cost and limits:**
  - `gpt-6-luna`: **$0.00067 per query** ($0.67 per 1,000 queries), $0.11 per 1,000 profiles (≈ $1.10 for 20k via Batch).
  - `gemini-3.5-flash-lite` paid: $0.0026 per query (≈ 4×), $0.45 per 1,000 profiles.
  - Gemini Free Tier: **15 RPM**, read from the 429 `quotaValue`. RPD and TPM aren't published.
  - Gemini free reliability: **9 of 68 attempts got a 503 ("high demand")**. OpenAI had 0 API errors.
- **Q2, data use:**
  - **The Gemini free tier may not serve EEA/UK/CH users** (ES is a launch country), and its prompts are used for training. So the online path cannot be zero cost.
  - **Gemini's terms (paid too) bar services *likely to be accessed* by under-18s.** OpenAI only requires a parent's or guardian's consent for minors.
  - A privacy note is proposed for the UI and README.
- **Q3, structured output:**
  - **0 schema errors in 120 responses.** Every failure was semantic or a 503.
  - `gpt-6-luna`: understand 20/20, re-rank 19/20 (one duplicate pick), profiles 20/20; extraction 20/20 exact, including 10/10 non-English.
  - Gemini: 4-tone outputs over the cap of 3, one extra avoid value, and 503s.
  - Pitches: 0 over 350 chars, 0 P2 flags.
  - Gotchas: google-genai's `response_schema` rejects integer enums (use `response_json_schema`); plain retries without feedback repeat errors; TMDB `*stinger` keywords leak into pitches.
- **Q4, latency, LLM time per query:**
  - `gpt-6-luna`: p50 4,979 / p95 6,304 ms.
  - Gemini: p50 2,940 / p95 4,673 ms, biased low because 503s were logged as 0 ms.
  - Keep the 2 calls separate, because step 4 must run between them.
- **Q5, framework:** **Pydantic AI 2.68.0 with `NativeOutput`** (needs an ADR in feat-012).
  - Provider swap is one argument.
  - `output_validator` + `ModelRetry` retries with the error fed back.
  - The default output retry budget is 1, measured.
  - `FallbackModel` falls back on `ModelAPIError` (401/503 live; 429/timeout offline) and never on invalid output.
  - `TestModel`/`FunctionModel` work offline.
  - Tool-output mode costs +85 (OpenAI) / +342 (Gemini) input tokens.
- **Q6, fallback:** primary `gpt-6-luna`; fallback `gemini-3.5-flash-lite` on the paid tier via `FallbackModel`, if the owner enables billing and the under-18 clause allows it. Free alternatives (Groq, OpenRouter) are listed but not tested.

**Other changes:**
- `.env.example` gains `OPENAI_API_KEY`.
- `docs/conventions.md` gains "Windows notes": UTF-8 I/O, PowerShell quoting and `Get-Content` encoding, `--python 3.13`, and reading CI without `gh`.

**Review:**
- **Round 1** had 9 findings, all fixed:
  - Q1 daily limits;
  - FallbackModel and retry-default claims, now verified offline;
  - Gotcha 3 overstated;
  - Gemini latency logged 503s as 0 ms;
  - a percentile off-by-one;
  - the Gemini cost denominator;
  - Q3 wording;
  - unsourced claims;
  - traceability.
- **Round 2** had 6 findings, all fixed: privacy-note retention per provider, the request count, `--fallback-only` provenance, fallback scope (live vs offline), source labels, and 6.4 s.

## Verification Evidence
```text
$ uv run --no-project --python 3.13 --with openai --with google-genai --with fastembed python -W ignore spikes/11-llm/probe_llm.py --provider openai --model gpt-6-luna --reasoning none --rounds 2 --profiles 20 --tag bench1
[r1] q01-en-tired-romcom understand ok (1 att) ... [r2] q10-ja-heartwarming-anime rerank FAIL (2 att)
[profile] ... 20/20 ok
wrote spikes\11-llm\runs\openai__gpt-6-luna__bench1.jsonl

$ ... probe_llm.py --provider gemini --model gemini-3.5-flash-lite --reasoning level:minimal --rounds 2 --profiles 20 --min-interval 4 --tag bench1
wrote spikes\11-llm\runs\gemini__gemini-3.5-flash-lite__bench1.jsonl
(429 body: quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier, quotaValue '15')

$ uv run --no-project python spikes/11-llm/summarize.py
=== gemini:gemini-3.5-flash-lite:level:minimal
  understand valid 17/20 -> 18/20  p50/p95 956.5/1503.1 ms  in/out 382/103  429-waits 1
  rerank     valid 13/18 -> 17/18  p50/p95 1671.7/2508.0 ms  in/out 4477/349  429-waits 0
  profile    valid 18/20 -> 19/20  p50/p95 1029.0/1731.9 ms  in/out 359/135  429-waits 0
  llm_time_per_query_ms: {"n": 17, "p50": 2939.5, "p95": 4673.4}
  cost_usd: per_query 0.002642, per_1000_profiles 0.4461
=== openai:gpt-6-luna:none
  understand valid 20/20 -> 20/20  p50/p95 1635.4/2658.5 ms  in/out 613/67  429-waits 0
  rerank     valid 19/20 -> 19/20  p50/p95 3258.6/4045.8 ms  in/out 4191/255  429-waits 0
  profile    valid 20/20 -> 20/20  p50/p95 2222.1/2801.2 ms  in/out 580/103  429-waits 0
  extraction: runtime 20/20, avoid exact 20/20, non-English exact 10/10
  llm_time_per_query_ms: {"n": 19, "p50": 4979.1, "p95": 6303.7}
  cost_usd: per_query 0.000668, per_1000_profiles 0.1097, spent_in_this_run 0.0156

$ ... probe_pydantic_ai.py --openai-model gpt-6-luna --openai-reasoning none --gemini-model gemini-3.5-flash-lite --gemini-thinking minimal --min-interval 5
openai tool/native: 6/6 ok; gemini: 2/6 ok, 4x ModelUnavailableError 503
fallback: broken_key_then_openai -> answered_by gpt-6-luna (3075 ms); gemini_free_then_openai 3/3 answered by gemini

$ ... probe_fallback_offline.py   (no network)
fallback_on_default ["ModelAPIError"]; 503/503_http/429/timeout/401 -> secondary answered; invalid output -> 2 calls on primary, no fallback;
retry budget: not passed=2 calls, 0=1, 1=2, 2=3

$ uv run poe check   (2026-11-16 10:35 CET, Windows)
All checks passed! · 14 files already formatted · pyright 0 errors · Contracts: 2 kept, 0 broken · 26 passed
```

## Unverified
- Gemini Free Tier RPD and TPM, and Gemini paid Tier 1 RPM/TPM/RPD. They're not published, and the owner can read them in AI Studio (https://ai.dev/rate-limit).
- Retry with error feedback on a real model; it was shown only with a scripted `FunctionModel`.
- Whether the real `OpenAIChatModel`/`GoogleModel` map SDK 429s and timeouts to `ModelAPIError` subclasses.
- Gemini latency including 503 round trips.
- Facts labelled "from the research report" in the spike doc, which I didn't re-fetch myself.
- CI on the pushed branch.
