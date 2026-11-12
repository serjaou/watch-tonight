# Progress

## Now
- **Active feature:** none (`feat-007` — Antigravity on the Mac verification — is `done` on branch `chore/verify-antigravity-mac`, awaiting PR merge).
- **State:** `feat-007` verified all `feat-004` harness changes on macOS in Antigravity:
  - live Antigravity `Stop` hook (`.agents/hooks.json` → `python3 ../scripts/hooks/stop_gate.py`) fired on turn completion, blocked on a real `F401` lint error in `tests/test_smoke.py` with `decision: "continue"` (`attempt 2/3`), and allowed stopping once green;
  - fixed a state-leak edge case in `scripts/hooks/stop_gate.py`: when a failing edit is reverted so `has_code_changes()` becomes `False`, `COUNTER` (`.harness/stop_gate_attempts`) is now unlinked instead of left behind (covered in `tests/harness/test_harness.py`);
  - verified that Antigravity natively loads `.agents/agents/reviewer.md` as `TypeName: "reviewer"` with `tools: [read_file, run_command]` (`read_file` and `run_command` present; `view_file`, `edit_file` and `write_file` absent), and updated `.agents/skills/review/SKILL.md` to invoke `TypeName: "reviewer"` directly;
  - verified autonomous task flow (ADR 0004): agent ran `uv run poe check`, `/review` (`"No findings"`), and `/handoff` on its own.
- **Last check:** `uv run poe check` green, 2026-11-12 23:54 CET, Mac (ruff check, ruff format --check, pyright strict 0 errors, lint-imports 2/2 kept, pytest 25 passed).
- **Next step:** after merging `chore/verify-antigravity-mac`, start `feat-005` (*Architecture v0 + spike question files*, `chore`, ready).
- **Waiting on owner:**
  1. Merge the `feat-007` PR from `chore/verify-antigravity-mac` after green CI.
  2. Ensure GitHub branch protection on `main` (required checks `check` and `gates`) and the `tests-approved` label are configured (README "Repository settings").
- **Unverified:**
  - GitHub CI (`check` and `gates`) on the `chore/verify-antigravity-mac` PR (`gh` CLI not installed on this Mac).

## Log (newest first, 1–3 lines each)
- 2026-11-12 · Mac · Antigravity · feat-007: verified `feat-004` harness changes on the Mac. Live `Stop` hook blocked on a real `F401` lint error and allowed when green; fixed `stop_gate.py` to clear `.harness/stop_gate_attempts` when changes are reverted; verified `TypeName: "reviewer"` uses `read_file` + `run_command` (`view_file`/write tools absent) and updated `/review`; completed autonomous `/review` ("No findings") + `/handoff`.
- 2026-11-12 · Windows · Claude Code · feat-004: first Windows session. Installed uv; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, a reviewer that missed committed work, and a pre-commit/project ruff mismatch, all fixed. Added Claude Code support (ADR 0003), autonomous task runs with owner gates (ADR 0004), PR gates CI, English-only launch, 350-character pitches, and backlog feat-005…feat-011.
- 2026-11-12 · Mac · Antigravity · feat-000: completed end-to-end harness dry run (`/spec`, `prompt_validation.py`, `stop_gate.py` test, Reviewer subagent `"No findings"`, `/defend` in `LEARNING.md`, ADRs `0001`–`0002`, and `/handoff`).
- 2026-11-11 · Mac · Antigravity · feat-001: added `.python-version`, `pyproject.toml`, `uv.lock`, `src/watch_tonight/` layers, `tests/test_smoke.py`, `.pre-commit-config.yaml` (ruff + gitleaks), and `.github/workflows/ci.yml`; `uv run poe check` green.
- 2026-11-11 · Mac · Antigravity · feat-001: drafted `docs/product.md`, refined `AGENTS.md` and `feature_list.json` with Definition of Ready and spike rules, added Step 1 repo hygiene files.
