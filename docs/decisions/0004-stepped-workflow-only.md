# 0004. Stepped workflow only; drop the Autonomous mode until a real need exists

- **Date:** 2026-11-12
- **Status:** Accepted. Supersedes decision 2 of [0002](0002-full-harness-upfront-with-stepped-mode.md).
- **Context:** ADR 0002 described two execution modes, Stepped (the owner triggers each phase) and Autonomous (the agent chains build, review, fixes and push). Nothing in the repo selected or enforced either mode: they existed only as prose in `docs/workflow.md` and the `/review` skill. In practice agents chained phases on their own, for example running `/handoff` and other steps without asking. The `AGENTS.md` heading "Session end protocol (always, even mid-task)" also read as permission to run the handoff unprompted.
- **Decision:**
  1. There is one workflow, the stepped one. Each phase (`/spec`, build, `/review`, `/defend`, `/handoff`) ends with a report, and the agent starts the next phase only when the owner asks for it in their latest message. This rule lives in `AGENTS.md`.
  2. The session end protocol runs when the owner ends the session or types `/handoff`, never on the agent's own initiative. Commits and pushes happen only during `/handoff` or when the owner asks.
  3. Unattended or overnight runs are out of scope for now. When a real task needs one (e.g. the enrichment batch), it gets its own design: a goal, a verification command, a stop condition and a turn/cost budget (course L13), on its own branch and never merging to `main`.
- **Consequences:**
  - Instructions describe only what is enforced or expected now; there is no mode for the agent to guess.
  - More owner prompts per feature. That is intended while the owner is learning (brief R4).
  - The Stop hook and the reviewer stay: they are gates within a phase, not a mode.
