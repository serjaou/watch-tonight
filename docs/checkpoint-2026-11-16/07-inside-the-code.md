# Part 7 · Inside the code: six worked examples

**Reading time:** about 30 minutes (best with the files open next to it) · [Back to the index](README.md) · Previous: [Part 6](06-spike-recommendation-quality.md) · Next: [Part 8 · Concepts and questions](08-concepts-and-questions.md)

> [!NOTE]
> **Key ideas in this part**
> - Six short pieces of real code, from the harness and from the spikes, each tied to a decision you've read about.
> - Every example has a "C# comparison" and a "watch out" note.
> - The spike code is throwaway, but the **ideas** in it (the Bayesian score, the closed vocabulary, the retry with feedback, the filtered search, the hybrid score) will be rebuilt in `src/`. Understanding them now makes the walking-skeleton review much easier.

The excerpts below are shortened, and some comments were added for this guide. The linked files have the full, original code.

| # | Example | File | Why it matters |
|---|---|---|---|
| 1 | The Stop hook | [scripts/hooks/stop_gate.py](../../scripts/hooks/stop_gate.py) | The harness's main automatic gate |
| 2 | The Bayesian quality score and the gate | [spikes/16-recommendation/corpus.py](../../spikes/16-recommendation/corpus.py) | Decides which movies exist in the product |
| 3 | A closed vocabulary as Python types | [spikes/16-recommendation/schemas_v1.py](../../spikes/16-recommendation/schemas_v1.py) | Makes constraints testable |
| 4 | Structured output with a validator and a retry | [spikes/11-llm/probe_pydantic_ai.py](../../spikes/11-llm/probe_pydantic_ai.py) | How the LLM calls stay safe |
| 5 | Filtered vector search | [spikes/09-atlas/probe_atlas.py](../../spikes/09-atlas/probe_atlas.py) | The heart of the "R" in RAG |
| 6 | The hybrid score | [spikes/16-recommendation/rank_eval.py](../../spikes/16-recommendation/rank_eval.py) | How candidates are ordered |

---

## 1. The Stop hook: one script, two dialects

**File:** [stop_gate.py](../../scripts/hooks/stop_gate.py), function `main` (line 107).

When the agent tries to end its turn, the AI tool runs this script and sends it a JSON message on standard input. The script decides: may the agent stop?

```python
def main() -> None:
    os.chdir(REPO_ROOT)
    payload = read_payload()
    claude = payload.get("hook_event_name") == "Stop"      # which tool is calling?

    termination_reason = payload.get("terminationReason", "NO_TOOL_CALL")
    if termination_reason != "NO_TOOL_CALL":                 # Antigravity: user cancelled, etc.
        respond(allow=True, claude=claude)
        return

    if not has_code_changes():                               # Q&A or docs only: never block
        COUNTER.unlink(missing_ok=True)
        respond(allow=True, claude=claude)
        return

    result = run(cmd)                                        # uv run --no-sync poe check
    if result.returncode == 0:
        COUNTER.unlink(missing_ok=True)
        respond(allow=True, claude=claude)
        return

    attempts = int(COUNTER.read_text().strip()) + 1 if COUNTER.exists() else 1
    if attempts > MAX_ATTEMPTS:                              # give up after 3: hand back to the owner
        ...
```

**What to notice:**

- **One script, two answer formats.** `respond()` prints `{"decision": "block"}` for Claude Code, and `{"decision": "continue"}` for Antigravity. The rest of the logic is shared. This is the "one source of truth" decision in code.
- **A counter file** (`.harness/stop_gate_attempts`) remembers failed attempts between runs, because each hook run is a new process. It's deleted when the check passes.
- **It only blocks when watched folders changed** (`src`, `web`, `tests`, `scripts`, `pyproject.toml`), compared with `origin/main`. That's why it never blocked during the spikes.
- **Reading the input safely on Windows** (`read_payload`, line 90): `sys.stdin.buffer.read().decode("utf-8-sig")` reads raw bytes and decodes them as UTF-8, dropping the BOM that PowerShell 5.1 adds.

> [!TIP]
> **C# comparison.** `Path(__file__).resolve().parents[2]` is like `Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", ".."))`: "two folders up from this file". `subprocess.run(cmd, capture_output=True, encoding="utf-8")` is `Process.Start` with `RedirectStandardOutput = true` and `StandardOutputEncoding = Encoding.UTF8`.

> [!WARNING]
> **Watch out.** In Python, `subprocess.run(..., text=True)` without `encoding=` uses the operating system's default code page. On Windows that's cp1252, which crashes on UTF-8 output. Always pass `encoding="utf-8"`.

## 2. The Bayesian quality score and the gate

