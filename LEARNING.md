# Learning Map & Session Index

Tracks Python, FastAPI, MongoDB, and agentic harness concepts encountered in `watch-tonight`, mapped to C# / .NET equivalents. Detailed session notes live in `docs/learning/` (one file per session).

**Status progression:** `Seen` (explained by tutor) → `Practised` (used in code) → `Can explain` (defended in `/defend` or `/tutor quiz`).

---

## 1. Concept Map

| Concept | Category | C# / .NET Equivalent | Status | Where Used |
|---|---|---|---|---|
| `.python-version` + `uv` | Tooling | `global.json` + `dotnet` CLI / NuGet | `Practised` | [.python-version](.python-version), [pyproject.toml](pyproject.toml) |
| `pyproject.toml` (`[project]`, `[dependency-groups]`) | Tooling | `.csproj` (`<PropertyGroup>`, `<PackageReference>`) | `Practised` | [pyproject.toml](pyproject.toml) |
| Editable install (`hatchling`) | Packaging | `<ProjectReference>` between `tests/` and `src/` | `Seen` | [pyproject.toml](pyproject.toml) |
| `__init__.py` packages | Language | Explicit module/package boundary (vs folder-implied namespaces in C#) | `Practised` | [src/watch_tonight/__init__.py](src/watch_tonight/__init__.py) |
| `ruff` (lint + format) | Quality Gates | Roslyn analyzers (`AnalysisMode`) + `dotnet format` | `Practised` | [pyproject.toml](pyproject.toml), [.pre-commit-config.yaml](.pre-commit-config.yaml) |
| `pyright` (`typeCheckingMode = "strict"`) | Type System | `<Nullable>enable</Nullable>` + `<TreatWarningsAsErrors>` | `Practised` | [pyproject.toml](pyproject.toml) |
| `import-linter` contracts | Architecture | `NetArchTest` / separate `.csproj` layer references | `Practised` | [pyproject.toml](pyproject.toml) |
| `pytest` markers (`@pytest.mark.integration`) | Testing | xUnit `[Trait("Category", "Integration")]` | `Seen` | [pyproject.toml](pyproject.toml) |
| `@pytest.mark.parametrize` | Testing | xUnit `[Theory]` + `[InlineData(...)]` | `Practised` | [tests/unit/test_prompt_validation.py](tests/unit/test_prompt_validation.py) |
| `typing.Final` | Type System | `const` / `readonly` (enforced by static analyzer only, not at runtime) | `Can explain` | [src/watch_tonight/domain/prompt_validation.py](src/watch_tonight/domain/prompt_validation.py) |
| `typing.TypedDict` | Type System | Compile-time-only shape annotation over a mutable `dict` (vs Pydantic / C# `record`) | `Can explain` | [tests/harness/test_harness.py](tests/harness/test_harness.py) |
| `pathlib.Path` & `subprocess.run` (`encoding="utf-8"`, `utf-8-sig`) | Stdlib | `FileInfo` / `Path` & `Process.Start` / `StreamReader` | `Can explain` | [scripts/hooks/stop_gate.py](scripts/hooks/stop_gate.py) |
| `@pytest.fixture` & `tmp_path` | Testing | xUnit constructor DI (`IClassFixture<T>`) + temp directory | `Can explain` | [tests/harness/test_harness.py](tests/harness/test_harness.py) |
| `str.startswith(tuple)` & comprehensions | Language | `prefixes.Any(p => path.StartsWith(p))` / LINQ `.Where()` | `Can explain` | [scripts/ci/pr_gates.py](scripts/ci/pr_gates.py) |
| Gate strengths (outside the agent / tool hook / instruction) | Harness | Branch policies / pre-push hook / `CONTRIBUTING.md` | `Seen` | [checkpoint Part 2](docs/checkpoint-2026-11-16/02-the-harness.md) |
| Fakes per port in unit tests | Testing | One Moq `Setup(...).Returns(...)` per test | `Seen` | [docs/architecture.md](docs/architecture.md) §2 |
| Embeddings (text → 384 numbers) | RAG | No direct equivalent; a "similarity-preserving hash" | `Seen` | [ADR 0007](docs/decisions/0007-embeddings-fastembed-profile-template.md), [embed_pool.py](spikes/16-recommendation/embed_pool.py) |
| Cosine similarity | RAG | `TensorPrimitives.CosineSimilarity` (System.Numerics.Tensors) | `Seen` | [rank_eval.py](spikes/16-recommendation/rank_eval.py) |
| HNSW / approximate nearest-neighbour index | RAG | Azure AI Search `hnsw` vs `exhaustiveKnn` | `Seen` | [probe_atlas.py](spikes/09-atlas/probe_atlas.py) |
| Pre- vs post-filtering; exact vs approximate search | RAG | `Where` before vs after `OrderBy().Take()` | `Seen` | [docs/architecture.md](docs/architecture.md) §3 |
| Closed vocabulary (`Literal`) + mirror schema | LLM output | C# `enum` + a JSON Schema `enum` | `Seen` | [schemas_v1.py](spikes/16-recommendation/schemas_v1.py), [ADR 0005](docs/decisions/0005-closed-vocabulary-mirror-schema.md) |
| Structured output + `output_validator` + `ModelRetry` | LLM output | FluentValidation + a Polly retry that sends the errors back | `Seen` | [probe_pydantic_ai.py](spikes/11-llm/probe_pydantic_ai.py) |
| Bayesian weighted rating & the corpus gate | Ranking | — | `Seen` | [corpus.py](spikes/16-recommendation/corpus.py) |
| Hybrid re-score & min-max normalisation | Ranking | — | `Seen` | [rank_eval.py](spikes/16-recommendation/rank_eval.py) |
| LLM-as-judge noise (self-disagreement) | Evals | Flaky-test rate as a noise floor | `Seen` | [spike 16 §5](docs/spikes/16-recommendation-signals-and-ranking.md) |

---

## 2. Learning Log Index (newest first)

| Date | Target | Topics Defended / Covered | Session File |
|---|---|---|---|
| 2026-11-21 | Checkpoint 2026-11-16 (guide Parts 1–4 and 6, written answers) | Gate strengths, response states, closed vocabulary, embeddings & HNSW, pre-filtering, `/discover` trap, churn, the corpus gate | [2026-11-21-checkpoint.md](docs/learning/2026-11-21-checkpoint.md) |
| 2026-11-13 | `HEAD~10..HEAD` (`feat-004`, `feat-007`) | Cross-OS encodings (`cp1252` vs `utf-8-sig`), `@pytest.fixture` (`tmp_path` → `gate_repo`), `str.startswith(tuple)` & trailing `/` boundary | [2026-11-13-feat-004-007.md](docs/learning/2026-11-13-feat-004-007.md) |
| 2026-11-12 | `feat-000` | `typing.Final` vs C# `const`, `.strip()` order & Rule P4 rejection, `typing.TypedDict` vs Pydantic / C# `record` | [2026-11-12-feat-000.md](docs/learning/2026-11-12-feat-000.md) |
| 2026-11-12 | `feat-001` | `pyproject.toml` tool consolidation & `import-linter` contracts vs `.csproj` layer references | [2026-11-12-feat-001.md](docs/learning/2026-11-12-feat-001.md) |
