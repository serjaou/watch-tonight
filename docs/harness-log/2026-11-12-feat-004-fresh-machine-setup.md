# Harness Log: `2026-11-12` · Windows · Claude Code (`feat-004`) — Fresh-machine setup documentation

- **Finding:** The fresh-machine test failed at step zero: `uv` wasn't installed and the `README.md` didn't say how to install it, or that `pre-commit install` is needed per clone (so gitleaks wasn't running on this machine).
- **Layer:** `environment`.
- **Root cause:** Setup knowledge lived only on the Mac.
- **Harness change:** "Machine setup" table in `README.md` (macOS + Windows); `AGENTS.md` tells agents to point the owner there instead of installing tools themselves.
- **Lesson:** L03 / L06 the fresh-session test: "how do I run it" must be answerable from the repo.
