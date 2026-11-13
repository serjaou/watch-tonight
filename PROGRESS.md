# Progress

## Now
- **Active feature:** none. `feat-006` (Metrics: `docs/metrics.md` and a `/handoff` row per finished feature) is done on branch `chore/metrics`; its PR waits for the owner's merge. `feat-014` is merged.
- **State:** `feat-006` delivered:
  - `docs/metrics.md`: defines online query metrics (`trace`), offline pipeline metrics (`ingestion_runs`), deterministic + quality eval metrics (`evals/` / `eval_runs`), a spike baseline summary table for `feat-008`…`011`, and the `/handoff` process & harness log backfilled for all 8 finished items (`feat-001`, `feat-000`, `feat-004`, `feat-007`, `feat-005`, `feat-013`, `feat-014`, `feat-006`);
  - wired `/handoff` in `AGENTS.md`, `.agents/skills/handoff/SKILL.md`, and `docs/workflow.md` to record each completed feature's row (and spike baselines for spikes);
  - enforced in `tests/harness/test_harness.py` (and documented in `docs/conventions.md`) that `docs/metrics.md` exists and every `done` feature in `feature_list.json` has a `/handoff` row in `docs/metrics.md`.
- **Last check:** `uv run poe check` green, 2026-11-14 00:02 CET, Mac (ruff check + format check passed, pyright strict 0 errors, import-linter 2/2 kept, pytest 25 passed in 0.78s).
- **Next step:** after the merge, `feat-008` (Spike: TMDB terms, rate limits and watch providers in `docs/spikes/08-tmdb-and-providers.md`). Its questions are ready; needs `TMDB_API_KEY` in local `.env`.
- **Waiting on owner:**
  1. Review and merge the `feat-006` PR.
  2. Before starting `feat-008` (and `feat-009`…`011`): put `TMDB_API_KEY` in your local `.env` (plus a MongoDB Atlas `MONGODB_URI` for `feat-009` and LLM API keys for `feat-011`; never committed, see `.env.example`).
  3. Q13 (movies without a TMDB poster) once spike `feat-008` reports how many lack one.
- **Unverified:** CI on the `feat-006` PR (runs when the PR is opened).

## Log (newest first, 1–3 lines each)
- 2026-11-13 · Mac · Antigravity · feat-006: added `docs/metrics.md` (online, offline, eval, spike baseline and `/handoff` process metrics), backfilled all 8 completed tasks, wired `/handoff` and `AGENTS.md`, and enforced per-feature rows in `tests/harness/test_harness.py`. Reviewer: round 1, "No findings".
- 2026-11-13 · Mac · Antigravity · feat-014: validated harness with `walkinglabs/learn-harness-engineering` `validate-harness.mjs` (60/100 → 92/100); added `init.sh`, `feature_list.json` `description` field + harness test, aligned `AGENTS.md` headings, and logged accepted differences in `docs/harness-log.md`. Reviewer: round 1, 2 findings fixed; round 2, "No findings".
- 2026-11-13 · Windows · Claude Code · feat-013: recorded the owner's decisions on architecture Q8–Q11, posters, zero-cost budget and a provider-neutral LLM spike; reviewer subagent found 7 + 3 consistency gaps (UI vs text constraints, extraction eval, state precedence), all fixed.
- 2026-11-13 · Windows · Claude Code · feat-005: wrote architecture v0 and the spike question files; reviewer subagent found 12 + 2 design gaps (P3 avoid check, Partial vs bad LLM output, per-result availability date, spike methods), all fixed; added runtime-LLM spike feat-011 (refinement is now feat-012).
- 2026-11-12 · Mac · Antigravity · feat-007: verified `feat-004` harness changes on the Mac. Live `Stop` hook blocked on a real `F401` lint error and allowed when green; fixed `stop_gate.py` to clear `.harness/stop_gate_attempts` when changes are reverted; verified `TypeName: "reviewer"` uses `read_file` + `run_command` (`view_file`/write tools absent) and updated `/review`; completed autonomous `/review` ("No findings") + `/handoff`.
- 2026-11-12 · Windows · Claude Code · feat-004: first Windows session. Installed uv; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, a reviewer that missed committed work, and a pre-commit/project ruff mismatch, all fixed. Added Claude Code support (ADR 0003), autonomous task runs with owner gates (ADR 0004), PR gates CI, English-only launch, 350-character pitches, and backlog feat-005…feat-011.
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
