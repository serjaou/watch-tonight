---
name: review
description: >-
  Run the independent read-only Reviewer subagent to check the current diff
  against the active feature's spec. Use after implementation and `uv run poe
  check` pass, or when the owner types /review.
---

# Independent Code Review (`/review`)

1. Verify that `uv run poe check` passes first. Do not run the Reviewer if deterministic checks are failing.
2. Read the reviewer instructions in [.agents/agents/reviewer.md](../../agents/reviewer.md).
3. Spawn a read-only subagent using `invoke_subagent` (with `TypeName: "research"` or a subagent defined via `define_subagent` with `EnableWriteTools: false`), passing it:
   - The instructions from `.agents/agents/reviewer.md`
   - The path to the active feature's spec (`docs/specs/NN-slug.md`)
   - Instructions to inspect `git diff` against `HEAD` / `main` and report findings.
4. When the Reviewer subagent replies:
   - **In Stepped Mode (default):** show the Reviewer's exact findings to the owner and ask before applying fixes (unless the finding is a trivial bug).
   - **In Autonomous Mode:** fix the findings and re-run `uv run poe check` + Reviewer for at most **2 rounds**.