**File:** [corpus.py](../../spikes/16-recommendation/corpus.py), function `wr` (line 59) and the gates (from line 154).

```python
def wr(rating: float, votes: int, c: float, m: float) -> float:
    """IMDb-style Bayesian weighted rating: shrinks low-vote ratings towards the mean C."""
    return (votes / (votes + m)) * rating + (m / (votes + m)) * c
```

**In words:** the score is a weighted mix of the movie's own rating and the average rating of all movies (`C`). The more votes a movie has, the more its own rating counts. `m` is the number of votes at which the two count equally. In the spike, `C = 6.08` (the catalogue average) and `m = 50` (the median number of votes).

**Worked example:**

| Movie | Rating | Votes | Own weight `v/(v+m)` | Score |
|---|---:|---:|---:|---:|
| A | 9.0 | 3 | 3/53 = 0.06 | 0.06 × 9.0 + 0.94 × 6.08 = **6.25** |
| B | 7.6 | 5,000 | 5000/5050 = 0.99 | 0.99 × 7.6 + 0.01 × 6.08 = **7.59** |

Movie A's 9.0 from three votes is mostly pulled back to the average. Movie B keeps almost all of its 7.6.

**The gate G7** is a dictionary entry whose value is a small function:

```python
"G7 age-aware tmdb (old>=200) + WR>=6.3 if age>25, WR>=5.0 all": lambda m: (
    m["vote_count"] >= age_votes([(1, 20), (3, 60), (10, 120), (999, 200)])(m)
    and m["wr_tmdb"] >= 5.0
    and (m["age"] <= 25 or m["wr_tmdb"] >= 6.3)
),
```

`age_votes(...)` is a **function that returns a function**: given the thresholds, it builds `need(movie)`, which returns how many votes that movie needs for its age.

> [!TIP]
> **C# comparison.** The `gates` dictionary is a `Dictionary<string, Func<Movie, bool>>`, and `lambda m: (...)` is `m => ...`. `age_votes` is a method returning a `Func<Movie, int>` that captures `thresholds` in a closure, exactly like a C# lambda capturing a local variable.

> [!WARNING]
> **Watch out.** In the spike, `C` and `m` are recomputed from the data every run. In the product they are **pinned** (`C = 6.08`, `m = 50`; [decision record 0008](../decisions/0008-corpus-gate-and-hybrid-ranking.md)). Otherwise every daily crawl would shift every movie's score a little, and a movie could fall in and out of the gate for no real reason.

## 3. A closed vocabulary as Python types

**File:** [schemas_v1.py](../../spikes/16-recommendation/schemas_v1.py).

```python
from typing import Literal
from pydantic import BaseModel

Pacing = Literal["slow", "medium", "fast"]
Intensity = Literal[1, 2, 3, 4, 5]
ContentWarning = Literal["violence", "gore", "sexual_content", ..., "flashing_lights"]

class QueryIntent(BaseModel):
    # channel 1: hard pre-filters
    max_runtime_minutes: int | None
    max_intensity: Intensity | None
    avoid: list[ContentWarning]
    audience: Literal["kids", "teens"] | None
    # channel 2: meaning
    tone: list[Tone]
    semantic_description: str
    # channel 3: ranking hints
    specificity: Literal["broad", "medium", "specific"]
```

**What to notice: one type does three jobs.**

1. **For the type checker (pyright):** code that writes `intent.avoid = ["spiders"]` fails before it runs.
2. **At runtime (Pydantic):** `QueryIntent.model_validate(json)` rejects any value not in the list.
3. **For the LLM:** `QueryIntent.model_json_schema()` produces a JSON Schema with `"enum": ["slow", "medium", "fast"]`, and the provider **constrains the model's output** to it. The model literally can't produce "spiders" as a content warning. That's why the design needs `unmapped_constraints`: a place for things the vocabulary can't express.

> [!TIP]
> **C# comparison.** `Literal[...]` is close to a C# `enum`, but the values are plain strings at runtime, which is what JSON needs. `BaseModel` is like a C# `record` with DataAnnotations or FluentValidation attached. `int | None` is `int?`.

> [!WARNING]
> **Watch out.** Look at `tone: list[Tone]  # 1-3` in the spike file. The "1 to 3" is only a **comment**, so nothing enforces it. This is exactly how Gemini returned 4 tones in spike 11. In `src/`, write it as `Annotated[list[Tone], Field(min_length=1, max_length=3)]`, and *still* check it in code: spike 11 notes that Gemini strips length limits from the schema it receives.

## 4. Structured output with a validator and a retry

**File:** [probe_pydantic_ai.py](../../spikes/11-llm/probe_pydantic_ai.py), `rerank_agent` (line 76) and the fake test (line 216).

