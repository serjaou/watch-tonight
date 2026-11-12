# 0004. Agents run a ready task end to end; the owner decides at the gates

- **Date:** 2026-11-12
- **Status:** Accepted. Supersedes decision 2 of [0002](0002-full-harness-upfront-with-stepped-mode.md).
- **Context:**
  - ADR 0002 described two execution modes: Stepped (the owner triggers each phase) and Autonomous (the agent chains build, review, fixes and push). Nothing in the repo selected or enforced either; they existed only as prose. In practice agents chained phases anyway, e.g. running `/handoff` without being asked.
  - The point of a harness is that agents complete tasks "without constant human supervision" (learn-harness-engineering README). The human sets the direction (goal and stop condition), reviews the output and improves the rules (L13).
  - Running autonomously has costs the course names (L13): "comprehension rot" and "cognitive surrender", the owner's understanding drifting from the code.
- **Decision:**
  1. **One default, no modes.** Once a task is ready, the agent runs it end to end without asking: build → `uv run poe check` (Stop hook) → `/review` → fix findings (at most 2 rounds) → `/handoff` steps (PROGRESS.md, feature_list.json, commit, push the branch) → open a PR (or give the owner the link) → report and stop. The next task starts after the owner merges.
  2. **The owner decides at the gates:** approving a spec (`status: approved`), merging a PR, and any question that needs a human decision: the spec looks wrong, an unknown changes the design, the check is still red after 3 attempts, or a review finding changes the scope. At those points the agent stops and asks.
  3. **Opt-out:** when the owner says "step by step" (for a task or the session), the agent stops after each phase and waits.
  4. **Enforced, not just written:** branch protection on `main` (PR + green CI required; a GitHub setting the owner turns on), and a CI check that fails a PR touching `tests/acceptance/` or `evals/` unless the owner adds the `tests-approved` label.
  5. **`/defend` is optional** and not part of the workflow. The owner runs it when they want to discuss a feature, a commit or the current branch. This accepts the comprehension risk above in exchange for less friction; `/tutor` and `/defend` stay available.
- **Consequences:**
  - The Claude Code skill stubs are model-invocable again, so the agent can run `/review` and `/handoff` itself.
  - Unattended loops across several tasks (overnight runs, Ralph loops) are still not designed: autonomy here is one task per run, ending at a PR.
  - If the owner finds they can no longer explain merged code, the fix is to make `/defend` (or a lighter check) part of the merge gate again.
