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
   - **In Antigravity:** spawn a read-only subagent using `invoke_subagent` (with `TypeName: "research"` or a subagent defined via `define_subagent` with `EnableWriteTools: false`), passing it the reviewer instructions and the spec path.
   - **In Claude Code:** use the `reviewer` subagent (`.claude/agents/reviewer.md`, which loads the same instructions) and pass it the spec path.
3. Show the owner the reviewer's findings verbatim. Fix nothing unless the owner asks (stepped workflow, ADR 0004).
