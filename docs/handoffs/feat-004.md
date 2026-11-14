# Handoff: `feat-004` — Harness review: first Windows session and Claude Code support

- **Type:** `chore`
- **Date:** 2026-11-12
- **Machine · Tool:** Windows · Claude Code
- **Stop-gate blocks:** `1` *(intentional test)*
- **Reviewer (rounds / findings):** `n/a` *(fixed reviewer diff target)*
- **Escaped / owner fixes:** `1` *(piped commit slip, fixed in session)*

## Summary & Outcome
- First Windows session: installed `uv`; found red CI (git-state-dependent test), Windows encoding/BOM bugs in the Stop hook, a reviewer that missed committed work, and a pre-commit/project ruff mismatch — all fixed and logged in [docs/harness-log.md](../harness-log.md).
- Added Claude Code support (ADR 0003), autonomous task runs with owner gates (ADR 0004), PR gates CI, English-only launch, 350-character pitches, and backlog `feat-005`…`feat-011`.

## Verification Evidence
```text
Windows, 2026-11-12:
uv run poe check
-> ruff: All checks passed!
-> pyright strict: 0 errors
-> lint-imports: 2 kept, 0 broken
-> pytest: 25 passed

pre-commit run --all-files -> gitleaks, ruff check, ruff format: Passed.
Real Claude Code Stop hook (uv run --no-sync python scripts/hooks/stop_gate.py with a Stop payload):
-> decision block on a real F401 lint error, no output when green.
CI on GitHub and Antigravity on the Mac: verified in feat-007.
```
