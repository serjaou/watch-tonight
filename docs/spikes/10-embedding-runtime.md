---
id: feat-010
type: spike
status: questions ready   # questions ready -> answered
timebox: 2 sessions
---
# Spike: query-time embedding runtime (model, container size, free hosting)

## Why
Every query embeds its intent summary, so the API needs the embedding model at runtime, and it must be the same model that embedded the profiles. A local model in the API container may not fit a free host's memory. Architecture open question Q5.

## Questions
Each answer: the finding, plus evidence (measurements, docs links).

1. **Quality.** With an English small model (e.g. `bge-small-en-v1.5`, 384-d), do mood-style queries find sensible neighbours? Use overviews + keywords of ~200 movies as a stand-in for profiles, and 10 written queries.
   - *Changes:* model choice, vector size in the data model.
2. **Runtime options.** For each of:
   - (a) `sentence-transformers` with PyTorch;
   - (b) an ONNX runtime (e.g. `fastembed`);
   - (c) a hosted embeddings API (Gemini, or embeddings computed by Atlas);

   what are the container image size, RAM, cold start, latency per query, cost and free-tier limits?
   - *Changes:* the `Embedder` adapter, the API image.
3. **Hosting.** Which free tiers could run the API, the UI and a daily job (candidates: Azure Container Apps, Fly.io, Render, Cloud Run)? With what RAM, CPU, cold starts and scheduled-job support? Which runtime options from question 2 fit?
   - *Changes:* hosting choice (product DoD: deployed URL).
4. **Batch cost.** How long does embedding 20k profiles take on a laptop CPU with the chosen runtime?
   - *Changes:* the embed job's design (batching, resumability).
5. **Changing models later.** Changing the model means re-embedding everything. Is recording `embedding_model` per document enough to migrate safely (e.g. embed into a new field, then switch)?
   - *Changes:* data model, embed job.

## How
- Throwaway scripts in `spikes/10-embedding/`. Measure options (a) and (b) locally; for (c) and question 3, read the docs and pricing pages and record links and dates.
- Question 1 needs TMDB data: reuse feat-008's sample if it exists, otherwise fetch ~200 movies with `TMDB_API_KEY` in `.env`.
