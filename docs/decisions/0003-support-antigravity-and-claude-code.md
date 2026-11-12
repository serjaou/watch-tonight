# 0003. Support Antigravity and Claude Code from one source of truth

- **Date:** 2026-11-12
- **Status:** Accepted. Replaces the "Antigravity only" decision of the inception docs (brief Q2, harness-workflow §1.6).
- **Context:** The harness was built for Antigravity only. Antigravity's usage tiers and LLM limits are too restrictive for daily work, so the owner also uses a Claude Code subscription. The setup is **Antigravity on the Mac** and **Claude Code on the Windows laptop**. The two tools read different files (verified 2026-11-12 in their official docs):
  - Antigravity reads `AGENTS.md` and `.agents/skills/`, `.agents/agents/`, `.agents/hooks.json`.
  - Claude Code reads `CLAUDE.md` (and not `AGENTS.md` when a `CLAUDE.md` exists), `.claude/skills/`, `.claude/agents/` and hooks in `.claude/settings.json`.
  - Neither reads the other's folder. Both use the Agent Skills `SKILL.md` format, but their Stop hooks expect different replies (`continue` vs `block`) and their tools have different names.
- **Decision:**
  1. `AGENTS.md` and `.agents/` stay the single source. `.claude/` holds only thin adapters: `CLAUDE.md` imports `AGENTS.md` with `@AGENTS.md`; each `.claude/skills/<name>/SKILL.md` and `.claude/agents/reviewer.md` tells Claude to load the `.agents` file.
  2. Tool-specific steps inside a shared file are labelled **In Antigravity:** / **In Claude Code:**, as in `/review`.
  3. One Stop hook script, `scripts/hooks/stop_gate.py`, serves both tools. It recognises the caller from its stdin payload and replies in that tool's format.
  4. Only the two pairings in use are verified: Antigravity on macOS, Claude Code on Windows. Either tool may work on the other OS, but nothing checks it.
- **Rejected:**
  - Symlinks from `.claude/` to `.agents/`: git on Windows checks them out as plain text files.
  - Full copies: they drift.
- **Consequences:**
  - A harness test fails when an `.agents` skill has no `.claude` stub, or when either tool's config doesn't wire `stop_gate.py`.
  - Every harness change is checked against both tools. Things only verifiable inside a tool, such as Antigravity's subagent tool names, are tracked as feature_list items.
  - Antigravity's `.agents/hooks.json` calls `python3`, which on Windows can be the Microsoft Store stub. That doesn't matter while Antigravity runs only on the Mac.
