# Conventions

What agents and the owner need to know to change code here without breaking `uv run poe check`.

## Commands

Every task is a poethepoet task in `pyproject.toml` (`[tool.poe.tasks]`) and behaves the same on macOS and Windows.

- `uv run poe check` runs `lint` → `fmt-check` → `typecheck` (pyright) → `arch` (import-linter) → `test`, and stops at the first failure. Run one step with `uv run poe <step>`.
- `./init.sh` (macOS, Linux, Git Bash) runs `uv sync` and `uv run poe check` with `set -euo pipefail`. It exists for session start and for the guide's validator (feat-014); `poe check` stays the source of truth.
- One test: `uv run pytest tests/unit/test_prompt_validation.py::test_subclass_of_value_error`. By name: `uv run pytest -k overlong`.
- `uv run poe serve` runs the API locally with the walking skeleton's in-memory adapters and fictional films (feat-018); open http://127.0.0.1:8000/docs.
- Tests that need Docker or external services carry `@pytest.mark.integration`. `poe check` skips them; `poe test-all` runs them (testcontainers starts the pinned `mongodb-atlas-local` image; about 30 s once the 2.1 GB image is pulled). CI runs them in a separate `integration` job.
- Local Atlas by hand (feat-030): `uv run poe db-up` (compose.yaml), `uv run poe seed` (spike 16's 300 films from TMDB, about 300 free calls), `uv run poe serve-atlas` (the API on it, fake LLM and embedder), `uv run poe db-down` (removes the data). The app's database is `WATCH_TONIGHT_MONGODB_URI` (default: that local container); `MONGODB_URI` is never read by default.
- CI (`.github/workflows/ci.yml`) runs `uv sync --locked` and `uv run poe check`. A dependency change must include the updated `uv.lock`.
- PR gates (`.github/workflows/pr-gates.yml` → `scripts/ci/pr_gates.py`) fail a PR that changes `tests/acceptance/` or `evals/` until the owner adds the `tests-approved` label.
- pre-commit runs gitleaks and the project's own ruff (from `uv.lock`) before each commit.
- **Secrets:** never print `.env` lines or values, not even through a filter meant to hide them (a filter that fails prints the secret). Check that a variable exists with `grep -c '^NAME=' .env`; to learn something about a URI, parse it and print only the safe part (e.g. `urllib.parse.urlsplit(uri).scheme`). `MONGODB_URI` in `.env` is the cloud M0 cluster (spike 09).

### Windows notes (seen in feat-011)

- Python's default text encoding on Windows is the locale's (cp1252). Pass `encoding="utf-8"` to every `open`/`read_text`/`write_text`. Set `PYTHONUTF8=1` (or `sys.stdout.reconfigure(encoding="utf-8")`) before printing non-ASCII text such as Japanese mood input.
- PowerShell mangles quotes inside `python -c "..."`. For inline Python, use a Git Bash heredoc (`uv run python - <<'EOF'`) or a script file.
- Windows PowerShell 5.1 `Get-Content` reads UTF-8 files as ANSI, so `–` shows up as `â€“`. Use `-Encoding UTF8`, or the Read tool. The file itself is fine.
- `gh` is installed via winget, to `C:\Program Files\GitHub CLI\gh.exe`, and is logged in. A shell started before the install doesn't have it on PATH yet, so call it by full path until the session restarts. Without `gh`, CI status of this public repo can still be read: `Invoke-RestMethod 'https://api.github.com/repos/serjaou/watch-tonight/actions/runs?branch=<branch>&per_page=1' -Headers @{'User-Agent'='ci-check'}`.
- Git Bash `curl` uses Windows schannel and can fail with `CRYPT_E_NO_REVOCATION_CHECK`. Download with Python `urllib` instead of weakening TLS checks.
- JSONL with real-world text (any OS): split on `"\n"`, never `str.splitlines()`. TMDB overviews contain U+2028/U+2029, which `splitlines()` treats as line breaks (feat-016).
- Throwaway spike scripts with extra packages: `uv run --no-project --python 3.13 --with <pkg> python spikes/...`. Without `--python 3.13`, uv may pick the laptop's system Python 3.11.
- **Spike outputs that hold TMDB data stay local.** Raw API responses, movie text (overviews, taglines), LLM output about real films (profiles, pitches, run logs) and catalogue ID dumps are gitignored; copy them between machines by hand if needed. Commit the scripts and the reports with aggregate numbers, titles and IDs of a few examples. Tests use fictional fixtures.

## Code

- **Layers** (`src/watch_tonight/`, enforced by import-linter in `pyproject.toml`):
  - `domain/`: entities, value objects, ports (`Protocol`s). No I/O; imports no other layer.
  - `application/`: use cases. Imports only `domain`.
  - `infra/`, `api/`, `mcp_server/`, `jobs/`: outer layers. Nothing yet stops them importing each other.
- **Types:** pyright runs in strict mode on `src`, `tests`, `scripts` and `evals` (ruff lints the same four). Annotate every function, tests included (`-> None`). Give `json.loads` results a type (e.g. a `TypedDict`) instead of indexing `Any`.
- **Formatting:** ruff, line length 100. Line endings are LF (`.gitattributes`).

## Tests

- `tests/acceptance/`: one file per spec, with the test names the spec lists. The owner approves them; agents don't edit them.
- `tests/unit/`: written with the code; shared builders in `tests/unit/builders.py`.
- `evals/deterministic/`: the six deterministic evals (owner-approved, protected like `tests/acceptance/`). They restate the product rules instead of importing `src/` logic, so a bug can't hide in its own check. pytest has the repo root on `sys.path` (`pythonpath = ["."]`), so tests import `evals` and the acceptance fixtures.
- `tests/harness/`: checks the harness itself. It fails when:
  - an index/instruction file exceeds its line limit (`AGENTS.md <= 150`, `feature_list.json <= 120`, `PROGRESS.md <= 80`, `LEARNING.md <= 120`, `docs/harness-log.md <= 100`, `docs/metrics.md <= 150`);
  - `feature_list.json` (active items: `todo|in_progress|blocked`) or `docs/handoffs/done_features.json` (`done` items) breaks an invariant: a `done` item left in `feature_list.json`, a non-`done` item in `done_features.json`, `type` not in `feature|spike|chore`, an empty or missing `description`, more than one `in_progress`, `done` without a concise `evidence` (`<= 160` chars) referencing an existing `docs/handoffs/<feat-id>.md` or without a `/handoff` row in `docs/metrics.md`, a `feature` or `spike` without a `spec` path, a dependency on an unknown id across active + done;
  - an index file (`PROGRESS.md`, `LEARNING.md`, `docs/harness-log.md`, `docs/metrics.md`, `docs/handoffs/done_features.json`) links to a missing detail file in `docs/handoffs/`, `docs/learning/`, or `docs/harness-log/`, or a detail file in those folders is not linked from its index;
  - a required harness file is missing (skills, reviewer, hooks, state docs, `docs/handoffs/done_features.json`, `docs/metrics.md`, `stop_gate.py`, `init.sh`), or a skill in `.agents/skills/` has no stub in `.claude/skills/`;
  - `scripts/hooks/stop_gate.py` stops behaving as specified (it runs in a throwaway git repo, so the result never depends on this repo's state);
  - `scripts/ci/pr_gates.py` stops protecting `tests/acceptance/` and `evals/`.
