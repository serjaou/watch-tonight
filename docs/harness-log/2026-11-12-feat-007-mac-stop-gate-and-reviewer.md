# Harness Log: `2026-11-12` · Mac · Antigravity (`feat-007`) — Stop-gate counter cleanup & native reviewer

- **Finding:** Two details surfaced when verifying `feat-004` in Antigravity on the Mac:
  1. After the live `Stop` hook blocked on a temporary lint error (`attempt 2/3`), reverting the watched file made `has_code_changes()` false, and `stop_gate.py` returned `allow` early without deleting `.harness/stop_gate_attempts` (leaving the counter at `2` for future turns).
  2. Antigravity natively loads `.agents/agents/reviewer.md` as `TypeName: "reviewer"` with `tools: [read_file, run_command]` (`read_file` and `run_command` present; `view_file`, `edit_file` and `write_file` absent), whereas `.agents/skills/review/SKILL.md` still told Antigravity to spawn `TypeName: "research"` or `define_subagent`.
- **Layer:** `verification` / `context`.
- **Root cause:** The `not has_code_changes()` early return skipped counter cleanup; Antigravity's native `.agents/agents/reviewer.md` discovery and tool names had not been verified on the Mac yet.
- **Harness change:** `stop_gate.py` unlinks `COUNTER` when `not has_code_changes()` (asserted in `test_stop_gate_allows_stop_without_checking_when_no_code_changed`), and `.agents/skills/review/SKILL.md` now tells Antigravity to invoke `TypeName: "reviewer"` directly.
- **Lesson:** L10 — exercising the real hook and subagent on the target OS catches state-cleanup edge cases and removes workarounds.
