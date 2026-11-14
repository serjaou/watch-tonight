# Handoff: `feat-005` — Architecture v0 and spike question files

- **Type:** `chore`
- **Date:** 2026-11-13
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (12 + 2)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- Wrote `docs/architecture.md` v0 (components, layers and ports, 7-step query flow, offline pipeline, data model, cross-cutting, open questions Q1–Q12) and the spike question files (`docs/spikes/08`, `09`, `10`, `11`).
- Reviewer subagent found `12 + 2` design gaps (P3 avoid check, Partial vs bad LLM output, per-result availability date, spike methods), all fixed; added runtime-LLM spike `feat-011` (`feat-012` is refinement).

## Verification Evidence
```text
Windows, 2026-11-13:
- docs/architecture.md (128 lines) and docs/spikes/08, 09, 10, 11 with explicit questions tied to the design decisions they change.
- uv run poe check -> ruff: All checks passed!; pyright: 0 errors; lint-imports: 2 kept, 0 broken; pytest: 25 passed.
- Reviewer subagent: round 1, 12 findings fixed; round 2, 2 findings fixed (max 2 rounds, ADR 0004).
```
