# Handoff: `feat-018` — Walking skeleton, part 1: search end to end with in-memory adapters

- **Type:** `feature` · spec [docs/specs/18-walking-skeleton.md](../specs/18-walking-skeleton.md) (approved 2026-11-24)
- **Date:** 2026-11-25
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (13 + 3)`: round 1 found 4 medium and 9 low; round 2 confirmed every fix and found 3 low (all fixed after it, see below).
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- **What works:** `POST /search` end to end through `domain` → `application` → `api`, with in-memory adapters (scripted fake LLM, fixed or hash-based embedder, in-memory catalogue and search). No Docker and no API key, so everything runs in `uv run poe check`. `uv run poe serve` runs it locally (Swagger UI at `/docs`) over the 20 fictional fixture films.
- **All 10 acceptance tests of the spec pass** (23 cases with their parameters): success, merged limits re-checked by value, the audience rule, exclusions and one film per collection, partial including zero (no re-rank call), the "couldn't apply" note, results without pitches (5 failure modes), 422 (8 invalid inputs, no port called), 503 (understand or search fails), and the deterministic evals.
- **Code** (all new):
  - `domain/`: `vocabulary.py` (v1 closed vocabulary), `providers.py` (static list, TMDB ids from spike 08 Q5), `movie.py`, `intent.py`, `search.py` (request/response contract, P5 notice), `limits.py` (step 4: one unit per hard limit, the Q16 audience rule, one film per collection), `output_checks.py` (step 6), `ports.py`, `errors.py`.
  - `application/search_movies.py`: steps 2–7 and the five response states; no retry loop (the retry belongs to the part-4 adapter).
  - `infra/memory.py` (in-memory catalogue and search), `infra/fakes.py` (`HashEmbedder`, `EchoLanguageModel`).
  - `api/app.py`: `POST /search`, 422 `invalid_input` and 503 `service_unavailable` bodies.
  - `evals/deterministic/checks.py`: the six evals. They restate the rules instead of importing `src/` logic (review M2), so a bug can't hide in its own check.
  - Tests: `tests/acceptance/test_walking_skeleton.py` + `walking_skeleton_fixtures.py` (written in the session with the owner's permission, 2026-11-24), unit tests in `tests/unit/` (`test_limits.py`, `test_output_checks.py`, `test_search_request_and_api.py`, `builders.py`).
- **Dependencies:** `fastapi`, `uvicorn`; dev `httpx` (as the spec says). `pyproject.toml`: `evals` added to the ruff and pyright paths, pytest `pythonpath = ["."]`, `poe serve`.

## Deviations from the spec (for the owner)
- **No `TestClient`.** The installed Starlette (1.10) types its `TestClient` against a new package, `httpx2` (published by the pydantic org; Starlette's metadata names it), and deprecates `httpx` for it. With `httpx`, `TestClient.post` is untyped under pyright strict. Swapping the dev dependency to `httpx2` was blocked by Claude Code's permission check pending your approval, so the acceptance helper calls the app in memory through `httpx.ASGITransport` (same routing, validation, handlers and serialisation; the reviewer judged it acceptable). **Your decision:** keep `httpx`, or switch to `httpx2`.
- **Small additions found in review:** repeated providers are kept once; `""`/`NR` ratings count as no rating (Q16); a movie without a vector is never a candidate; bounds on the intent's limits (runtime > 0, years 1880–2100 in order, lowercase ISO 639-1 languages); unreadable JSON is reported on `body`; a rejected step-5 answer still counts in the trace's tokens and cost.

## Open questions for the owner (from the review), answered 2026-11-25
- **Unknown request fields (review L2):** today they are ignored, so a misspelled `"maxRuntime": 90` returns 200 without the limit. `extra="forbid"` would make it a 422 naming the field. Product rule P7 makes this your call; I'd recommend forbid, because the constraints rule (P3) says UI limits are always applied.
- **Freshness with zero results (review L8):** P6 says every response says when availability was last refreshed, but the contract carries the date per film, so a zero-result response has none. Options: a top-level `availability_updated_at`, or accept the gap.
- **Answers (owner, 2026-11-25), built in the follow-up PR on branch `feat-018-followups`:** reject unknown fields with 422; add a top-level `availability_updated_at`; `httpx` or `httpx2` left to the agent, which kept `httpx` (the tests don't use Starlette's `TestClient`, so its deprecation doesn't apply; no change needed).

## Notes for the next parts
- **Part 2 (feat-030):** the acceptance helper runs `asyncio.run` per request (a new event loop each time). A shared async Mongo client breaks with that: switch to async tests on one loop. The seed's TMDB calls use `httpx` (kept, 2026-11-25).
- **Part 4 (feat-029):** if the adapter raises after spending tokens (invalid output twice), the usage can't reach the trace, because the port's exception carries none; decide how (e.g. an exception carrying a `Usage`). The trace has no `retries` yet; the adapter decides how it reports them (`docs/metrics.md` updated).

## Verification Evidence
```text
$ uv run poe check   (2026-11-25 10:38 CET, Windows, commit after 414d35a)
Poe => ruff check src tests scripts evals
All checks passed!
Poe => ruff format --check src tests scripts evals
37 files already formatted
Poe => pyright
0 errors, 0 warnings, 0 informations
Poe => lint-imports
Domain layer is independent KEPT
Application layer depends only on domain KEPT
Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration'
95 passed in 8.03s

