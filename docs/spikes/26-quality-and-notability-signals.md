---
id: feat-026
type: spike
status: questions ready   # draft -> questions ready (owner, 2026-11-21) -> answered
timebox: 2 sessions
---
# Spike: quality and notability signals beyond TMDB, and a more generous corpus gate

## Why

The corpus gate decides which films can **ever** be recommended. Today it uses only TMDB votes and ratings (gate G7, [decision record 0008](../decisions/0008-corpus-gate-and-hybrid-ranking.md)). The [2026-11-16 checkpoint](../checkpoint-2026-11-16/review.md) found two problems:

1. **It drops well-known, watchable films.** 1,129 films have enough votes but are excluded only because of their rating; 225 of them have 1,000 votes or more. Most fail the rule "older than 25 years needs a quality score of at least 6.3". Examples: *Mission: Impossible II*, *Antz*, *Stuart Little*, *Waterworld*, *Deep Impact*, *Mad Max Beyond Thunderdome*, *The World Is Not Enough*, *Dune* (1984), *Scream 3*, *Charlie's Angels*. A wrong exclusion is invisible and permanent: nobody ever sees the film.
2. **It trusts one audience.** TMDB voters are not the whole audience we target.

### The owner's principles for the gate (2026-11-21)

- **Be generous.** These films are already on a subscription service, so they have passed a first selection. Storage is not a reason to be strict (see the table below).
- **The gate removes filler, not mediocre films.** Quality is judged per request by the ranking.
- **Popularity first.** How many people saw a film (or want to) is the safest first signal: vote counts, box office, lasting notability.
- **Ratings with caution.** Audience ratings punish light, simple films that are fun to watch. Use them to rank, and to exclude only films that are clearly bad.
- **Critics only to prioritise.** Critic scores raise films in the ranking. They never exclude a film, unless it is extremely bad.
- **Old and mediocre can go, but not old and popular.** Films older than 25 years with mediocre ratings can be left out **only if few people know them**. *Mission: Impossible II* (2000, rating 6.1, 7,967 votes) must stay in.
- **Several sources and categories.** Audience opinion, critics, commercial reach, cultural notability and current interest are kept apart, as Rotten Tomatoes keeps critics and audience apart. Wikidata is used **together with** TMDB, not only as a fallback. None of this needs an LLM.
- **An English-language bias is acceptable.** The owner accepts, and even prefers, a corpus biased toward English-language films. Coverage is measured by era and country only.

## What we already know

- **Catalogue:** 51,527 films on a subscription in ES, US or BO with at least 10 TMDB votes; 51,414 have a poster and an overview (spike 16, `spikes/16-recommendation/data/catalog.jsonl`, gitignored, on the Windows laptop only).
- **Why films fail G7 today** (recomputed 2026-11-20 from that file, pinned constants C = 6.08, m = 50):

  | Reason | Films |
  |---|---:|
  | Too few votes for their age | 25,575 |
  | Too few votes, and older than 25 years with quality below 6.3 | 9,692 |
  | **Only** older than 25 years with quality below 6.3 | 843 |
  | Other (quality below 5.0, combinations) | 826 |

- **Gentler rules for old films, measured on the same file (2026-11-21):**

  | Rule for films older than 25 years with quality below 6.3 | Corpus | Added vs G7 | Storage (estimate) |
  |---|---:|---:|---:|
  | Excluded (G7 today) | 14,478 | — | ~102 MiB |
  | Kept if ≥ 2,000 votes | 14,544 | +66 | ~102 MiB |
  | Kept if ≥ 1,000 votes (keeps *Mission: Impossible II*) | 14,656 | +178 | ~103 MiB |
  | Kept if ≥ 500 votes | 14,844 | +366 | ~105 MiB |
  | Rule removed | 15,321 | +843 | ~108 MiB |

  Removing the rule completely also lets in obscure titles such as *Clownhouse*, *Phantasm III* and *Omen IV*. All options cost at most ~6 MiB, so **the choice is about what gets in, not about space**.