```python
def rerank_agent(native: bool) -> Agent[set[int], schemas.Rerank]:
    output_type: Any = NativeOutput(schemas.Rerank) if native else schemas.Rerank
    agent: Agent[set[int], schemas.Rerank] = Agent(
        output_type=output_type,
        instructions=prompts.RERANK_SYSTEM,
        deps_type=set[int],        # candidate IDs, injected per run
        retries=1,
    )

    @agent.output_validator
    def _check(ctx: RunContext[set[int]], rerank: schemas.Rerank) -> schemas.Rerank:
        problems = schemas.check_rerank(rerank, ctx.deps)   # real IDs? duplicates? length?
        if problems:
            # Pydantic AI sends this text back to the model and asks again (one retry).
            raise ModelRetry("Fix these problems: " + "; ".join(problems))
        return rerank

    return agent
```

**How it flows:**

1. The model answers. Pydantic checks the **shape** (valid JSON for `Rerank`).
2. `_check` checks the **meaning** with plain code: every picked ID must be in `ctx.deps` (the candidate IDs passed in for this run), no duplicates, pitch length.
3. If there's a problem, `ModelRetry` sends the message back to the model, which tries once more.
4. If it fails again, Pydantic AI raises `UnexpectedModelBehavior`. The application catches that and returns "results without pitches".

**The test with no network:**

```python
def scripted(messages, info):
    calls["n"] += 1
    bad  = {"picks": [{"tmdb_id": 999, "pitch": "x"}]}             # an invented movie
    good = {"picks": [{"tmdb_id": 1, "pitch": "A quiet, warm drama."}]}
    return ModelResponse(parts=[ToolCallPart(tool, bad if calls["n"] == 1 else good)])

res2 = rerank_agent(False).run_sync("req", model=FunctionModel(scripted), deps={1})
# -> model_calls == 2: the validator rejected 999, the retry returned a valid pick
```

> [!TIP]
> **C# comparison.**
> - `Agent[set[int], Rerank]` is a generic type, like `Agent<TDeps, TOutput>` with `TDeps = HashSet<int>`.
> - `deps` is per-run dependency injection: like a scoped service resolved for one request.
> - `@agent.output_validator` is a **decorator**: it registers `_check` with the agent, similar to registering a validator in DI or a MediatR pipeline behaviour.
> - `ModelRetry` is used like an exception, but it means "tell the model and try again", not "fail".
> - `FunctionModel` is a Moq fake whose `Setup(...).Returns(...)` changes on the second call.

> [!WARNING]
> **Watch out.** This retry was proven only with the scripted fake. Whether the **real** model fixes its answer after the feedback is unverified; the walking skeleton checks it.

## 5. Filtered vector search

**File:** [probe_atlas.py](../../spikes/09-atlas/probe_atlas.py), `vector_index_definition` (line 190) and `run_prefilter_verification` (line 324).

First, the index. Every field you'll filter on must be declared:

```python
{
    "fields": [
        {"type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine"},
        {"type": "filter", "path": "streamable"},
        {"type": "filter", "path": "runtime"},
        {"type": "filter", "path": "_id"},
        {"type": "filter", "path": "profile.intensity"},
        {"type": "filter", "path": "profile.content_warnings"},
    ]
}
```

Then the query, an aggregation pipeline (simplified: the script builds the same structure from variables; here they are replaced by example values):

```python
pipeline = [
    {"$vectorSearch": {
        "index": "movies_vector_idx",
        "path": "embedding",
        "queryVector": query_vec,          # 384 numbers from the embedder
        "numCandidates": 400,              # how many neighbours the index explores
        "limit": 40,                       # how many it returns
        "filter": {"$and": [
            {"streamable": {"$in": ["ES:8", "ES:337", "ES:119"]}},
            {"runtime": {"$lte": 120}},
            {"_id": {"$nin": exclude_ids}},
            {"profile.intensity": {"$lte": 3}},
            {"profile.content_warnings": {"$nin": ["sexual_violence", "animal_harm"]}},
        ]},
    }},
    {"$project": {"title": 1, "score": {"$meta": "vectorSearchScore"}}},
]
```

**What to notice:**

