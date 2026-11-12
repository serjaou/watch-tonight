# Conventions

What agents and the owner need to know to change code here without breaking `uv run poe check`.

## Commands

Every task is a poethepoet task in `pyproject.toml` (`[tool.poe.tasks]`) and behaves the same on macOS and Windows.

- `uv run poe check` runs `lint` → `fmt-check` → `typecheck` (pyright) → `arch` (import-linter) → `test`, and stops at the first failure. Run one step with `uv run poe <step>`.
- One test: `uv run pytest tests/unit/test_prompt_validation.py::test_subclass_of_value_error`. By name: `uv run pytest -k overlong`.
- Tests that need Docker or external services carry `@pytest.mark.integration`. `poe check` skips them; `poe test-all` runs them.
- CI (`.github/workflows/ci.yml`) runs `uv sync --locked` and `uv run poe check`. A dependency change must include the updated `uv.lock`.

## Code

- **Layers** (`src/watch_tonight/`, enforced by import-linter in `pyproject.toml`):
  - `domain/`: entities, value objects, ports (`Protocol`s). No I/O; imports no other layer.
  - `application/`: use cases. Imports only `domain`.
  - `infra/`, `api/`, `mcp_server/`, `jobs/`: outer layers. Nothing yet stops them importing each other.
- **Types:** pyright runs in strict mode on `src`, `tests` and `scripts`. Annotate every function, tests included (`-> None`). Give `json.loads` results a type (e.g. a `TypedDict`) instead of indexing `Any`.
- **Formatting:** ruff, line length 100. Line endings are LF (`.gitattributes`).

## Tests

- `tests/acceptance/`: one file per spec, with the test names the spec lists. The owner approves them; agents don't edit them.
- `tests/unit/`: written with the code.
- `tests/harness/`: checks the harness itself. It fails when:
  - `AGENTS.md` is longer than 150 lines;
  - `feature_list.json` breaks an invariant: `type` not in `feature|spike|chore`, `status` not in `todo|in_progress|blocked|done`, more than one `in_progress`, `done` without `evidence`, a `feature` or `spike` without a `spec` path, a dependency on an unknown id;
  - a required harness file is missing (skills, reviewer, hooks, state docs, `stop_gate.py`), or a skill in `.agents/skills/` has no stub in `.claude/skills/`;
  - `scripts/hooks/stop_gate.py` stops behaving as specified (it runs in a throwaway git repo, so the result never depends on this repo's state).