- **Clearly bad films stay out.** 12 films have quality below 5.0 despite 2,000 votes or more: *Fantastic Four* (2015), *Batman & Robin*, *The Last Airbender*, *Death Note* (2017), *Catwoman*, *Scary Movie 5*, *Movie 43*, *Zoolander 2* and 4 more. They stay excluded unless the owner decides otherwise.
- **Signals already measured in spike 16:** IMDb mostly repeats TMDB (rank correlation 0.83), and its licence rules it out (re-checked 2026-11-20: *"personal and non-commercial use"*, and not *"to create any kind of online/offline database of movie information"*). Wikidata critic scores are a different signal (rank correlation 0.58 with TMDB quality), covering 70% of G7 films but only 40% of those from 2020 on.
- **Limits:**
  - **Storage:** the free database tier has 512 MiB in total. At the current size estimate (≈ 7 KiB per film, still to be re-measured), 14.5k films ≈ 20%, 25k ≈ 34%, and all 51k ≈ 71%.
  - **Money:** OpenAI profiling costs ≈ $0.00007 per film with the Batch API and ≈ $0.00014 without. It is paid again for every film each time the profile prompt changes.

## Questions

1. **Sources and licences.** Which free sources can a public, non-commercial app use, and what does each give?
   - Candidates:
     - **TMDB:** rating, vote count, daily popularity, box-office revenue and budget (same per-movie call).
     - **Wikidata (CC0):** critic scores (Rotten Tomatoes %, Metacritic), awards and nominations, box office, and the number of Wikipedia language editions with an article about the film.
     - **Wikipedia page views** (Wikimedia API or monthly dumps): long-term interest.
     - **Trakt:** ratings, watcher counts.
     - Any other found during the spike.
   - For each: the licence or terms (quoted, with link and date), how to get it (bulk download, SPARQL query or per-film API), rate limits, and how often it changes.
   - *Changes:* which signals the ingest job collects, attribution text, `docs/architecture.md` §4–§5.
2. **Coverage.** For each signal, what share of the 51,414 films has it, by release era (pre-1970, 1970s … 2020s) and by launch country (ES, US, BO)?
   - *Changes:* whether a signal can be used in the gate (needs broad coverage) or only in the ranking (with a fallback when missing).
3. **Distinctness.** How similar is each signal to TMDB's quality score, and to the others (rank correlation)? Which category does each belong to (audience opinion, critics, commercial reach, cultural notability, current interest)?
   - *Changes:* which signals are worth keeping. A signal that repeats another adds cost, not information.
