# Handoff: `feat-013` — Record the owner decisions of 2026-11-13

- **Type:** `chore`
- **Date:** 2026-11-13
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `0`
- **Reviewer (rounds / findings):** `2 (7 + 3)`
- **Escaped / owner fixes:** `0`

## Summary & Outcome
- Recorded the owner's decisions on architecture Q8–Q11 (no-pitch fallback, any input language, React, LLM filters over a closed vocabulary), posters, zero-cost budget, and a provider-neutral LLM spike across `docs/product.md`, `docs/architecture.md`, `docs/spikes/08`, `10`, `11`, and `AGENTS.md`.
- Reviewer subagent found `7 + 3` consistency gaps (UI vs text constraints, extraction eval, state precedence), all fixed.

## Verification Evidence
```text
Windows, 2026-11-13:
- Decisions recorded in docs/product.md, docs/architecture.md (Decided table Q8-Q11, new Q13), docs/spikes/08, 10, 11 and AGENTS.md.
- uv run poe check -> ruff: All checks passed!; pyright: 0 errors; lint-imports: 2 kept, 0 broken; pytest: 25 passed.
- Reviewer subagent: round 1, 7 findings fixed; round 2, 3 findings fixed (max 2 rounds, ADR 0004).
```
