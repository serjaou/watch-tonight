# Part 6 · The recommendation-quality spike

**Reading time:** about 25 minutes · [Back to the index](README.md) · Previous: [Part 5](05-spike-llm.md) · Next: [Part 7 · Inside the code](07-inside-the-code.md)

> [!NOTE]
> **Key ideas in this part**
> - This spike asked the question the whole product depends on: **will the recommendations be good?**
> - Three answers did most of the work: **choose the right movies** to store (a quality gate), **describe them by feeling** (the LLM profile), and only then **tune the ranking formula**.
> - Before trusting a quality measurement, **measure the measuring tool**. The LLM judge disagreed with itself on 26% of items, so small differences mean nothing.
> - It dropped two "obvious" data sources (IMDb ratings and user reviews), one for licence reasons and one because a test showed no gain.

Full report: [docs/spikes/16-recommendation-signals-and-ranking.md](../spikes/16-recommendation-signals-and-ranking.md) · Decisions: [record 0005](../decisions/0005-closed-vocabulary-mirror-schema.md), [0007](../decisions/0007-embeddings-fastembed-profile-template.md), [0008](../decisions/0008-corpus-gate-and-hybrid-ranking.md)

---

## 1. Why this spike exists: four gaps in "just use vector similarity"

The simplest recommender embeds every movie, embeds your request, and returns the nearest movies. The spike's question file names four ways that goes wrong:

1. **The "1984 problem."** A forgotten 1984 TV movie with 18 votes and a "lighthearted romantic comedy" synopsis can be just as similar to *"something light and romantic"* as *When Harry Met Sally*. Similarity knows nothing about quality.
2. **Broad vs specific requests.** For *"something easy to watch"*, thousands of movies fit, and small similarity differences are noise; quality should decide. For *"a slow-burn sci-fi mystery where a small crew is trapped on a station"*, only a few fit, and similarity should decide.
3. **Which outside data helps?** IMDb ratings? Critic scores? User reviews?
4. **What should the profile contain**, and how do we avoid five movies from the same franchise?

## 2. The data the spike built

| Data | Size | Used for |
|---|---|---|
| **The full catalogue** | 51,527 movies on a subscription in ES, US or BO, with at least 10 TMDB votes. 4,290 TMDB calls, about 4 minutes. | Counting what each quality gate keeps |
| **Pool A** | All 14,478 movies that pass the chosen gate, embedded from their **TMDB text** (title, genres, overview). 17 minutes on the Windows laptop. | Testing ranking at realistic scale |
| **Pool B** | 300 movies with a real **LLM profile** each (`gpt-6-luna`) | Testing profiles, embedding formats, the schema |
| **12 test requests** | From vague (*"exhausted, something light and easy"*) to specific (*"tense submarine or single-location thriller"*), plus a kids request, a Korean one, a 90s one and a Spanish one | All comparisons |
| **A blind LLM judge** | Rates each (request, movie) pair 0, 1 or 2 without knowing which method produced it | Relevance scores |

Total LLM spend: about $0.13.

## 3. Question 1 · Which movies to store: the gate

The catalogue is mostly filler. The spike compared several **admission gates**:

| Gate | Movies kept | Share made before 2000 | From the last 3 years | Weakest old film kept |
|---|---:|---:|---:|---|
| None | 51,414 | 31% | 6,135 | *"MANOS" The Hands of Fate* (rated 2.2) |
| At least 200 votes | 12,421 | 27% | **1,165** (new films starved) | *"MANOS"*, *Troll 2* |
| Votes needed depend on age | 12,554 | 13% | 3,219 | *Jaws: The Revenge* (4.1) |
| **G7 (chosen)** | **14,478** | **17%** | **3,203** | *The Greatest Show on Earth* (6.3) |

**G7 in plain words.** A movie gets in if:

- it has enough votes **for its age**: 20 if it's at most 1 year old, 60 if at most 3, 120 if at most 10, otherwise 200 (new films haven't had time to collect votes);
- its **quality score** is at least 5.0; and
- if it's more than 25 years old, its quality score is at least 6.3 (old films must have *stayed* good).

