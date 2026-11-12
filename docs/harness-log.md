# Harness Log

Records every time an agent, hook, or handoff fails or reveals a gap, along with the root cause and the change made to the harness.

**Entry format:** Finding · **Layer** (where it failed, course L01: `spec`, `context`, `environment`, `verification` or `state`) · Root cause · Harness change · Lesson.

---

## 2026-11-12 · Windows · Claude Code (`feat-004`, first session on Windows)
- **Finding:** CI had been red since 26f3ebf. `test_stop_gate_blocks_on_failure_and_allows_on_success` only passed on a working tree with uncommitted code changes (the Mac during the dry run); on a clean checkout the gate correctly allowed stopping and the test failed. `PROGRESS.md` listed CI as unverified, but no step made a session check it.
- **Layer:** verification.
- **Root cause:** the test ran the gate against the real repo, so its result depended on the repo's git state (a hidden input, like a test that reads the clock).
- **Harness change:** the test runs a copy of the gate in a throwaway git repo. `/start` checks the latest CI run; a red CI is the session's task (AGENTS.md).
- **Lesson:** L09 premature victory: a sensor that was never seen failing isn't proven.

## 2026-11-12 · Windows · Claude Code (`feat-004`)
- **Finding:** the fresh-machine test failed at step zero: `uv` wasn't installed and the README didn't say how to install it, or that `pre-commit install` is needed per clone (so gitleaks wasn't running on this machine).
- **Layer:** environment.
- **Root cause:** setup knowledge lived only on the Mac.
- **Harness change:** "Machine setup" table in README.md (macOS + Windows); AGENTS.md tells agents to point the owner there instead of installing tools themselves.
- **Lesson:** L03 / L06 the fresh-session test: "how do I run it" must be answerable from the repo.

## 2026-11-12 · Windows · Claude Code (`feat-004`)
- **Finding:** running the real Stop hook on Windows showed two bugs that the unit tests (all on the happy path) missed:
  1. `stop_gate.py` decoded the check's output as cp1252, so a failing check that printed import-linter's UTF-8 box art crashed the gate: on Windows it could never block.
  2. Windows PowerShell 5.1 pipes a BOM before the JSON payload, which made payload parsing fail silently.
  3. Later the same day, the BOM test passed under PowerShell but failed under Git Bash: Python decoded the payload with the shell's settings (UTF-8 where `PYTHONIOENCODING` was set, cp1252 in Git Bash, which is where Claude Code runs hooks). Claude Code's payload carries the last assistant message as raw UTF-8, so some characters could crash the gate.
- **Layer:** verification.
- **Root cause:** the gate was only ever run on macOS, where the default encoding is UTF-8; then the tests inherited the shell's encoding variables (a hidden input, like the git state in the first entry).
- **Harness change:** subprocess output and the stdin payload are decoded as UTF-8 explicitly (`utf-8-sig` also drops the BOM); the tests strip `PYTHONIOENCODING`/`PYTHONUTF8` and send raw UTF-8 like Claude Code does. Verified in PowerShell and Git Bash.
- **Agent slip:** the failing test was committed (not pushed) because the agent chained `pytest ... | tail -1 && git commit`, which checks only the pipeline's last command. The Stop hook runs at the end of a turn, not before commits, so it can't catch this; CI would have. Don't gate a commit on a piped command's exit status.
- **Not fixed (by decision):** `.agents/hooks.json` calls `python3`, which on this Windows machine is the Microsoft Store stub ("Python was not found"). Antigravity runs only on the Mac (ADR 0003), so it doesn't matter.
- **Lesson:** L10 end-to-end checks: run the real hook command on every OS it must support.

## 2026-11-12 · Windows · Claude Code (`feat-004`)
- **Finding:** the reviewer subagent diffed against `HEAD`, so after a WIP commit it saw no changes and would answer "No findings".
- **Layer:** verification.
- **Root cause:** `git diff HEAD` shows only uncommitted changes; the template had `origin/main...HEAD`.
- **Harness change:** reviewer and `/defend` use `git diff origin/main` plus `git status --short`.
- **Lesson:** L09 separate worker and checker, and check that the checker sees the work.

## 2026-11-12 · Windows · Claude Code (`feat-004`)
- **Finding:** agents chained phases on their own (e.g. ran `/handoff` and further steps without asking). The Stepped/Autonomous modes existed only as prose, and "Session end protocol (always, even mid-task)" read as permission to run it unprompted. Skills also restated AGENTS.md and had drifted from it.
- **Layer:** context.
- **Root cause:** declarative modes with nothing selecting or enforcing them; the same rule written in several places.
- **Harness change:** ADR 0004: one default, no modes. A ready task runs end to end (build, check, review + fixes, handoff, PR); the owner decides at spec approval, merge and any human-decision point, and can ask for "step by step". `/defend` is optional. The rules that matter are enforced, not just written: branch protection on `main` and a CI gate on `tests/acceptance/` and `evals/` (`tests-approved` label). Skills point to AGENTS.md instead of restating it.
- **Note:** the owner first chose "stepped only", then reversed it the same day: the point of a harness is that agents complete tasks without constant supervision, and the gates are what make that safe.
- **Lesson:** L04 one source per rule; L13 the human sets direction and decides at the gates, the harness makes the rest safe.

## 2026-11-12 · Windows · Claude Code (`feat-004`)
- **Finding:** `.pre-commit-config.yaml` pinned ruff v0.9.10 while `uv.lock` had ruff 0.17.4, so a commit could pass pre-commit and fail `poe fmt-check` (or the reverse).
- **Layer:** environment.
- **Root cause:** two places pinned the same tool.
- **Harness change:** pre-commit runs the project's ruff (`uv run --no-sync ruff`, a local hook); `uv.lock` is the only pin.
- **Lesson:** L04 one source of truth, also for tool versions.

## 2026-11-12 · Mac · Antigravity (`feat-001`)
- **Finding:** Two environment assumptions in the initial `stop_gate.py` sketch would have failed at runtime:
  1. Antigravity runs commands in `.agents/hooks.json` with `.agents/` as the process working directory (not the repository root), while passing the workspace root in the `stdin` JSON payload (`cwd`).
  2. Non-interactive shells on macOS do not always inherit `/opt/homebrew/bin` in `PATH`, causing `uv: command not found`.
- **Layer:** environment.
- **Root cause:** The initial sketch assumed `hooks.json` ran from the repo root with the user's interactive terminal `PATH`.
- **Harness change:** Updated `scripts/hooks/stop_gate.py` to resolve `REPO_ROOT = Path(__file__).resolve().parents[2]`, `os.chdir(REPO_ROOT)`, locate `uv` across `PATH` and standard install paths (`/opt/homebrew/bin/uv`, `~/.local/bin/uv`), and only gate normal turn completions (`terminationReason == "NO_TOOL_CALL"`).
- **Lesson:** L06 / L10 — verify hook execution context and environment assumptions rather than trusting templates.
