# watch-tonight

Describe how you feel tonight, pick your country and streaming services, and get **5 movies you can stream right now**, each with a short pitch grounded in the movie's data.

> **Status:** harness in place, product work not started. See [PROGRESS.md](PROGRESS.md) and [docs/product.md](docs/product.md).

## Stack

- **Backend:** Python 3.13 · FastAPI · MongoDB Atlas Vector Search · Gemini · MCP Python SDK
- **Frontend:** Web UI in `web/`
- **Tooling:** `uv` · `ruff` · `pyright` · `import-linter` · `pytest` · `poethepoet`
- **AI coding tools:** Google Antigravity (Mac) and Claude Code (Windows), sharing one harness ([ADR 0003](docs/decisions/0003-support-antigravity-and-claude-code.md))

## Machine setup (once per machine)

| Tool | macOS | Windows | Why |
|---|---|---|---|
| uv | `brew install uv` | `winget install --id=astral-sh.uv -e` | Installs Python 3.13 and the locked packages |
| pre-commit | `uv tool install pre-commit` | `uv tool install pre-commit` | Runs gitleaks and ruff before each commit |
| Docker Desktop | optional | optional | Only for `uv run poe test-all` (integration tests) |
| GitHub CLI | `brew install gh` (optional) | `winget install --id=GitHub.cli -e` (optional) | Lets `/start` read the last CI run |

Then, in the repo:

```bash
uv sync              # creates .venv with Python 3.13 and the exact locked packages
pre-commit install   # adds the git hook (once per clone)
uv run poe check     # must be green before any work
```

## Repository settings (once, on GitHub)

Agents work on branches and open PRs; these settings make sure nothing reaches `main` unchecked ([ADR 0004](docs/decisions/0004-autonomous-task-runs-owner-gates.md)):

1. **Settings → Branches → Add branch ruleset** (or classic branch protection) for `main`:
   - require a pull request before merging;
   - require status checks to pass: `check` (workflow `CI`) and `gates` (workflow `PR gates`);
   - block force pushes.
2. **Issues → Labels → New label:** `tests-approved`. Only you add it, after reviewing changes to `tests/acceptance/` or `evals/`.

## Documentation

- [docs/workflow.md](docs/workflow.md) — **owner's 1-page SDLC & daily session cheat sheet**
- [AGENTS.md](AGENTS.md) — map and working rules for AI agents
- [PROGRESS.md](PROGRESS.md) — current session state and log
- [feature_list.json](feature_list.json) — scope and feature status
- [docs/product.md](docs/product.md) — product specification and rules
- [LEARNING.md](LEARNING.md) — Python & agentic engineering concept map and learning log

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB. Streaming availability data provided by JustWatch via TMDB.
