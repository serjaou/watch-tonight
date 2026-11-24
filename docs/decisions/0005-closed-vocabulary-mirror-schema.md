# 0005. Constraints go through a closed vocabulary that mirrors the movie fields

- **Date:** 2026-11-16
- **Status:** Accepted (owner decisions Q11 and Q16; evidence in feat-016).
- **Context:**
  - P3 says explicit constraints (runtime, things to avoid, intensity, "with my kids") must be respected, and breaking one is a failure.
  - An LLM asked "is this movie OK for kids?" gives answers that can't be tested and vary between calls. A filter on a stored field gives the same answer every time.
  - In feat-016 a `QueryIntent` over a closed vocabulary extracted sensible filters for all 12 test queries, including a Spanish one. For example, "kids 7 and 10" became `audience=kids` + `max_intensity=2`, and "Korean thriller" became `original_languages=["ko"]`. Japanese and other non-English input were tested in feat-011 with a placeholder vocabulary (10/10 runs).
  - The US certification exists for only 63% of films (feat-016 Q3), so a certification-only `audience` filter would silently drop a third of the catalogue.
- **Decision:**
  1. **Step 2 outputs a `QueryIntent` with three channels.** Every field mirrors a stored movie field (architecture §3, §5):
     - hard filters: `max_runtime_minutes`, `max_intensity`, `avoid`, `year_min`/`year_max`, `audience`, `original_languages`;
     - semantic fields: `tone`, `pacing`, `viewing_effort`, `ending_feel`, `humor_style`, `themes`, `semantic_description`;
     - ranking controls: `specificity`, `era_mode`, `acclaim_preference`.
  2. **The enums are closed and shared by the profile and the intent.** v1 values are in spike 16 §5 Q3; the profile design feature anchors their definitions. The LLM may only pick listed values.
     - A constraint with no matching value is never guessed into a nearby value.
     - It goes into `unmapped_constraints`, and the response tells the user it couldn't be applied (Q18).
  3. **Hard filters are applied by the data layer, never by an LLM:** as `$vectorSearch` pre-filters, then re-checked by value in step 4.
     - Spike 09 verified five of the filters together on M0.
     - The `year`, `original_language` and certification filters are verified in feat-030 (the walking skeleton's local Atlas part; feat-018 was split on 2026-11-24).
  4. **`audience`** uses the US certification, else the ES one, else the profile (`intensity` plus excluded content warnings), as in architecture Q16.
     - A missing certification is stored as `null`.
     - If Atlas can't express the rule as one pre-filter (it needs an `$or` with the null case), it is applied in step 4 only.
  5. **The channel-2 fields go to step 5 as context, not as step-4 filters.** Direct field matching lowered relevance in feat-016. It can be revisited with the owner-labelled golden set.
- **Consequences:**
  - Adding a new kind of constraint means changing the schema in three places: the vocabulary, the profile prompt and the intent prompt. That's deliberate.
  - **The v1 list of hard limits is a starting point, not final** (owner, 2026-11-24). Content limits such as genre, director, main cast and keyword flags (e.g. "based on a true story") will be added. Spike feat-026 question 7 decides *how* (an exact mirror field, a required or only preferred genre, or content in the vector text), not *whether*. The code keeps adding a limit cheap: each limit is one intent field, one movie field, one check and one pre-filter clause.
  - How well constraints are extracted is measured by the extraction eval (P3), not guaranteed.
  - Films with no certification can pass a kids filter on their profile alone. That relies on profile quality, which the profile design feature measures.
