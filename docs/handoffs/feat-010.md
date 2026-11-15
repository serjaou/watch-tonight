# Handoff: `feat-010` — Spike: query-time embedding runtime

- **Type:** `spike`
- **Date:** 2026-11-15
- **Machine · Tool:** Mac · Antigravity
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `1 (0)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- Built `spikes/10-embedding/probe_embedding.py` and executed isolated `uv run --no-project --with ...` worker subprocesses against 200 real TMDB movie stand-in profiles (`spikes/10-embedding/sample_movies_200.json`, averaging `512.6 chars`: title, year, genres, tagline, overview, keywords), recording all empirical results in `spikes/10-embedding/report.json`, `docs/spikes/10-embedding-runtime.md` (`status: answered`), and `docs/metrics.md` §1.4:
  - **Q1 (Quality of `BAAI/bge-small-en-v1.5`, 384-d):** Across 10 diverse English mood queries (`Q01`–`Q10`), `BAAI/bge-small-en-v1.5` retrieves coherent, mood- and genre-appropriate top-5 neighbours (`10/10` queries free of tonal/horror leakage; e.g., *Interstellar* `#1` & *Inception* `#3` on cerebral sci-fi `Q02`; *Se7en* `#1`, *The Godfather* `#3` & *Pulp Fiction* `#5` on gritty crime `Q03`; *Return of the King* `#2`, *Two Towers* `#4` & *Ramayana* `#1` on epic fantasy `Q07`). Also empirically confirmed why `feat-016`'s hybrid ranking is needed: pure cosine similarity treats keyword-heavy synopses of unreleased/obscure titles on par with acclaimed classics.
  - **Q2 (Runtime options — PyTorch vs ONNX `fastembed` vs Hosted API / Atlas):**
    - **`(b) fastembed` (ONNX Runtime CPU, `BAAI/bge-small-en-v1.5`) — CHOSEN:** `+212.2 MB` added image size (`148.16 MB` packages + `64.07 MB` weights; **`4.6x` smaller** than PyTorch's `+988.4 MB`), **`279.06 MB` query-time RSS** (vs **`509.42 MB`** for PyTorch `sentence-transformers`), **`0.58 s` cold start** (`0.405 s` import + `0.174 s` load from disk; **`7.1x` faster** than PyTorch's `4.15 s`), **`p50 = 5.04 ms` / `p95 = 5.88 ms`** single-query latency (**`2.0x` faster** than PyTorch's `10.38 ms` / `11.58 ms`), and **`0.999999` mean cosine similarity** (`4.9 / 5.0` top-5 overlap) with PyTorch.
    - **`(c)` Hosted Gemini (`gemini-embedding-001`, MRL `384-d`) & Atlas `autoEmbed`:** `0 MB` container overhead, but Gemini Free Tier caps at `100 RPM`, `30,000 TPM`, and `1,000 RPD` (`$0.15 / 1M tokens` on Paid Tier 1) and adds a 3rd network round-trip (`~120–300 ms`) to every search; Atlas `autoEmbed` (Voyage AI) is Preview-only and embeds a single raw field.
  - **Q3 (Free hosting tiers):** **Google Cloud Run (Always Free)** and **Azure Container Apps (Monthly Free Grant)** both provide `180,000 vCPU-s`, `360,000 GiB-s`, `2M requests/month`, `512 MiB – 2+ GiB` RAM, scale-to-zero (`~2–6 s` cold start with baked `fastembed` image), and free scheduled jobs (Cloud Scheduler 3 free jobs/mo; Container Apps scheduled jobs). **Render Free** (`512 MB` RAM, `0.1 CPU`, `30–60 s` spin-down wake-up) also fits `(b) fastembed` (`~340 MB` total RSS with FastAPI; `(a) PyTorch` OOMs) when paired with **GitHub Actions `schedule:`** for the daily job. **Fly.io** deprecated its permanent free tier for new accounts.
  - **Q4 (Batch cost on laptop CPU):** `fastembed` embeds 20,000 profiles on an 8-core Mac ARM CPU in **`11.77 minutes`** (`706.0 s`, `28.33 docs/s`; PyTorch `sentence-transformers` takes `3.36 min` at `99.25 docs/s`). Because daily new-release delta is only `1–5` movies (`feat-008` Q7/Q12), `fastembed` alone handles both the one-time 20k seed (`~12 min`) and weekly incremental runs (`< 2 s`).
  - **Q5 (Changing models later):** Storing `embedding_model` (and `embedded_profile_hash`) per document enables resumable backfills and supports both (A) fast in-place re-embedding (`~12 min` CPU + `51 s` M0 index rebuild if dimensions change) and (B) zero-downtime blue/green migration via a second field (`embedding_v2`) and a second M0 vector index (`feat-009` Q1 confirmed M0 supports up to `3` vector indexes and 20k `FLOAT32` binary vectors take only `29.8 MiB`).
  - **Q6 (Multilingual viability):** Tested `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (`384-d` via `fastembed` ONNX). While it achieves `3.25 / 5.0` top-5 overlap on Spanish/French/Portuguese raw prompts (vs `1.50 / 5.0` for `bge-small-en-v1.5`), it increases model disk size `3.75x` (`240.46 MB`), pushes query-time RSS to **`546.66 MB`** (exceeding `512 MB` free containers), and suffers severe tonal leakage on English mood queries (ranking horror movies `Buddy`, `Obsession`, and `Mickey's Slayhouse` in the top 5 for cozy animation `Q01`, romance `Q06`, and feel-good comedy `Q10`). **Decision:** Keep English-only `BAAI/bge-small-en-v1.5` and rely on Step 2's LLM to translate non-English prompts into English intent summaries (`Q9`), backed by a fallback LLM provider (`feat-011`).

## Verification Evidence
```text
Mac, 2026-11-15:
$ uv run python spikes/10-embedding/probe_embedding.py
[dataset] Loaded 200 cached movies from sample_movies_200.json
[orchestrator] Running worker 'fastembed-bge-small' via: uv run --no-project --offline --with fastembed --with psutil python /Users/sergio/Sergio/Workspaces/watch-tonight/spikes/10-embedding/probe_embedding.py --worker fastembed-bge-small
[orchestrator] Running worker 'st-bge-small' via: uv run --no-project --offline --with sentence-transformers --with psutil python /Users/sergio/Sergio/Workspaces/watch-tonight/spikes/10-embedding/probe_embedding.py --worker st-bge-small
[orchestrator] Running worker 'fastembed-multilingual-minilm' via: uv run --no-project --offline --with fastembed --with psutil python /Users/sergio/Sergio/Workspaces/watch-tonight/spikes/10-embedding/probe_embedding.py --worker fastembed-multilingual-minilm
[orchestrator] GEMINI_API_KEY is empty in .env; recording documented specs for (c).
[orchestrator] Saved full report to spikes/10-embedding/report.json

$ uv run poe check
Poe => ruff check src tests scripts
All checks passed!
Poe => ruff format --check src tests scripts
14 files already formatted
Poe => pyright
0 errors, 0 warnings, 0 informations
Poe => lint-imports
Contracts: 2 kept, 0 broken.
Poe => pytest -m 'not integration'
..........................                                               [100%]
26 passed in 0.77s

Reviewer subagent (73c27e90-c75a-480f-85a9-c9112dc8b0b5):
Round 1: "No findings"
```
