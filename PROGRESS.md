# Progress

## Now
- **Active feature:** none. `feat-005` (Architecture v0 + spike question files) is done on branch `chore/architecture-v0`; its PR waits for the owner's merge.
- **State:** `feat-005` delivered:
  - `docs/architecture.md` v0: components, layers and ports, the 7-step query flow (P1/P3 checked on candidates before the LLM picks, so 2 LLM calls per query), offline pipeline, data model, cross-cutting concerns, and open questions Q1–Q12, each routed to a spike or an owner decision;
  - spike question files `docs/spikes/08` (TMDB), `09` (Atlas), `10` (embedding runtime), `11` (runtime LLM);
  - new spike `feat-011` (runtime LLM): it was on the inception Week 1 checklist but had no backlog item. Refinement + slicing is now `feat-012`, and ids still follow the order.
- **Last check:** `uv run poe check` green, 2026-11-13 13:30, Windows (ruff, pyright strict 0 errors, import-linter 2/2 kept, pytest 25 passed).
- **Next step:** after the merge, `feat-006` (metrics: `docs/metrics.md` and a `/handoff` row per finished feature). It's a chore, so it's ready.
- **Waiting on owner:**
  1. Review and merge the `feat-005` PR. Check `feat-011`'s place in the backlog, and the owner questions in architecture.md §7: Q8 (LLM down or invalid output), Q9 (non-English input), Q10 (frontend framework), and Q11 (how "avoid" constraints are represented; decided in feat-012).
  2. Before the spikes (feat-008…011): create a TMDB API key, a MongoDB Atlas account and a Gemini API key, and put them in your local `.env` (never committed; see `.env.example`).
- **Unverified:** CI on the `feat-005` PR (runs when the PR is opened).

## Log (newest first, 1–3 lines each)
- 2026-11-13 · Windows · Claude Code · feat-005: wrote architecture v0 and the spike question files; reviewer subagent found 12 + 2 design gaps (P3 avoid check, Partial vs bad LLM output, per-result availability date, spike methods), all fixed; added runtime-LLM spike feat-011 (refinement is now feat-012).
- 2026-11-12 · Mac · Antigravity · feat-007: verified `feat-004` harness changes on the Mac. Live `Stop` hook blocked on a real `F401` lint error and allowed when green; fixed `stop_gate.py` to clear `.harness/stop_gate_attempts` when changes are reverted; verified `TypeName: "reviewer"` uses `read_file` + `run_command` (`view_file`/write tools absent) and updated `/review`; completed autonomous `/review` ("No findings") + `/handoff`.
- 2026-11-12 · Windows · Claude Code · feat-004: first Windows session. Installed uv; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, a reviewer that missed committed work, and a pre-commit/project ruff mismatch, all fixed. Added Claude Code support (ADR 0003), autonomous task runs with owner gates (ADR 0004), PR gates CI, English-only launch, 350-character pitches, and backlog feat-005…feat-011.
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
