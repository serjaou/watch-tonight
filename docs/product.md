# watch-tonight: product

**What this file is:** what the product does, for whom, and where it stops. It holds the product judgment an agent can't infer from the code. Architecture lives in `docs/architecture.md`; per-feature detail lives in `docs/specs/`.
**Owner:** Sergio. Agents may propose changes but never edit this file on their own.
**Status:** draft · **Last updated:** 2026-11-13. Items marked **(to confirm)** are proposals the owner hasn't settled yet. Items marked **(verify)** depend on the Week 1 spike.

---

## 1. Product core

- **Pitch:** describe how you feel tonight and get 5 movies you can stream right now on your services.
- **Primary user:** someone who pays for one or more streaming services and wants to pick a movie for tonight without scrolling for half an hour.
- **Main frustrations removed:**
  - Recommendations are built around genres and popularity, not around people's mood and how their day went.
  - Even when you find something, it often isn't on the services you pay for in your country. Searching the internet for availability doesn't always give accurate information.
- **Quality bar:** availability is never wrong as of the last refresh, and the pitches make you want to watch the movie.
- **Budget:** zero cost by default. A small spend is fine when it clearly improves quality; any recurring cost needs the owner's approval.

## 2. The one task (MVP)

> Describe your mood and preferences (e.g. *"I feel tired and I want to watch something light, maybe a rom-com, but not too dramatic"*). Pick your country and your streaming services. Get **5 movie recommendations you can watch tonight**, each with a short pitch grounded in the movie's data. This happens in a thin web UI, and is also available through the API and an MCP server.

| | |
|---|---|
| **Input** | Free text (mood and preferences, max 500 characters); country; one or more streaming services; optional constraints (e.g. max runtime, "nothing too intense") |
| **Output** | 5 movies. Each has a title, year, runtime, poster **(verify)**, service(s) where it's streamable, a short pitch, a link to its TMDB page, and the availability date |
| **Countries at launch** | ES, US, BO **(verify BO provider coverage)** |
| **Language at launch** | The mood text can be in any language. The UI, movie titles and pitches are in English only, and the UI says so. More languages later (section 8). |

The more detail the user gives, the more specific the results. Vague input (e.g. *"anything"*) still returns results.

## 3. Product rules

Agents must not break these. Each rule should end up backed by a test or an eval.

| ID | Rule |
|---|---|
| P1 | **Never show a title that isn't streamable** (flat-rate subscription, not rent or buy) on one of the selected services in the selected country, according to the last availability refresh. |
| P2 | **The pitch is about the movie, never about the user.** It highlights the qualities of the film that are relevant to the request (tone, pace, setting, performances, themes), stated as facts about the film. It never refers to the user, their mood or their request, and never claims the movie is a good fit for them or will make them feel better. Every fact comes from the movie's data, and there are no spoilers. It is **at most 350 characters** (about 2–3 sentences), so 5 results stay readable on a phone. |
| P3 | **Explicit constraints are respected** (runtime, things to avoid). Breaking one counts as a failure, not as a "less good" result. Constraints set in the UI (picked from fixed options: max runtime, max intensity, content to avoid) are always applied. Constraints the LLM extracts from the free text, once extracted, are applied exactly; how well they are extracted is measured by an eval, not guaranteed. |
| P4 | **The free-text input is at most 500 characters.** Longer input is rejected with a validation message, not silently truncated. |
| P5 | **Attribution is shown as the data sources require** **(verify exact terms in the spike)**: in the UI, the TMDB logo (less prominent than ours) and the notice *"This product uses the TMDB API but is not endorsed or certified by TMDB"*, plus *"Streaming availability by JustWatch"* wherever availability is shown. API and MCP responses include an attribution field. |
| P6 | **Show how fresh the data is:** every response says when availability was last refreshed. |
| P7 | **Ambiguous behaviour is a spec gap, not permission to guess.** If this file or a spec doesn't say what should happen, ask the owner. |

## 4. Response states

| State | When | What the user sees |
|---|---|---|
| **Success** | 5 movies pass P1 and the constraints | 5 results with pitches, attribution and the availability date |
| **Partial** | Fewer than 5 pass (unlikely, but possible with one service in a small market) | The results that pass, plus a short note suggesting to add a service or relax a constraint |
| **Invalid input** | Empty text or more than 500 characters (P4), no service selected, unsupported country | A validation message on the field at fault |
| **Results without pitches** | The search worked, but the LLM fails when choosing and pitching the results, or its output is still invalid after a retry | Up to 5 of the best results that pass P1 and the constraints, without pitches, plus a short note that pitches are temporarily unavailable (and the *Partial* note too if fewer than 5 passed) |
| **Service unavailable** | The LLM can't interpret the request (down, quota exhausted, or its output is still invalid after a retry), or the database or an upstream service is down | A clear error and a "try again later" message. Never silent failure or made-up results. |

## 5. User stories (MVP)

| ID | Story | Acceptance |
|---|---|---|
| US1 | As a user, I describe my mood, pick my country and services in the UI, and get 5 movies | P1, P2, P5 and P6 hold; each result has a poster **(verify)** and a pitch of at most 350 characters (except in the *Results without pitches* state) |
| US2 | I can add constraints such as max runtime or "nothing too intense" | P3 holds: always for constraints set in the UI; for constraints written in the text, measured by the extraction eval |
| US3 | I can ask again and exclude what I've already been shown in this session | No movie repeats within the session |
| US4 | An AI assistant can call the service through MCP | The tool returns the same structured results as the API, including links and attribution |

## 6. Scope

### In scope (MVP)
- The one task (section 2) through a **thin web UI**, a public **API** and an **MCP server**.
- **Mobile-friendly UI:** usable on a phone-width screen (about 375 px) without horizontal scrolling.
- **Fast responses:** p95 latency target **(to confirm after the spike; initial guess: under 10 s)**.
- A daily refresh of streaming availability.

### Out of scope (MVP)
- Series and TV shows: movies only (documentaries are movies and are included).
- Movies available only to rent or buy (see section 8).
- User accounts, personal history and saved preferences.
- Long or complex prompts (P4).
- A sophisticated UI: no animations, themes or design system.
- Native mobile apps, social features, paid data APIs, music.

## 7. Definition of done (MVP)

**Product:**
- US1–US4 acceptance tests pass.
- Deterministic evals (P1, P3 on the constraints as applied, P4, pitch length from P2, every result is a real catalogue movie, output schema) pass at 100% in CI.
- An eval measures how well constraints are extracted from the free text (P3), with a recorded baseline.
- Deployed URL with a working UI.

**Project deliverables:**
- Public repo with a README: architecture diagram, setup, eval results, cost per query and design decisions.
- MCP server documented.
- 3-minute demo video.
- `LEARNING.md` showing what was learned.

## 8. Future enhancements

- **"Movies you like":** the user lists movies they like, to improve the recommendations.
- **Movies to rent or buy:** include them as an opt-in, clearly labelled with their price type.
- Accounts and saved preferences (services, country, things to avoid).
- Links to trailers.
- TV series.
- More languages for the UI, titles and pitches (e.g. Spanish for ES and BO).

## 9. Glossary

| Term | Meaning |
|---|---|
| **Streamable** | Available with a flat-rate subscription on the given service in the given country, according to the last refresh (P1) |
| **Pitch** | The text shown with each movie (at most 350 characters); about the movie, never about the user (P2) |
| **Emotional profile** | The structured description of a movie's tone, pacing, intensity and themes, built offline from its data. Recommendations are based on it |
| **Refresh** | The daily job that updates which movies are streamable where |
