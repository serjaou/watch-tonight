# Harness Log: `2026-11-12` · Windows · Claude Code (`feat-004`) — Windows Stop hook UTF-8 & BOM encoding

- **Finding:** Running the real Stop hook on Windows showed two bugs that the unit tests (all on the happy path) missed:
  1. `stop_gate.py` decoded the check's output as `cp1252`, so a failing check that printed `import-linter`'s UTF-8 box art crashed the gate: on Windows it could never block.
  2. Windows PowerShell 5.1 pipes a BOM before the JSON payload, which made payload parsing fail silently.
  3. Later the same day, the BOM test passed under PowerShell but failed under Git Bash: Python decoded the payload with the shell's settings (UTF-8 where `PYTHONIOENCODING` was set, `cp1252` in Git Bash, which is where Claude Code runs hooks). Claude Code's payload carries the last assistant message as raw UTF-8, so some characters could crash the gate.
- **Layer:** `verification`.
- **Root cause:** The gate was only ever run on macOS, where the default encoding is UTF-8; then the tests inherited the shell's encoding variables (a hidden input, like the git state in `2026-11-12-feat-004-ci-git-state-test.md`).
- **Harness change:** Subprocess output and the `stdin` payload are decoded as UTF-8 explicitly (`utf-8-sig` also drops the BOM); the tests strip `PYTHONIOENCODING`/`PYTHONUTF8` and send raw UTF-8 like Claude Code does. Verified in PowerShell and Git Bash.
- **Agent slip:** The failing test was committed (not pushed) because the agent chained `pytest ... | tail -1 && git commit`, which checks only the pipeline's last command. The Stop hook runs at the end of a turn, not before commits, so it can't catch this; CI would have. Don't gate a commit on a piped command's exit status.
- **Not fixed (by decision):** `.agents/hooks.json` calls `python3`, which on this Windows machine is the Microsoft Store stub ("Python was not found"). Antigravity runs only on the Mac (ADR 0003), so it doesn't matter.
- **Lesson:** L10 end-to-end checks: run the real hook command on every OS it must support.