4. **The gate.** Following the owner's principles above, which gate admits the films we want without letting filler back in?
   - **Candidates** (the agent proposes them; their thresholds are part of the question):
     - **A:** G7, but old films below 6.3 are kept when popular (≥ 1,000 votes is the starting point).
     - **B:** G7 with the old-film rule removed.
     - **C:** A, plus other popularity signals for films that fail the vote rule. A film gets in if, for example, its box office or its number of Wikipedia languages is high enough, even with few TMDB votes.
   - In every candidate: the admission data checks stay (overview, poster, runtime > 0, at least one genre); clearly bad films (quality below 5.0) stay out; critic scores never exclude.
   - For each candidate: how many films it adds and removes compared with G7, by era and country, and what it does to the 225 well-known films above.
   - **The owner rates short samples**, answering yes / no / unsure to "would I be happy to see this recommended, for some mood?":
     - about 40 random films the candidate **adds**;
     - about 20 films it still **excludes**, chosen just below its thresholds;
     - any films G7 kept that the candidate **removes**.
   - **Target (agent's proposal; the owner may change it):** at least 80% "yes" on the films a gate adds, and mostly "no" on the films just below its thresholds.
   - *Changes:* the gate in decision record 0008 and architecture §4, corpus size.
5. **Size, cost and refresh.** For the chosen gate:
   - corpus size, and its share of the free tier, **re-measured with realistic documents** (the current per-film size comes from synthetic data);
   - one-time profiling cost, with and without the Batch API, and the cost of re-profiling after a prompt change;
   - extra calls in the daily job, and how often each signal needs refreshing (daily, monthly, rarely).
   - *Changes:* whether it fits the free tier and the budget; the retention and eviction rule.
6. **Ranking inputs (proposal only).** Which signal or signals should drive quality for each preference the intent can express: *crowd-pleaser*, *critically acclaimed*, *hidden gem*, *any*? How should missing values be handled?
   - The weights are tuned later, against the owner's golden set, in the ranking-and-evals task (feat-022). This spike only proposes the inputs.
   - *Changes:* the inputs of the step-4 score (decision record 0008).
7. **Content in the search.** Can the search handle content requests ("an action movie", "a heist set in Paris", "based on a true story", "a Christopher Nolan film") by combining two ideas: **exact mirror fields** for facts (genres, director, main cast; all from TMDB, no LLM), and **content in each movie's vector text** (genres, TMDB keywords, a one-line premise next to the profile)? Two risks must be tested explicitly:
   - **7a · Dilution.** Adding content to the vector text may weaken the mood signal (spike 16 found TMDB text alone worse than the profile alone: 1.12 vs 1.30).
     - Test: compare "profile only" with "profile + content" on spike 16's 12 requests and on about 10 content requests.
     - Pass condition: content requests improve, and mood requests don't drop by more than the judge's noise (about 0.1).
   - **7b · Over-filtering by genre.** TMDB's 19 genres are coarse: "feel-good" is not a genre, and "rom-com" is two (Romance + Comedy).
     - Test: for each content request that names a genre, compare a **hard filter** (only that genre), a **boost** (that genre ranks higher) and **nothing**.
     - Count the relevant films the hard filter removes, and list the words that don't map cleanly to a TMDB genre.
     - Expected outcome: a rule for when the intent marks a genre as **required** ("only horror") and when as **preferred** ("an action movie").
   - **7c · Which content fields become exact mirror fields** (genres, director, main cast, keyword flags such as "based on a true story"), and how the intent expresses them.
   - **Content requests (draft; the owner edits this list):** "an action movie that critics liked", "a heist movie", "something based on a true story", "a Christopher Nolan film", "a movie with Meryl Streep", "a time-travel movie", "a courtroom drama", "a Christmas movie for the family", "a sports underdog story", "a horror comedy".
   - Method: re-use spike 16's 300 profiled films (check first that the pool has matches for each request) and the same blind judge.
   - *Changes:* the embedding template (decision record 0007), the mirror schema and the intent (decision record 0005), architecture §3 and §5.

## How

- Throwaway scripts in `spikes/26-quality-signals/`, never `src/`.
- Re-use spike 16's catalogue. `data/catalog.jsonl` exists only on the Windows laptop; on the Mac, re-create it with `spikes/16-recommendation/catalog.py` (about 4 minutes, TMDB only).
- Wikidata through bulk SPARQL queries keyed by TMDB ID, as spike 16 did. Page views from monthly dumps or a sample, not 50k individual calls, unless the API's rate limit allows it comfortably.
- Every number in the report says whether it is **measured**, **estimated** or **from documentation** (with link and date), and points to its raw output file. Commit each script together with the output it produced (checkpoint review, finding 3).
- **Cost:** $0 for questions 1–6 (no LLM). Question 7: about $0.01–0.05 (judging, and re-embedding 300 films locally for free).
- **Owner time:** about 30 minutes to rate the question 4 samples, plus editing the content requests in question 7.
- **Order (owner, 2026-11-21):** after the walking skeleton (feat-018) and the reviewer spike checklist (feat-027, so this spike is reviewed with it), and before profile design (feat-019), which depends on question 7. It must also be answered before the ingest task (feat-020), because it changes the gate. It does not block the walking skeleton, which uses a fixed set of 300 films.

## Out of scope

- Tuning the ranking weights (feat-022, with the golden set).
- IMDb data in any form (licence; re-checked 2026-11-20).
- Coverage or balance by the film's original language (an English-language bias is accepted; owner, 2026-11-21).
- Paid data sources, unless the owner approves one after question 1.
- Changing the launch countries.

## Findings & Evidence

_Empty until the spike runs._
