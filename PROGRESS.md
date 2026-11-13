# Progress

## Now
- **Active feature:** none. `feat-013` (owner decisions of 2026-11-13) is done on branch `chore/owner-decisions`; its PR waits for the owner's merge. `feat-005` is merged.
- **State:** `feat-013` recorded the owner's decisions:
  - product.md: zero-cost budget; any input language with English UI/titles/pitches; posters (verify); P3 split (UI constraints always applied, text constraints measured by an extraction eval); new *Results without pitches* state;
  - architecture.md: the LLM turns free text into filters over a closed vocabulary and the data layer applies them deterministically; React; profile quality and "metadata ingested once" principles; Q8–Q11 decided; new open question Q13 (movies without a poster);
  - spikes: 08 asks about TMDB image linking and missing posters; 10 about a multilingual model; 11 compares Gemini's free tier with a low-cost OpenAI model;
  - AGENTS.md: no paid service or recurring cost without the owner's approval.
- **Last check:** `uv run poe check` green, 2026-11-13, Windows (ruff, pyright strict 0 errors, import-linter 2/2 kept, pytest 25 passed).
- **Next step:** after the merge, `feat-006` (metrics: `docs/metrics.md` and a `/handoff` row per finished feature). It's a chore, so it's ready.
- **Waiting on owner:**
  1. Review and merge the `feat-013` PR.
  2. Before the spikes (feat-008…011): a TMDB API key, a MongoDB Atlas account, and API keys for the LLM providers spike 11 compares (e.g. Gemini, OpenAI), all in your local `.env` (never committed; see `.env.example`).
  3. Q13 (movies without a TMDB poster) once spike feat-008 reports how many lack one.
- **Unverified:** CI on the `feat-013` PR (runs when the PR is opened).

## Log (newest first, 1–3 lines each)
- 2026-11-13 · Windows · Claude Code · feat-013: recorded the owner's decisions on architecture Q8–Q11, posters, zero-cost budget and a provider-neutral LLM spike; reviewer subagent found 7 + 3 consistency gaps (UI vs text constraints, extraction eval, state precedence), all fixed.
- 2026-11-13 · Windows · Claude Code · feat-005: wrote architecture v0 and the spike question files; reviewer subagent found 12 + 2 design gaps (P3 avoid check, Partial vs bad LLM output, per-result availability date, spike methods), all fixed; added runtime-LLM spike feat-011 (refinement is now feat-012).
- 2026-11-12 · Mac · Antigravity · feat-007: verified `feat-004` harness changes on the Mac. Live `Stop` hook blocked on a real `F401` lint error and allowed when green; fixed `stop_gate.py` to clear `.harness/stop_gate_attempts` when changes are reverted; verified `TypeName: "reviewer"` uses `read_file` + `run_command` (`view_file`/write tools absent) and updated `/review`; completed autonomous `/review` ("No findings") + `/handoff`.
- 2026-11-12 · Windows · Claude Code · feat-004: first Windows session. Installed uv; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, a reviewer that missed committed work, and a pre-commit/project ruff mismatch, all fixed. Added Claude Code support (ADR 0003), autonomous task runs with owner gates (ADR 0004), PR gates CI, English-only launch, 350-character pitches, and backlog feat-005…feat-011.
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
