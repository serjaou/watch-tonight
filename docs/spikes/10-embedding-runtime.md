---
id: feat-010
type: spike
status: answered   # questions ready -> answered
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
6. **Multilingual.** Input can be in any language (product.md §2). Is a small multilingual model viable (quality on English profiles, size, latency)? It would let the API embed the raw text when the understanding call fails, instead of returning *Service unavailable* (architecture Q8).
   - *Changes:* model choice, a possible fallback in query step 2.

## How
- Throwaway scripts in `spikes/10-embedding/`. Measure options (a) and (b) locally; for (c) and question 3, read the docs and pricing pages and record links and dates.
- Question 1 needs TMDB data: reuse feat-008's sample if it exists, otherwise fetch ~200 movies with `TMDB_API_KEY` in `.env`.

---

## Findings & Evidence

Measured on **2026-11-15** (macOS ARM64, 8-core Apple Silicon CPU, Python `3.13.11`) using [probe_embedding.py](../../spikes/10-embedding/probe_embedding.py), with full machine-readable output in [report.json](../../spikes/10-embedding/report.json) and the 200-movie stand-in corpus in [sample_movies_200.json](../../spikes/10-embedding/sample_movies_200.json) (`200` popular movies from `feat-008`'s TMDB snapshot enriched via `GET /3/movie/{id}?append_to_response=keywords`, averaging `512.6 chars` per profile: `"{title} ({year}). Genres: {genres}. Tagline: {tagline} Overview: {overview} Keywords: {keywords}."`). Each local runtime was executed in its own isolated `uv run --no-project --with ...` subprocess so RSS memory and `site-packages` disk footprints were measured cleanly without cross-contaminating `pyproject.toml` or process arenas.

---

### 1. Quality (`BAAI/bge-small-en-v1.5`, 384-d on 200 TMDB movies across 10 mood queries)

- **Finding:** **Yes — `BAAI/bge-small-en-v1.5` (`384-d`) retrieves coherent, genre- and mood-appropriate neighbours across all 10 written mood queries**, even on un-enriched TMDB stand-in profiles (`overview` + `keywords` + `genres` + `tagline`).
  - **Crucial observation for `feat-016`:** Pure cosine similarity accurately matches semantic mood and themes, but treats keyword-rich synopses of unreleased/obscure titles (e.g., *Scene*, *Digger*, *Ebenezer*) on par with acclaimed classics (*Se7en*, *The Godfather*, *Parasite*, *Back to the Future*). This empirically validates the need for `feat-016`'s hybrid ranking layer (combining vector similarity with Bayesian quality and era/popularity).
  - **Combined with `feat-009` Q1:** `384-d` vectors keep 20,000 movies at **`27.6%`** of Atlas M0's 512 MiB storage limit as JSON arrays or **`17.4%`** (`89.0 MiB`) as BSON Binary `FLOAT32` vectors.
- **Evidence (Top-5 neighbours per mood query from `fastembed` `BAAI/bge-small-en-v1.5` in [report.json](../../spikes/10-embedding/report.json)):**

| Query ID | Mood Query | Top-5 Retrieved Movies (`title (year) — cosine`) | Assessment |
|---|---|---|---|
| `Q01_cozy_animation` | *"warm, comforting animated family adventure with heart, humor, and low stress after a long week"* | 1. *Tad and The Magic Lamp* (2026) — `0.6153`<br>2. *Hoppers* (2026) — `0.5956`<br>3. *The Cat in the Hat* (2026) — `0.5930`<br>4. *A Very Arctic Christmas* (2026) — `0.5920`<br>5. *Toy Story 5* (2026) — `0.5887` | **5/5** warm family/animation/holiday comedies; zero horror/thriller leakage |
| `Q02_cerebral_scifi` | *"mind-bending sci-fi mystery about space exploration, time dilation, and existential survival"* | 1. *Interstellar* (2014) — `0.6282`<br>2. *Klara and the Sun* (2026) — `0.5942`<br>3. *Inception* (2010) — `0.5907`<br>4. *The End of Oak Street* (2026) — `0.5899`<br>5. *Backrooms* (2026) — `0.5864` | **5/5** cerebral sci-fi/mystery (*Interstellar* `#1`, *Inception* `#3`) |
| `Q03_gritty_crime` | *"dark, tense crime drama about mafia loyalty, organized crime corruption, and moral decay"* | 1. *Se7en* (1995) — `0.6539`<br>2. *Scene* (2026) — `0.6443`<br>3. *The Godfather* (1972) — `0.6310`<br>4. *The Cycle* (2026) — `0.6223`<br>5. *Pulp Fiction* (1994) — `0.6216` | Strong crime classics (*Se7en*, *The Godfather*, *Pulp Fiction*) alongside dark thriller/crime entries |
| `Q04_atmospheric_horror` | *"scary supernatural horror or monster thriller with unsettling dread, claustrophobia, and survival terror"* | 1. *Beware Boiúna* (2026) — `0.6782`<br>2. *Onslaught* (2026) — `0.6661`<br>3. *Never After Dark* (2026) — `0.6628`<br>4. *Backrooms* (2026) — `0.6509`<br>5. *Resident Evil* (2026) — `0.6481` | **5/5** horror / monster survival thrillers |
| `Q05_high_octane_action` | *"relentless high-adrenaline action thriller with martial arts, gunplay, or a one-man-army revenge mission"* | 1. *Onslaught* (2026) — `0.6786`<br>2. *The Shadow's Edge* (2025) — `0.6728`<br>3. *Never Surrender* (2026) — `0.6722`<br>4. *War Machine* (2026) — `0.6576`<br>5. *One Last Shot* (2026) — `0.6511` | **5/5** relentless action / revenge thrillers |
| `Q06_romantic_drama` | *"intimate, emotional romantic drama about love, longing, heartbreak, and unforgettable chemistry"* | 1. *Possible Love* (2026) — `0.6410`<br>2. *Your Heart Will Be Broken* (2026) — `0.6309`<br>3. *La Bola Negra* (2026) — `0.6125`<br>4. *Love of Your Life* (2026) — `0.6110`<br>5. *Sense and Sensibility* (2026) — `0.6109` | **5/5** intimate romantic / emotional dramas |
| `Q07_epic_fantasy` | *"epic mythological fantasy quest with ancient magic, fellowship, and massive battles between good and evil"* | 1. *Ramayana: Rise of a Legend* (2026) — `0.6766`<br>2. *The Lord of the Rings: The Return of the King* (2003) — `0.6688`<br>3. *The Odyssey* (2026) — `0.6576`<br>4. *The Lord of the Rings: The Two Towers* (2002) — `0.6230`<br>5. *Dune: Part Two* (2024) — `0.6138` | **5/5** epic fantasy / mythological quests (*LOTR* `#2` & `#4`, *Ramayana* `#1`, *The Odyssey* `#3`, *Dune: Part Two* `#5`) |
| `Q08_dark_satire` | *"sharp, chaotic dark comedy or social satire about wealth, greed, absurdity, and things spiralling out of control"* | 1. *Digger* (2026) — `0.6656`<br>2. *Parasite* (2019) — `0.6442`<br>3. *Forrest Gump* (1994) — `0.6045`<br>4. *Possible Love* (2026) — `0.6022`<br>5. *Pulp Fiction* (1994) — `0.6002` | Surfaces *Parasite* (`#2`), *Digger* (`#1`), and *Pulp Fiction* (`#5`) |
| `Q09_psych_suspense` | *"twisty psychological thriller with paranoia, hidden identities, mind games, and a dark obsession"* | 1. *Inception* (2010) — `0.6153`<br>2. *Obsession* (2026) — `0.6123`<br>3. *Never After Dark* (2026) — `0.6104`<br>4. *Backrooms* (2026) — `0.6047`<br>5. *Disclosure Day* (2026) — `0.6032` | **5/5** psychological suspense / mind-game thrillers |
| `Q10_feelgood_comedy` | *"fun, lighthearted laugh-out-loud comedy or nostalgic adventure that doesn't take itself seriously"* | 1. *Ebenezer* (2026) — `0.5723`<br>2. *Back to the Future* (1985) — `0.5709`<br>3. *Allen* (2026) — `0.5707`<br>4. *Tad and The Magic Lamp* (2026) — `0.5699`<br>5. *Wild Horse Nine* (2026) — `0.5675` | **5/5** comedy / nostalgic adventures (*Back to the Future* `#2`) |

---

### 2. Runtime Options Comparison (`(a)` PyTorch vs `(b)` ONNX `fastembed` vs `(c)` Hosted API / Atlas)

- **Finding:** **Option `(b)` `fastembed` (ONNX Runtime CPU) with `BAAI/bge-small-en-v1.5` (`384-d`) is the clear winner for both the API container and the offline `embed` job.**
  - It is **`4.6x` smaller on disk** (`212.2 MB` added vs `988.4 MB` for PyTorch), uses **`45%` less query-time RAM** (`279.1 MB` RSS vs `509.4 MB`), initializes **`7.1x` faster** (`0.58 s` total import + model load vs `4.15 s`), embeds single queries **`2.0x` faster** (`p50 = 5.04 ms` vs `10.38 ms`), costs **`$0`** with no external rate limits or network round-trips, and produces vectors with **`0.999999` cosine similarity** (`4.9 / 5.0` top-5 overlap) to PyTorch `sentence-transformers`.
- **Evidence (Summary Table from [report.json](../../spikes/10-embedding/report.json) + official docs checked `2026-11-15`):**

| Metric | `(a)` `sentence-transformers` (PyTorch CPU, `bge-small-en-v1.5`) | `(b)` `fastembed` (ONNX CPU, `bge-small-en-v1.5`) — **CHOSEN** | `(c1)` Hosted Gemini API (`gemini-embedding-001`, MRL `384-d`) | `(c2)` Atlas Automated Embedding (`autoEmbed`, Voyage AI) |
|---|---|---|---|---|
| **Added `site-packages` disk** | `860.15 MB` (`torch` CPU + `transformers` + `scipy`) | **`148.16 MB`** (`fastembed` + `onnxruntime` + `tokenizers`) | **`0 MB`** (uses existing HTTP client) | **`0 MB`** (computed inside Atlas) |
| **Model weights on disk** | `128.27 MB` (FP32 SafeTensors) | **`64.07 MB`** (ONNX quantized/optimized) | **`0 MB`** | **`0 MB`** |
| **Total added container size** | **`+988.4 MB`** (`~1.14 GB` on `python:3.13-slim`) | **`+212.2 MB`** (`~360 MB` on `python:3.13-slim`) | **`+0 MB`** (`~150 MB` on `python:3.13-slim`) | **`+0 MB`** |
| **RAM (RSS after import)** | `400.00 MB` | **`87.53 MB`** | `~30 MB` (base Python) | `~30 MB` |
| **RAM (RSS query-time: 1 query)** | **`509.42 MB`** *(OOMs 512 MB hosts once FastAPI is added)* | **`279.06 MB`** *(~340 MB w/ FastAPI — fits 512 MB hosts)* | `~80–100 MB` (FastAPI only) | `~80–100 MB` (FastAPI only) |
| **RAM (RSS batch peak: `batch=64`)** | `658.72 MB` | `720.09 MB` *(offline CLI only; tunable via `batch_size=16..32`)* | `~100 MB` | `n/a` |
| **Cold start (import + load from disk)** | `3.822 s` + `0.323 s` = **`4.15 s`** | `0.405 s` + `0.174 s` = **`0.58 s`** | **`0 s`** local (`~150–250 ms` TLS handshake) | **`0 s`** |
| **Single-query latency (`p50` / `p95`)** | `p50 = 10.38 ms` / `p95 = 11.58 ms` | **`p50 = 5.04 ms` / `p95 = 5.88 ms`** | `~120–300 ms` (network HTTPS RTT) | Included inside `$vectorSearch` |
| **Cost (online + 20k profiles)** | **$0** | **$0** | **$0** on Free Tier; **$0.15 / 1M tokens** on Paid Tier 1 (`~$0.60` per 20k profiles) | **$0** on M0 Preview; usage-billed on production Voyage AI |
| **Free-tier limits / Bottlenecks** | None (CPU-bound), but **cannot fit in 512 MB RAM** | **None** — runs 100% locally in `5 ms` inside 512 MB RAM | **100 RPM · 30,000 TPM · 1,000 RPD** ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)); adds a 3rd network call to every user search | **Preview only** ([docs](https://www.mongodb.com/docs/atlas/atlas-vector-search/automated-embedding/)); embeds a single raw field; `voyage-3` uses 1024-d (`70.5%` of M0 storage) |

- **ONNX vs PyTorch equivalence (`onnx_vs_pytorch_parity` in [report.json](../../spikes/10-embedding/report.json)):**
  - Across the first 20 movie profiles, the cosine similarity between `fastembed` (`BAAI/bge-small-en-v1.5`) and `sentence-transformers` (`BAAI/bge-small-en-v1.5`) is **`min = 0.999998`, `mean = 0.999999`, `max = 0.999999`**.
  - Across the 10 mood queries, top-5 overlap is **`4.9 / 5.0`** (`9/10` queries return the exact same 5 movies in the exact same order; `Q03` differs only at rank `#5` where cosine scores are tied at `0.6216` vs `0.6219`).

---

### 3. Hosting Options (Free Tiers for API, UI, and Daily Job)

- **Finding:** **Google Cloud Run (Always Free Tier)** and **Azure Container Apps (Monthly Free Grant)** are the strongest $0 hosts for the API + daily job, while **Render (Free Hobby Tier)** also works for the API (`512 MB` RAM) if paired with `(b) fastembed` (`~340 MB` total RSS) and **GitHub Actions `schedule:`** for the daily availability refresh job. **Fly.io no longer offers a permanent free tier** for new accounts.
- **Evidence (Official pricing & platform documentation checked `2026-11-15`):**

| Platform | Free Tier Allowance | Max RAM / CPU on Free Tier | Cold Start Behavior | Scheduled Daily Job Support | Which Runtime Options from Q2 Fit? |
|---|---|---|---|---|---|
| **Google Cloud Run** ([pricing](https://cloud.google.com/run/pricing), [scheduler](https://cloud.google.com/scheduler/pricing)) | **180,000 vCPU-s**, **360,000 GiB-s**, **2M requests/month** (Always Free) | **512 MiB – 2 GiB RAM**, **1 vCPU** per instance | Scales to zero (`min-instances=0`); **`~2–4 s`** cold boot with baked `fastembed` image | **Yes ($0):** Cloud Run Jobs + **Cloud Scheduler** (first **3 cron jobs/month free**) | **`(b) fastembed`** (in 512 MiB or 1 GiB) and **`(c) hosted`**; `(a) PyTorch` requires ≥1 GiB (burns GiB-s 2x faster) |
| **Azure Container Apps** ([pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/), [jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs)) | **180,000 vCPU-s**, **360,000 GiB-s**, **2M requests/month** per subscription | **0.5 GiB (`512 MiB`) / 0.25 vCPU** up to **4 GiB / 2 vCPU** | Scales to zero (`minReplicas: 0`); **`~3–6 s`** cold boot with baked `fastembed` image | **Yes ($0):** Native **Container Apps Jobs** (`triggerType: Schedule`) sharing the free grant | **`(b) fastembed`** (fits inside `0.5 GiB` or `1.0 GiB`) and **`(c) hosted`**; `(a) PyTorch` OOMs on `0.5 GiB` |
| **Render** ([free tier docs](https://render.com/docs/free), [pricing](https://render.com/pricing)) | **750 free instance hours/month** (Web Service) + **Free Static Sites** (React UI) | **512 MB RAM**, **0.1 CPU** | Spins down after **15 min** idle; **`~30–60 s`** wake-up on `0.1 CPU` | **No ($1/mo min for Render Cron Jobs)** → run daily job on **GitHub Actions `schedule:` ($0)** | **`(b) fastembed`** (`~340 MB` RSS fits in `512 MB`) and **`(c) hosted`**; **`(a) PyTorch` (`509 MB`+) OOMs** |
| **Fly.io** ([pricing](https://fly.io/docs/about/pricing/)) | **Deprecated permanent free tier** for new orgs (Pay-As-You-Go; informal `<$5` invoice waiver) | `shared-cpu-1x` w/ `256 MB` (`~$2.19/mo`) or `512 MB` (`~$3.69/mo`) | `auto_stop_machines = "stop"` wakes in **`~1–3 s`** | Fly Machines scheduled start or external cron | `(b) fastembed` fits `512 MB` (not `256 MB`); `(c) hosted` fits `256 MB`; excluded as default due to no formal $0 tier |

- **Dockerfile best practice for `(b) fastembed`:**
  - Pre-download the `64.07 MB` ONNX model weights into `/app/.model_cache` during `docker build` (`RUN uv run python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/.model_cache')"` and set `FASTEMBED_CACHE_PATH=/app/.model_cache`).
  - This guarantees that container cold starts **never download weights from HuggingFace at runtime** and initialize the ONNX session from local container disk in **`0.17 s`**.

---

### 4. Batch Cost (Embedding 20,000 Profiles on Laptop CPU)

- **Finding:** Embedding **20,000 profiles** (`avg 512.6 chars`) on the laptop CPU takes **`11.77 minutes` (`706.0 s`, `28.33 docs/s`)** with `fastembed` (ONNX CPU) — or **`3.36 minutes` (`201.5 s`, `99.25 docs/s`)** with `sentence-transformers` (PyTorch multi-core CPU).
  - Because `feat-008` Q7/Q12 proved that only **`1–5` brand-new flat-rate movies/day** (`~20–50/week`) enter the catalogue after the initial seed, the **one-time 20k seed takes ~12 minutes on a laptop CPU** and **weekly incremental `embed` runs take `< 2 seconds`**!
- **Evidence (from [report.json](../../spikes/10-embedding/report.json), `batch_size=64`):**
  - **`fastembed` (`BAAI/bge-small-en-v1.5`, ONNX CPU):**
    - `200` profiles: **`6.85 s`**
    - `1,000` profiles: **`35.29 s`** (`28.33 docs/s`)
    - `20,000` profiles: **`706.0 s` (`11.77 min`)**
  - **`sentence-transformers` (`BAAI/bge-small-en-v1.5`, PyTorch CPU):**
    - `200` profiles: **`2.49 s`**
    - `1,000` profiles: **`10.08 s`** (`99.25 docs/s`)
    - `20,000` profiles: **`201.5 s` (`3.36 min`)**
- **Changes to the `embed` job design ([docs/architecture.md](../architecture.md) §4):**
  1. **Single dependency (`fastembed`):** Keep only `fastembed` in the project dependencies (`pyproject.toml`) so the API container and CLI share the exact same lightweight ONNX runtime (`11.8 min` for a one-time 20k seed is fast enough that adding PyTorch is unnecessary).
  2. **Chunked batching + MongoDB `bulk_write` checkpoints:** Iterate cursor in chunks of **`64`–`128` documents**, call `list(embedder.embed(texts, batch_size=64))`, convert each 384-d vector to BSON Binary `FLOAT32` (`feat-009` Q1), and immediately flush `UpdateOne` operations to MongoDB. If interrupted at document `8,000`, restarting `embed` resumes from document `8,001`.

---

### 5. Changing Models Later (`embedding_model` per document)

- **Finding:** Recording `embedding_model` (plus `embedded_profile_hash`, the SHA-256 of the profile text that was embedded) per document is **necessary for idempotency and resumable backfills**, and supports **two safe model-migration paths**:
  1. **Why you cannot mix two models in one active `$vectorSearch` field without filtering:** An Atlas HNSW index on `embedding` has a fixed `numDimensions` and connects all vectors in a single proximity graph. Even if Model A and Model B are both `384-d`, their vector spaces are incompatible — querying with a Model B vector while half the collection still holds Model A vectors produces garbage similarity scores for the un-migrated documents.
  2. **Migration Path A — Fast In-Place Re-Embed (MVP Default, `< 13 min` window):**
     - Run the `embed` job with `TARGET_MODEL = "new-model-id"`. It queries `{"embedding_model": {"$ne": TARGET_MODEL}}`, re-embeds all 20k stored profiles in **`~11.8 min`** (zero LLM calls needed since the enriched profile text is already stored in MongoDB!), and overwrites `embedding` + `embedding_model` in batches. If `numDimensions` changed, update `movies_vector_idx` (`~50.8 s` rebuild on M0, measured in `feat-009` Q5).
  3. **Migration Path B — Zero-Downtime Blue/Green Field (`embedding_v2`) on Atlas M0:**
     - In `feat-009` Q1, we verified that **Atlas M0 allows up to 3 Vector Search indexes concurrently** and that 20,000 Binary `FLOAT32` 384-d vectors take only **`29.8 MiB`**.
     - Therefore, for zero-downtime migration: (1) backfill `embedding_v2` + `embedding_model: NEW_MODEL`; (2) build a second index `movies_vector_idx_v2` on `embedding_v2` (`50.8 s` on M0); (3) deploy the new API version pointing at `movies_vector_idx_v2` and `embedding_v2`; (4) `$unset` the old field and drop the old index.

---

### 6. Multilingual Model Viability (`paraphrase-multilingual-MiniLM-L12-v2` vs `BAAI/bge-small-en-v1.5`)

- **Finding:** **Do NOT switch to a small multilingual embedding model (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `384-d`). Keep `BAAI/bge-small-en-v1.5` (`384-d`) and rely on Step 2's LLM to translate non-English prompts into English intent summaries (Architecture Q9).**
  - While `paraphrase-multilingual-MiniLM-L12-v2` works cross-lingually on raw Spanish/French/Portuguese queries (`3.25 / 5.0` average top-5 overlap with paired English queries vs `1.5 / 5.0` for `bge-small-en-v1.5`), it suffers from **two dealbreakers**:
    1. **Degrades retrieval quality on English mood queries (100% of normal traffic):** Because its `384-d` capacity is split across 50+ languages, its tonal discrimination on English movie profiles is significantly weaker than `BAAI/bge-small-en-v1.5` — ranking **horror movies (`Buddy`, `Obsession`, `Mickey's Slayhouse`) and `Fight Club` in the Top 5 for cozy family animation (`Q01`), romantic drama (`Q06`), and lighthearted feel-good comedy (`Q10`)**!
    2. **Nearly doubles query-time RAM and breaks 512 MB free hosting tiers:** Its 250k-token multilingual vocabulary table balloons ONNX model disk size **`3.75x`** (`240.46 MB` vs `64.07 MB`) and increases query-time process RSS from **`279.06 MB` to `546.66 MB`**, exceeding `512 MB` free-tier limits on Render Free and 0.5 GiB Cloud Run / Azure Container Apps!
  - Furthermore, if Step 2's LLM call fails completely, raw-text embedding alone still loses constraint extraction (`max_runtime`, `max_intensity`, `avoid` content warnings — Product Rule P3); handling LLM unavailability via a **fallback LLM model/provider in `feat-011`** preserves both English intent translation and P3 constraint extraction without sacrificing embedding quality or container RAM.
- **Evidence (from [report.json](../../spikes/10-embedding/report.json)):**

| Metric | `BAAI/bge-small-en-v1.5` (`384-d` ONNX) | `paraphrase-multilingual-MiniLM-L12-v2` (`384-d` ONNX) |
|---|---|---|
| **ONNX model disk size** | **`64.07 MB`** | `240.46 MB` (`3.75x` larger) |
| **Total added container size** | **`212.2 MB`** | `388.6 MB` |
| **Query-time RAM (RSS after load + 1 query)** | **`279.06 MB`** *(fits 512 MB container)* | **`546.66 MB`** *(exceeds 512 MB container)* |
| **Cold start from disk** | **`0.174 s`** | `0.535 s` |
| **Single-query latency (`p50` / `p95`)** | **`5.04 ms` / `5.88 ms`** | `5.78 ms` / `7.07 ms` |
| **Cross-lingual Top-5 overlap with EN (`ES`/`FR`/`PT`)** | `1.50 / 5.0` (`ES`: `0/5`, `0/5`; `FR`: `3/5`; `PT`: `3/5`) | **`3.25 / 5.0`** (`ES`: `3/5`, `2/5`; `FR`: `4/5`; `PT`: `4/5`) |
| **English mood query tonal accuracy (`Q01`–`Q10`)** | **10/10 clean** (zero horror leakage in cozy/romance/comedy) | **Fails tonal boundaries on `Q01`, `Q06`, `Q10`:**<br>• `Q01_cozy_animation`: ranks `#2` *Buddy* (`Horror`)<br>• `Q06_romantic_drama`: ranks `#1` *Obsession* (`Horror, Thriller`)<br>• `Q10_feelgood_comedy`: ranks `#1` *Buddy* (`Horror`), `#4` *Fight Club*, `#5` *Mickey's Slayhouse* (`Horror`) |

---

## Summary of Architecture Impact (for `feat-012`)

1. **Architecture Q5 (Embedding model & runtime):** Choose **`BAAI/bge-small-en-v1.5` (`384-d`)** running locally via **`fastembed` (ONNX Runtime CPU)** for both the online API container (`p50 = 5.04 ms`, `279.1 MB` RSS, `+212.2 MB` image size) and the offline `embed` job (`28.33 docs/s` = `11.8 min` for 20,000 profiles on laptop CPU, `$0` cost). Bake the `64.07 MB` ONNX model into the Docker image at build time (`cold_start = 0.174 s`).
2. **Hosting choice:** Deploy the API + baked `fastembed` model on **Google Cloud Run (Always Free)** or **Azure Container Apps (Monthly Free Grant)** (with **Render Free** + **GitHub Actions `schedule:`** as a viable zero-cost alternative since `fastembed` stays under `350 MB` total RSS).
3. **Architecture Q8 & Q9 (Multilingual input & Step-2 fallback):** Keep English-only `BAAI/bge-small-en-v1.5` embeddings; handle non-English user prompts via Step 2's LLM intent translation (`Q9`) and protect Step 2 availability with a fallback LLM model/provider (`feat-011`) rather than bloating the container and degrading retrieval quality with a multilingual embedding model.
