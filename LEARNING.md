# Learning Map & Log

Tracks Python, FastAPI, MongoDB, and agentic harness concepts encountered in `watch-tonight`, mapped to C# / .NET equivalents.

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
| `pathlib.Path` & `subprocess.run` | Stdlib | `FileInfo` / `Path` & `Process.Start` | `Practised` | [scripts/hooks/stop_gate.py](scripts/hooks/stop_gate.py) |

---

## 2. Learning Log (newest first)

### 2026-11-12 · `feat-000` Harness dry run: mood prompt validator (Product Rule P4)
- **Concepts defended:**
  1. **`typing.Final` vs C# `const`:** In Python, type annotations (including `Final[int]`) have **zero runtime enforcement**—at runtime `MAX_PROMPT_LENGTH` is still a regular variable that could be reassigned unless a static type checker (`pyright`) blocks it. In C#, `const` is baked into IL at compile time and cannot be mutated at runtime.
  2. **Order of `.strip()` before `len()` & explicit rejection (Rule P4):** In Python, `len("")` does *not* fail (it simply returns `0`), and `if not cleaned:` checks whether the string is empty (`""` is falsy in Python, like `string.IsNullOrEmpty(cleaned)` after `.Trim()` in C#). We `.strip()` *before* checking `len(cleaned) > 500` so a 500-character prompt with accidental spaces at the end isn't falsely rejected, and we raise `PromptValidationError` instead of slicing (`cleaned[:500]`) because Product Rule P4 forbids silent truncation.
  3. **`typing.TypedDict` vs Pydantic / C# `record`:** `json.loads()` returns `Any` (an untyped Python `dict` at runtime). In `pyright` strict mode, indexing an untyped dict produces `Unknown` type errors. `TypedDict` tells `pyright` the expected key/value types at static-analysis time, **without** validating or converting the dictionary at runtime (it remains a plain, mutable `dict`). By contrast, a **Pydantic `BaseModel`** (which we will use in FastAPI and LLM outputs) validates types at runtime and can be configured as immutable (`frozen=True`), much closer to a C# `record` + `System.Text.Json` deserialization.

### 2026-11-12 · `feat-001` Repo skeleton and harness v0
- **Concepts covered:** How `pyproject.toml` consolidates package metadata, dev dependencies, task runner (`poethepoet`), linter/formatter (`ruff`), strict static type checking (`pyright`), architectural boundary enforcement (`import-linter`), and `pytest` configuration into a single file.
- **Key C# contrast:** In .NET, Clean Architecture boundaries are enforced by the compiler via separate `.csproj` files (`Domain.csproj`, `Application.csproj`, `Infrastructure.csproj`). In a single-package Python repo, any module can `import` any other module at runtime unless an explicit static tool like `import-linter` checks the import graph.
