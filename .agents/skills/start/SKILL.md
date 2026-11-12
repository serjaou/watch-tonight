---
name: start
description: >-
  Start-of-session routine. Use when the owner opens a new session, switches
  machines, or types /start.
---

# Start of session (`/start`)

1. Run the **Session start protocol** in [AGENTS.md](../../../AGENTS.md), steps 1–4.
2. For the CI result, use `gh run list --branch <branch> --limit 1` if `gh` is installed; otherwise ask the owner to check the Actions tab on GitHub.
3. Send the step-4 report. Then continue or wait for "go", as step 4 says.
