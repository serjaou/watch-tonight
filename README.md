# watch-tonight

Describe how you feel tonight, pick your country and streaming services, and get **5 movies you can stream right now**, each with a short pitch grounded in the movie's data.

> **Status:** `feat-001` — Repo skeleton and harness v0 in progress. See [PROGRESS.md](PROGRESS.md) and [docs/product.md](docs/product.md).

## Stack

- **Backend:** Python 3.13 · FastAPI · MongoDB Atlas Vector Search · Gemini · MCP Python SDK
- **Frontend:** Web UI in `web/`
- **Tooling:** `uv` · `ruff` · `pyright` · `import-linter` · `pytest` · `poethepoet`

## Quickstart

```bash
uv sync
uv run poe check
```

## Documentation

- [docs/workflow.md](docs/workflow.md) — **owner's 1-page SDLC & daily session cheat sheet**
- [AGENTS.md](AGENTS.md) — map and working rules for AI agents
- [PROGRESS.md](PROGRESS.md) — current session state and log
- [feature_list.json](feature_list.json) — scope and feature status
- [docs/product.md](docs/product.md) — product specification and rules
- [LEARNING.md](LEARNING.md) — Python & agentic engineering concept map and learning log

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB. Streaming availability data provided by JustWatch via TMDB.
