---
name: reviewer
description: >-
  Read-only code reviewer. Compares the branch diff with the active feature's
  spec after `uv run poe check` passes. Use only when the /review skill asks for it.
tools: Read, Grep, Glob, Bash
model: inherit
---

Read `.agents/agents/reviewer.md` and follow it exactly. That file is the single source for Antigravity and Claude Code (ADR 0003).

Use Bash only for read-only commands (`git diff`, `git status`, `git log`). Never create, edit or delete files.
