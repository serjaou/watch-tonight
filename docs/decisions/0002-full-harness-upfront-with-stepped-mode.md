# 0002. Build core harness upfront with Stepped vs. Autonomous execution modes

- **Date:** 2026-11-12
- **Status:** Accepted
- **Context:** `docs/inception/harness-workflow.md` originally proposed adding harness pieces incrementally across 6 weeks (`v0`–`v5`). However, the owner already has production experience with multi-agent workflows and wants the Learning Tutor (`/tutor`, `/defend`), Read-Only Reviewer (`/review`), and Stop hook (`stop_gate.py`) active from the very first product task. At the same time, the owner wants manual visibility into each actor now without blocking future unattended/overnight runs.
- **Decision:**
  1. Set up the complete core harness upfront (`AGENTS.md`, `PROGRESS.md`, `LEARNING.md`, `feature_list.json`, `stop_gate.py`, Reviewer subagent, `/start`, `/spec`, `/review`, `/tutor`, `/defend`, `/handoff`, and `tests/harness/test_harness.py`) and validate it with a dry run (`feat-000`) before starting product spikes.
  2. Support two execution modes over the same modular skills (`docs/workflow.md`):
     - **Stepped Mode (default now):** Human triggers `Build` → `/review` → `/defend` → `/handoff` step by step to inspect each actor.
     - **Autonomous Mode (future/overnight):** For features with `status: approved` specs, the agent chains `Build` + Stop hook + Reviewer (up to 2 rounds) + branch commit/push automatically, leaving `/defend` and merge for the owner.
- **Consequences:**
  - Every product spike and feature benefits from the Tutor, Reviewer, and deterministic gates from day one.
  - No harness rewrite is needed when transitioning from manual sessions to overnight runs.
