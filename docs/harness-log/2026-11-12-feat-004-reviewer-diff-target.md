# Harness Log: `2026-11-12` · Windows · Claude Code (`feat-004`) — Reviewer diff target (`origin/main` vs `HEAD`)

- **Finding:** The reviewer subagent diffed against `HEAD`, so after a WIP commit it saw no changes and would answer `"No findings"`.
- **Layer:** `verification`.
- **Root cause:** `git diff HEAD` shows only uncommitted changes; the template had `origin/main...HEAD`.
- **Harness change:** Reviewer and `/defend` use `git diff origin/main` plus `git status --short`.
- **Lesson:** L09 separate worker and checker, and check that the checker sees the work.
