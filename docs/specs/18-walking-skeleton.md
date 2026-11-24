---
id: feat-018
stories: [US1, US2, US3]
status: draft   # draft -> approved (set by the owner only)
---
# Walking skeleton, part 1: search end to end with in-memory adapters

## Goal
`POST /search` works end to end through `domain`, `application` and `api`, following the [query flow](../architecture.md#3-query-flow-online), with in-memory adapters in place of the database, the embedder and the LLM. It covers the five [response states](../product.md#4-response-states), the deterministic checks of step 4 (*Check and rank candidates*) and step 6 (*Check the LLM's output*), and the six deterministic evals. It needs no Docker and no API key, so all of it runs in `uv run poe check`.

## Acceptance tests (written or approved by the owner)
All in `tests/acceptance/test_walking_skeleton.py`. **Fixtures:** about 15–20 **fictional** films (made-up titles, IDs, availability and profiles), committed next to the tests in `tests/acceptance/`, each built to trigger one rule. The LLM is a scripted fake: each test sets the `QueryIntent`, picks and pitches it returns.

- [ ] **Success.** Given the fixture catalogue and a valid request, when at least 5 films pass, then HTTP 200, `state="success"`, and 5 films streamable on a selected service in the selected country (P1), each with every result field of the contract below and a pitch of at most 350 characters (P2), plus `attribution` (P5), each film's `availability_updated_at` (P6) and a `trace` -> `tests/acceptance/test_walking_skeleton.py::test_search_returns_five_streamable_movies_with_pitches_attribution_and_freshness`
- [ ] **Limits, merged and re-checked.** Given limits set in the UI (`max_runtime`, `max_intensity`, `avoid`) and in the text (the same three, plus `year_min`/`year_max` and `original_languages`, which only the text can set), and a search port that returns candidates breaking them, then the stricter limit applies (lower runtime and intensity, both `avoid` lists combined), step 4 drops every candidate that breaks an applied limit by value, and no returned film breaks one (P3, US2) -> `tests/acceptance/test_walking_skeleton.py::test_search_enforces_merged_ui_and_intent_constraints_strictly`
- [ ] **Audience.** Given `audience` kids or teens, and fixture films with a US rating, only a Spanish rating, or no rating (one with a gentle profile, one with a harsh one), then a film is returned exactly when the [audience rule](../architecture.md#decided-owner-and-spikes-2026-11-13-to-2026-11-16) (Q16) accepts it -> `tests/acceptance/test_walking_skeleton.py::test_search_enforces_audience_certification_and_profile_fallback_rule`
- [ ] **Exclusions and collections.** Given `exclude_ids` and three fixture films in one collection, then no excluded film appears (US3), only the highest-scoring film of that collection is kept, and films without a collection are never deduplicated -> `tests/acceptance/test_walking_skeleton.py::test_search_excludes_seen_ids_and_deduplicates_collections`
- [ ] **Partial, including zero.** Given filters that leave 1–4 films, then HTTP 200, `state="partial"`, those films with pitches, and the partial note. Given filters that leave none, then `state="partial"`, an empty `results` list, the partial note, and the re-rank-and-pitch call is never made -> `tests/acceptance/test_walking_skeleton.py::test_search_partial_state_including_zero_results`
- [ ] **Constraints it couldn't apply.** Given a `QueryIntent` with `unmapped_constraints=["no spiders"]`, then the response carries the note *"We couldn't apply: no spiders"* (Q18), in the success and the partial state alike -> `tests/acceptance/test_walking_skeleton.py::test_search_notes_constraints_it_could_not_apply`
- [ ] **Results without pitches.** Given the re-rank-and-pitch port raises, or returns output that fails the step-6 checks (an ID that isn't a candidate, a duplicate, the wrong number of picks, a pitch over 350 characters), then HTTP 200, `state="results_without_pitches"`, up to 5 valid films in score order with `pitch=null`, the pitches note, and also the partial note if fewer than 5 passed (Q8) -> `tests/acceptance/test_walking_skeleton.py::test_search_falls_back_to_results_without_pitches`
- [ ] **Invalid input.** Given text that is empty or over 500 characters (P4), an unsupported country, no provider, a provider not in that country's list, an `avoid` value outside the vocabulary, or more than 5,000 `exclude_ids`, then HTTP 422 with `state="invalid_input"` naming the field, and no port is called -> `tests/acceptance/test_walking_skeleton.py::test_search_rejects_invalid_input_with_422`
- [ ] **Service unavailable.** Given the understand port raises, or the search port raises, then HTTP 503 with `state="service_unavailable"` and a try-again-later message, never results (Q8) -> `tests/acceptance/test_walking_skeleton.py::test_search_returns_503_when_understand_or_search_fails`
- [ ] **Deterministic evals.** Given the six checks in `evals/deterministic/` (availability P1, limits as applied P3, input bounds P4, pitch length, every result is a catalogue film, response schema), when run over every scenario above plus deliberately bad fake-LLM outputs, then 100% pass. Each check also reports a planted violation, so it can't pass by checking nothing -> `tests/acceptance/test_walking_skeleton.py::test_deterministic_evals_pass_at_100_percent`

## Response contract
```jsonc
// request
{ "text": "...", "country": "ES", "providers": [8, 337],       // 1–500 chars after trim; ES|US|BO; ≥ 1, from the country's list
  "max_runtime": 120, "max_intensity": 3, "avoid": ["gore"],    // optional; avoid from the closed vocabulary
  "exclude_ids": [603] }                                        // optional, ≤ 5,000 (the size spike 09 tested)
// 200
{ "state": "success",                                           // success | partial | results_without_pitches
  "results": [{ "id": 603, "title": "...", "year": 1999, "runtime": 136,
                "poster_url": "https://image.tmdb.org/t/p/w342/....jpg",
                "services": [{ "id": 8, "name": "Netflix" }],     // only the selected services it streams on there
                "pitch": "..." /* or null */, "tmdb_url": "https://www.themoviedb.org/movie/603",
                "availability_updated_at": "2026-11-16T03:00:00Z" }],
  "notes": [{ "code": "partial", "message": "..." }],          // partial | pitches_unavailable | unmapped_constraints
  "attribution": { "tmdb": "This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.",
                   "availability": "Streaming availability by JustWatch" },
  "trace": { "timings_ms": { "understand": 0, "...": 0 }, "tokens": { "input": 0, "output": 0 }, "cost_usd": 0.0 } }
// 422 { "state": "invalid_input", "errors": [{ "field": "text", "message": "..." }] }
// 503 { "state": "service_unavailable", "message": "..." }
```
`id` is the TMDB id; the client sends the ids it has shown back as `exclude_ids` (US3).

## Out of scope
- The database (`mongodb-atlas-local`, the vector index, the pre-filters in Atlas), the seed of spike 16's 300 films, and Q4 on Windows → part 2, `feat-030`.
- The real embedder (`fastembed`), checking `query_embed`, embedding latency → part 3, `feat-028`.
- The real LLM (Pydantic AI + `gpt-6-luna`), the retry that feeds the error back, real tokens and cost, end-to-end latency (Q7) → part 4, `feat-029`.
- The hybrid score (`feat-022`): until then, step 4 orders by similarity.
- Genre, people and other content limits: they will be added after spike `feat-026` question 7 decides how (owner, 2026-11-24); this slice uses the v1 `QueryIntent` ([ADR 0005](../decisions/0005-closed-vocabulary-mirror-schema.md)).
- Ingest and the real provider list (`feat-020`).

## Design notes (with C# comparison)
- **Split** ([checkpoint finding 7](../checkpoint-2026-11-16/review.md#finding-7-keep-the-walking-skeleton-thin); owner, 2026-11-22 and 2026-11-24): part 1 in-memory (this spec), part 2 Atlas (`feat-030`), part 3 real embedder (`feat-028`), part 4 real LLM (`feat-029`). Each part is observable through `POST /search`.
- **Who writes the code** (owner, 2026-11-22): the agent writes the slice; afterwards the owner and the agent run a `/defend` session on it, and the owner refactors or extends a module.
- **Layers** ([architecture §2](../architecture.md#2-layers-and-ports)):
  - `domain`: the v1 vocabulary as `Literal` types; `Profile`, `Movie`, `QueryIntent` (with `unmapped_constraints`), the request, response and trace models; the static provider list (a few main services per country); the ports as `Protocol`s (`CandidateSearch`, `MovieRepository`, `LanguageModel`, `Embedder`); and the **check functions**: step 4 (every limit by value, the audience rule, one film per collection) and step 6 (picks and pitches). Pure functions, no I/O. A `Protocol` is like a C# interface that a class satisfies by its shape, without declaring `: IMyInterface`.
  - `application`: `SearchMovies`, the seven steps of the query flow.
  - `infra`: the in-memory catalogue and search (same filter meaning as the Atlas pre-filter, cosine similarity), and a deterministic fake embedder (a vector derived from a hash of the text). Both stay as fast test doubles after parts 2 and 3.
  - `api`: FastAPI `POST /search`; `Depends` wires the adapters (like ASP.NET Core DI). Locally, `uvicorn` serves it with the in-memory adapters and the fixture films.
- **Where the retry lives** (owner, 2026-11-24): the check functions live in `domain`. In part 4 the Pydantic AI adapter calls them inside its output validators, which gives the one retry with the error fed back ([ADR 0006](../decisions/0006-runtime-llm-openai-pydantic-ai.md)). `SearchMovies` runs them again on whatever the port returns, as a final guard. So in this slice the LLM port either returns output or raises, and `application` has no retry loop. In C# terms: the retry policy sits on the client (like Polly on an `HttpClient`); the validation sits in the service.
- **The list of hard limits will grow** (owner, 2026-11-24): genre, director, main cast and keyword flags come later ([ADR 0005](../decisions/0005-closed-vocabulary-mirror-schema.md)). Build each limit as its own unit (intent field, movie field, merge rule, check function, pre-filter clause), so adding one is additive and doesn't change the others.
- **Tokens and cost:** the LLM port returns them with each call, and `trace` adds them up. The fake returns fixed numbers.
- **Zero candidates** (owner, 2026-11-24): `partial`, an empty list, no re-rank call (architecture, step 5).
- **Attribution** (owner, 2026-11-24): the wording from section 3 of TMDB's terms, now in [product.md P5](../product.md#3-product-rules).
- **Evals:** `evals/` is new. Add it to the ruff, pyright and pytest paths; the PR gate already protects it. Part 4 re-runs the same checks on the real model.
- **New dependencies:** `fastapi` (the web framework; it brings Pydantic, which `domain` uses for its models because Pydantic does no I/O, like data annotations on a C# domain model) and `uvicorn` (the server that runs it, like Kestrel); dev: `httpx` (FastAPI's `TestClient` needs it, like `WebApplicationFactory`).

## Open questions (must be empty before status: approved)
- None
