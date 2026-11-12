# Harness Log

Records every time an agent, hook, or handoff fails or reveals a gap, along with the root cause and the change made to the harness.

---

## 2026-11-12 · Mac · Antigravity (`feat-001`)
- **Finding:** Two environment assumptions in the initial `stop_gate.py` sketch would have failed at runtime:
  1. Antigravity runs commands in `.agents/hooks.json` with `.agents/` as the process working directory (not the repository root), while passing the workspace root in the `stdin` JSON payload (`cwd`).
  2. Non-interactive shells on macOS do not always inherit `/opt/homebrew/bin` in `PATH`, causing `uv: command not found`.
- **Root cause:** The initial sketch assumed `hooks.json` ran from the repo root with the user's interactive terminal `PATH`.
- **Harness change:** Updated `scripts/hooks/stop_gate.py` to resolve `REPO_ROOT = Path(__file__).resolve().parents[2]`, `os.chdir(REPO_ROOT)`, locate `uv` across `PATH` and standard install paths (`/opt/homebrew/bin/uv`, `~/.local/bin/uv`), and only gate normal turn completions (`terminationReason == "NO_TOOL_CALL"`).
- **Lesson:** L06 / L10 — verify hook execution context and environment assumptions rather than trusting templates.
