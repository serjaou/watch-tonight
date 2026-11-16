# 0007. Embeddings: `fastembed` bge-small in-process; movies embed their profile

- **Date:** 2026-11-16
- **Status:** Accepted (evidence in feat-010 and feat-016).
- **Context:**
  - **Runtime (feat-010):** `BAAI/bge-small-en-v1.5` (384-d) through `fastembed` (ONNX, CPU) costs:
    - +212 MB image and 279 MB RSS at query time;
    - 0.58 s cold start and p50 5 ms per query.
    - PyTorch needed +988 MB and 509 MB RSS. A hosted embedding API adds a network hop and a free-tier quota.
    - 20k documents embed in ≈ 12 minutes on the Mac (28 docs/s, feat-010). The Windows laptop did 14,478 in 17.2 min (14 docs/s, feat-016), so ≈ 24 min for 20k.
  - **The multilingual model tested** (`paraphrase-multilingual-MiniLM-L12-v2`) was worse on English mood queries and exceeds 512 MB containers. Non-English input is already translated by step 2's `semantic_description` (Q9).
  - **What to embed (feat-016):** movie vectors built from the LLM profile (`template(profile)`) beat vectors built from TMDB text (74 vs 64 judged points, on 300 films and 12 queries). Profile retrieval at corpus scale is still to be confirmed. On the query side, a structured template gave no gain over the plain `semantic_description`.
- **Decision:**
  1. `Embedder` = `fastembed` `BAAI/bge-small-en-v1.5`, 384-d, in-process in the API and the jobs, with the model baked into the image.
  2. **Movies embed `template(profile)`** (`Tone: … | Pacing: … | Effort: … | Ending: … | Humor: … | Themes: … | Summary: …`). **Queries embed `semantic_description`** with the model's query instruction (`query_embed`).
  3. Every document stores `embedding_model`. Changing the model means re-embedding the corpus (≈ 12–24 min on CPU, depending on the machine) and rebuilding the index.
- **Consequences:**
  - The embedder is free, with no quota and no extra network call per query.
  - The API container needs ≈ 512 MB of RAM. That fits Cloud Run, ACA and Render Free (feat-010).
  - Retrieval quality depends on profile quality, which is why profile design is its own feature.