$ uv run pytest tests/acceptance/test_walking_skeleton.py -q -rA
PASSED test_search_returns_five_streamable_movies_with_pitches_attribution_and_freshness
PASSED test_search_enforces_merged_ui_and_intent_constraints_strictly
PASSED test_search_enforces_audience_certification_and_profile_fallback_rule[kids-expected0]
PASSED test_search_enforces_audience_certification_and_profile_fallback_rule[teens-expected1]
PASSED test_search_excludes_seen_ids_and_deduplicates_collections
PASSED test_search_partial_state_including_zero_results
PASSED test_search_notes_constraints_it_could_not_apply
PASSED test_search_falls_back_to_results_without_pitches[raises|invented-id|duplicate|wrong-count|pitch-too-long]
PASSED test_search_rejects_invalid_input_with_422[empty-text|blank-text|text-over-500|unsupported-country|no-provider|provider-not-in-country|avoid-outside-vocabulary|too-many-exclude-ids]
PASSED test_search_returns_503_when_understand_or_search_fails[understand-fails|search-fails]
PASSED test_deterministic_evals_pass_at_100_percent
(23 passed; the ERROR log lines in the run are the expected logs of the failure tests)
```

**Mutation checks** (each change made by hand, tests run, file restored and diffed):

| Change to the code | Acceptance tests that failed |
|---|---|
| Step 4 trusts the search (no re-check) | limits, exclusions and collections, evals |
| No one-film-per-collection | audience (kids, teens), exclusions and collections |
| Spanish rating checked before the US one | audience (kids, teens) |
| Step-6 guard removed | results without pitches (4 of 5 modes), evals |
| Intensity limit never checked (after review M3) | limits, evals |
| Latest-year limit ignored (after review M3) | limits, evals |
| Merge keeps the looser limit (after review M3) | limits, evals |

**Local server** (`uvicorn scripts.serve_skeleton:app`, real HTTP):
```text
200 success [(9001, 'The Lantern Keeper', ['Netflix']), (9002, 'Paper Comets', ['Disney Plus']), (9003, ...), (9004, ...), (9005, ...)]
trace: {'timings_ms': {'understand': 0.142, 'embed': 0.79, 'retrieve': 3.434, 'check': 0.109, 'pick_and_pitch': 0.069}, 'tokens': {'input': 0, 'output': 0}, 'cost_usd': 0.0}
422 {'state': 'invalid_input', 'errors': [{'field': 'text', 'message': 'Mood prompt must not be empty.'}]}
```
(Run before review round 1, when 9001 streamed on Netflix only; it now lists Netflix and Disney Plus.)

## Unverified
- CI on the PR (not run yet).
- Latency numbers here are in-memory and meaningless for Q7; Q7 is measured in feat-029.
