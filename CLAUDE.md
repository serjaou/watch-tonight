# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Claude Code specifics (ADR 0003)

`AGENTS.md` (imported above) and `.agents/` are the single source for both Antigravity and Claude Code. Commands and code conventions are in `docs/conventions.md`. This section lists only what differs in Claude Code.

- **Adapters in `.claude/`:**
  - Skill stubs in `.claude/skills/<name>/SKILL.md` load `.agents/skills/<name>/SKILL.md`. Adding or renaming a skill means adding its stub too; a harness test checks this.
  - The workflow skills are owner-only (`disable-model-invocation`), so phases start when the owner types them (ADR 0004).
  - The `reviewer` subagent stub (`.claude/agents/reviewer.md`) loads `.agents/agents/reviewer.md`.
- **Stop hook:** `.claude/settings.json` runs `scripts/hooks/stop_gate.py`. It won't let you end a turn that changed code while `uv run poe check` fails, and gives up after 3 attempts.
- **Profile:** use this repo only with the owner's personal Claude Code profile (`CLAUDE_CONFIG_DIR`, see "Machine setup" in README.md), never a work profile.
- **Log lines:** `PROGRESS.md` entries use `Claude Code` as the tool.
