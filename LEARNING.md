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

---

## 2. Learning Log Index (newest first)

| Date | Target | Topics Defended / Covered | Session File |
|---|---|---|---|
| 2026-11-13 | `HEAD~10..HEAD` (`feat-004`, `feat-007`) | Cross-OS encodings (`cp1252` vs `utf-8-sig`), `@pytest.fixture` (`tmp_path` → `gate_repo`), `str.startswith(tuple)` & trailing `/` boundary | [2026-11-13-feat-004-007.md](docs/learning/2026-11-13-feat-004-007.md) |
| 2026-11-12 | `feat-000` | `typing.Final` vs C# `const`, `.strip()` order & Rule P4 rejection, `typing.TypedDict` vs Pydantic / C# `record` | [2026-11-12-feat-000.md](docs/learning/2026-11-12-feat-000.md) |
| 2026-11-12 | `feat-001` | `pyproject.toml` tool consolidation & `import-linter` contracts vs `.csproj` layer references | [2026-11-12-feat-001.md](docs/learning/2026-11-12-feat-001.md) |
