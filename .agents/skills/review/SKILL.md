---
name: review
description: >-
  Run the independent read-only Reviewer subagent to check the current diff
  against the active feature's spec. Use after implementation and `uv run poe
  check` pass, or when the owner types /review.
---

# Independent code review (`/review`)

1. `uv run poe check` must pass first. If it fails, report that and stop: don't run the reviewer.
2. Spawn the read-only reviewer with the instructions in [.agents/agents/reviewer.md](../../agents/reviewer.md) and the active spec path (`docs/specs/NN-slug.md`, see PROGRESS.md):
   - **In Antigravity:** use the `reviewer` subagent via `invoke_subagent` (`TypeName: "reviewer"`, loaded from `.agents/agents/reviewer.md`) and pass it the spec path.
   - **In Claude Code:** use the `reviewer` subagent (`.claude/agents/reviewer.md`, which loads the same instructions) and pass it the spec path.
3. Fix the findings, then rerun `uv run poe check` and the reviewer: at most 2 rounds (ADR 0004).
   - Stop and ask the owner instead if a finding changes the scope or the spec.
   - In the final report, quote any finding you didn't fix and say why.
   - If the owner asked for "step by step", show the findings verbatim and wait instead of fixing.
