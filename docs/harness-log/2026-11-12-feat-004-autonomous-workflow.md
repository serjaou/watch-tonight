# Harness Log: `2026-11-12` · Windows · Claude Code (`feat-004`) — Autonomous workflow & owner gates (ADR 0004)

- **Finding:** Agents chained phases on their own (e.g. ran `/handoff` and further steps without asking). The Stepped/Autonomous modes existed only as prose, and "Session end protocol (always, even mid-task)" read as permission to run it unprompted. Skills also restated `AGENTS.md` and had drifted from it.
- **Layer:** `context`.
- **Root cause:** Declarative modes with nothing selecting or enforcing them; the same rule written in several places.
- **Harness change:** ADR 0004: one default, no modes. A ready task runs end to end (build, check, review + fixes, handoff, PR); the owner decides at spec approval, merge and any human-decision point, and can ask for `"step by step"`. `/defend` is optional. The rules that matter are enforced, not just written: branch protection on `main` and a CI gate on `tests/acceptance/` and `evals/` (`tests-approved` label). Skills point to `AGENTS.md` instead of restating it.
- **Note:** The owner first chose "stepped only", then reversed it the same day: the point of a harness is that agents complete tasks without constant supervision, and the gates are what make that safe.
- **Lesson:** L04 one source per rule; L13 the human sets direction and decides at the gates, the harness makes the rest safe.