The **quality score** is a Bayesian average of TMDB ratings ([Part 7](07-inside-the-code.md#2-the-bayesian-quality-score-and-the-gate) shows the formula with numbers). It stops a movie with three 10/10 votes from beating a movie with 5,000 votes averaging 7.6.

**Retention.** When a movie leaves every service, keep it (with an empty `streamable` list). Its profile and vector are already paid for. The spike estimated the storage cost of this, and the owner decided: no deletion job in the MVP; add one if storage passes ~60% of the free tier.

> [!TIP]
> **Reproduced for this checkpoint.** Re-running the gate on the spike's raw catalogue file gives exactly **14,478** movies. The same run shows something the spike didn't report: **Spanish-language films pass the gate less often.** Among movies available in Spain, 44% of English-language films pass, but only 22% of Spanish-language ones; Spanish-language films are 8.8% of Spain's subscription catalogue but 5.1% of the gated corpus. TMDB votes come mostly from English-speaking users. Whether that matters for a product launching in Spain and Bolivia is a product question, listed in the [review](review.md#finding-6-the-corpus-gate-under-represents-spanish-language-cinema).

## 4. Question 2 · Which outside data helps

| Source | What the spike measured | Decision |
|---|---|---|
| **IMDb ratings** (free download) | Joined to 90.7% of movies through Wikidata. But it mostly **duplicates** TMDB (rank correlation 0.83), and would add only 291 movies (2%) to the corpus. Its licence says the data must not be used *"to create any kind of online/offline database of movie information"*. | **Dropped** |
| **Critic scores and awards** (Wikidata, public domain) | Covers 70% of the corpus, but only 40% of films from 2020 on. Rank correlation with TMDB quality is only 0.58, so it is a **different signal**: it separates "critics' darlings" (*It Follows*, *The Babadook*) from crowd-pleasers critics disliked. | **Kept**, internal only, falls back to TMDB quality when missing |
| **User reviews** sent to the LLM while profiling | Profiles of 50 films, with and without up to 3 review excerpts, compared with a stronger model's reference profile. Reviews gave **no gain** (some fields got worse) and cost **+35% tokens**. | **Dropped** (provisionally) |

Two honest caveats the spike itself states about the reviews test: the reference model saw the same input as the "no reviews" version, which biases the test toward it; and well-known films are where a model's own knowledge is strongest. That's why the decision is "provisional" and will be re-checked with your own ratings.

Notice where the IMDb idea came from. The spike's question file (written before the spike) called IMDb the "prime candidate" and estimated the catalogue at 25,000–35,000 movies. Measurement found 51,527 movies and a licence that rules IMDb out. **Questions and estimates written before measuring are hypotheses, not facts.**

## 5. Question 3 · The profile and the "mirror schema"

### The mirror idea

Every field the "understand" step can output must **mirror** a field stored on the movie. If the intent says `max_intensity = 2`, the movie must have an `intensity` field to filter on. If the intent says `audience = kids`, the movie must have something that answers "suitable for kids". No mirror, no filter.

The schema has the three channels you met in [Part 3](03-the-architecture.md#2-one-search-step-by-step): hard filters, meaning, ranking hints. All the values come from **closed vocabularies**: fixed lists the LLM must choose from.

| Field | Allowed values |
|---|---|
| `tone` (1–3) | light, funny, heartwarming, romantic, uplifting, cozy, whimsical, thoughtful, melancholic, dark, gritty, tense, scary, exciting, epic, weird, satirical |
| `pacing` | slow, medium, fast |
| `intensity` | 1 to 5 |
| `viewing_effort` | comfort_background, easy, engaging, demanding |
| `ending_feel` | uplifting, warm_resolved, bittersweet, tense_cathartic, bleak_or_ambiguous |
| `content_warnings` | violence, gore, sexual_content, nudity, strong_language, drug_use, self_harm, animal_harm, child_harm, sexual_violence, horror_scares, flashing_lights |

**Results.** 400 of 400 profiles were valid. All 12 intents were valid and their filters looked right on inspection: *"kids 7 and 10"* → `audience = kids` and `max_intensity = 2`; *"Korean thriller"* → `original_languages = ["ko"]`; *"90s neo-noir"* → years 1990–1999; *"I don't mind subtitles"* → no language filter.

### Two problems the spike found in the data

- **Age ratings are missing for a third of films.** Only 63% of the 300 films have a usable US rating (G, PG, PG-13…). A kids filter on the US rating alone would silently drop a third of the catalogue. The decided rule: use the US rating; if missing, the Spanish one; if both are missing, the profile (intensity at most 2 and no adult content warnings).
- **`viewing_effort` came out almost binary:** 152 "engaging", 140 "easy", 7 "demanding", 1 "comfort_background". The LLM needs clear definitions with examples for each value before this field can carry weight. That's the "profile design" task in the backlog.

### What to embed

| Movie vectors made from | Query vector made from | Relevance of the top 5 (0–2) |
|---|---|---|
| **The LLM profile** (as a template) | The intent's English description | **1.30** |
| The LLM profile | Your raw text | 1.30 |
| The LLM profile | The intent, in the same template | 1.26 |
| TMDB text (title, genres, overview) | The intent's English description | 1.12 |

**The profile is the lever**: +0.14 to +0.18 over TMDB text, the biggest gap measured. The other rows are within noise (next section).

### Measuring the measuring tool

The same 57 (request, movie) pairs happened to be judged twice by the same LLM judge. The two runs **disagreed on 15 of 57 items (26%)**, even though the averages differed by only 0.02 (the flips cancelled out). Conclusion written into the architecture: **differences under about 0.1 between methods are not evidence.**

This is one of the most valuable results of the whole stage, because it calibrates every other number. Without it, "1.30 vs 1.26" would look like a finding.

## 6. Question 4 · Ranking: how many candidates, and what formula

### How deep to search

For broad requests, the good, popular films can sit deep in the similarity ranking (as deep as position 114). The spike measured what share of the final top 25 you'd find if you only fetched the top K by similarity:

| Request type | K = 50 | K = 100 | K = 150 |
|---|---:|---:|---:|
| Broad | 0.85 | 0.91 | **0.94** |
| Medium | 0.91 | 0.94 | 0.94 |
| Specific | 0.96 | 0.96 | 0.96 |

**Decision: K = 150.**

### The formula

```
score = w_sem·similarity + w_qual·quality + w_era·era + w_pop·popularity
```

The weights depend on how specific the request is: broad (0.45 / 0.30 / 0.10 / 0.15), medium (0.60 / 0.20 / 0.10 / 0.10), specific (0.80 / 0.10 / 0.05 / 0.05). [Part 7](07-inside-the-code.md#6-the-hybrid-score) walks through the code.

**Results on Pool A (12 requests, top 5):**

| | Pure similarity | Formula |
|---|---:|---:|
| Judged relevance (0–2) | 1.22 | 1.28 |
| Average quality score | 6.61 | **6.89** |

The relevance gain (+0.06) is **inside the judge's noise**: 8 of 12 requests tied, and one request alone gave most of the gain. The clear effect is on quality.

### A failure the spike found in its own formula

For *"exhausted, something light and easy"*, the formula put *A Brighter Summer Day* (a nearly 4-hour 1991 drama) **first**, and added *High and Low* (1963). Why: highly rated old films get an era factor close to 1, and broad requests put 30% of the weight on quality. **The formula pushes demanding classics into "easy" requests.** The fix needs an effort or runtime signal, and real profiles (Pool A had only TMDB text). This is recorded as a must-fix before trusting the quality weight.

### Two smaller findings

- **Similarity was rescaled per query** (min-max over the K candidates), which made scores depend on K. The design now asks for a fixed scale.
- **Franchise duplicates were rare**: 1 duplicate slot in all 12 top-25 lists. De-duplication stays as cheap insurance, not a measured gain. (The spike also found that its own de-duplication function was never called in the ranking run, and said so.)

## 7. The main lessons

1. **The corpus gate does most of the work on the "1984 problem".** Choosing what to store beats clever ranking.
2. **The profile matters more than the formula.** Describe movies the way users describe moods.
3. **Calibrate your judge before you compare.** 26% self-disagreement sets the noise floor.
4. **Licences and terms are design inputs**, as real as latency.
5. **A spike should report its own failures.** This one reported a formula failure, two bugs in its own scripts, and a biased test setup.

## 8. How sure are we?

This spike ran on Windows with Claude Code. It was not independently audited here, but its central number (14,478 movies after the gate) was **reproduced exactly** from its raw data for this checkpoint. Its reviewer found 21 issues across two rounds. Its limits, as it states them:

- **12 requests** is a small sample, and the judge is from the same model family as the profiles.
- **Pool A had no LLM profiles**, so the formula was never tested together with profile embeddings at scale.
- **The weights are hand-set.** They must be tuned on 30–50 requests labelled by you.
- **The audience fallback rule and the "teens" rule are untested proposals.**
- **The real catalogue churn rate** is still unknown (the next small task).

---

### Questions to think about

- Why does G7 ask *more* of old films (quality ≥ 6.3) but accept *fewer* votes from new ones? What would go wrong with one threshold for everyone?
- The judge disagreed with itself on 26% of items. How would you measure a judge's agreement with *you*? How many labels would you need?
- The formula failed on "exhausted, light and easy". Propose a fix using fields that already exist in the v1 profile.
- Why is "the profile matters more than the formula" good news for a solo project with limited time?
- Should the product care that Spanish-language films pass the gate half as often? What would you check before deciding?

[Back to the index](README.md) · Previous: [Part 5](05-spike-llm.md) · Next: [Part 7 · Inside the code](07-inside-the-code.md)
