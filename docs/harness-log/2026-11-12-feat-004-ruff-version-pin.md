# Harness Log: `2026-11-12` · Windows · Claude Code (`feat-004`) — Pre-commit vs `uv.lock` ruff version pin

- **Finding:** `.pre-commit-config.yaml` pinned `ruff v0.9.10` while `uv.lock` had `ruff 0.17.4`, so a commit could pass pre-commit and fail `poe fmt-check` (or the reverse).
- **Layer:** `environment`.
- **Root cause:** Two places pinned the same tool.
- **Harness change:** Pre-commit runs the project's ruff (`uv run --no-sync ruff`, a local hook); `uv.lock` is the only pin.
- **Lesson:** L04 one source of truth, also for tool versions.