- **`$in` on an array field** means "the movie's `streamable` list contains *any* of these". **`$nin` on an array** means "contains *none* of these". The spike checked that a movie with an empty `content_warnings` list passes `$nin`, which is the behaviour we want.
- **`numCandidates` vs `limit`.** The index is approximate (it's an HNSW graph, see [Part 8](08-concepts-and-questions.md#vectors-and-search)). It explores `numCandidates` neighbours and returns the best `limit`. MongoDB's documentation suggests `numCandidates` of about 20 × `limit` for good accuracy. With `limit = 150`, that's about 3,000, which is why latency must be measured again at full scale.
- **Pre-filter vs post-filter.** Here the filter runs *inside* the search, so all 40 results obey it. If you filtered *after* taking the top 40, a strict filter (one small service in Bolivia + kids) could leave you with 2 results.

> [!TIP]
> **C# comparison.** Pre-filtering is `movies.Where(rules).OrderByDescending(similarity).Take(40)`. Post-filtering is `movies.OrderByDescending(similarity).Take(40).Where(rules)`, which can return far fewer than 40.

> [!WARNING]
> **Watch out.** Forget to declare a path in the index, and the query fails with "Path 'year' needs to be indexed as filter". The walking skeleton adds `year`, `original_language` and the age-rating fields, so the index definition must change with them.

## 6. The hybrid score

**File:** [rank_eval.py](../../spikes/16-recommendation/rank_eval.py), function `hybrid` (line 110). The type hints are removed from the first line to keep it short; the body is unchanged.

```python
def hybrid(cands, meta, intent, max_logpop):
    sims = [s for _, s in cands]
    lo, hi = min(sims), max(sims)
    w_sem, w_qual, w_era, w_pop = {
        "broad":    (0.45, 0.30, 0.10, 0.15),
        "medium":   (0.60, 0.20, 0.10, 0.10),
        "specific": (0.80, 0.10, 0.05, 0.05),
    }[intent.specificity]
    scored = []
    for i, s in cands:
        m = meta[i]
        sim = (s - lo) / (hi - lo) if hi > lo else 1.0             # min-max over the candidates
        qual = min(1.0, max(0.0, (m["wr_tmdb"] - 5.0) / 3.0))      # quality 5..8 -> 0..1
        if intent.acclaim_preference == "critically_acclaimed" and m.get("critic") is not None:
            qual = 0.5 * qual + 0.5 * m["critic"] / 100
        pop = math.log1p(m["popularity"]) / max_logpop
        if intent.acclaim_preference == "hidden_gem":
            pop = 1.0 - pop                                          # prefer the less popular
        era = 1.0
        if intent.era_mode == "modern_default" and m["age"] > 20:
            era = 0.6 + 0.4 * qual          # old films keep full weight only when well rated
        wp = w_pop + (0.10 if intent.acclaim_preference == "crowd_pleaser" else 0.0)
        scored.append((i, w_sem * sim + w_qual * qual + w_era * era + wp * pop))
    return sorted(scored, key=lambda x: -x[1])
```

**Walk through it with the failure from [Part 6](06-spike-recommendation-quality.md#a-failure-the-spike-found-in-its-own-formula):** request *"exhausted, something light and easy"*, so `specificity = broad`.

- A great old drama (quality score 8.0, 35 years old): `qual = (8.0 − 5)/3 = 1.0`, and `era = 0.6 + 0.4 × 1.0 = 1.0`. So the "old film" discount disappears completely for well-rated classics.
- With broad weights, quality alone contributes `0.30 × 1.0 = 0.30`, and era another `0.10`.
- A mediocre-but-light recent comedy with `qual = 0.3` gets `0.09` from quality. Even if it is more similar, it struggles to catch up.

Nothing in the formula knows that a 4-hour drama is not "easy". That is the missing **effort or runtime signal**.

**The min-max problem.** `sim` is rescaled so the best candidate gets 1 and the worst gets 0. Fetch 150 candidates instead of 100, and the "worst" changes, so **every movie's `sim` changes**. A score that depends on how many neighbours you fetched is fragile. The decision: use a fixed scale.

> [!TIP]
> **C# comparison.** `{...}[intent.specificity]` is a dictionary lookup that returns a tuple, unpacked into four variables at once, like `var (wSem, wQual, wEra, wPop) = weights[intent.Specificity];` with a `ValueTuple`. `sorted(scored, key=lambda x: -x[1])` is `scored.OrderByDescending(x => x.Item2).ToList()`.

> [!WARNING]
> **Watch out.** These weights are hand-set and judged on 12 requests by an LLM. Treat them as a starting point to tune on your labelled requests, not as a result.

---

### Exercises (optional, 10–20 minutes each)

1. In a Python shell (`uv run python`), type the `wr` function and compute the score for a 7.0 movie with 50 votes, and for a 7.0 movie with 5,000 votes. Explain the difference in one sentence.
2. Write the `Annotated[..., Field(...)]` version of `tone` from example 3, create a `QueryIntent` with 4 tones, and read Pydantic's error message.
3. Change the hybrid formula on paper so that "easy" requests penalise films over 150 minutes. Which existing field would you use?

[Back to the index](README.md) · Previous: [Part 6](06-spike-recommendation-quality.md) · Next: [Part 8 · Concepts and questions](08-concepts-and-questions.md)
