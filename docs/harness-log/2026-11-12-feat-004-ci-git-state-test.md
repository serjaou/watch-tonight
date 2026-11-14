# Harness Log: `2026-11-12` · Windows · Claude Code (`feat-004`) — Git-state-dependent stop-gate test

- **Finding:** CI had been red since `26f3ebf`. `test_stop_gate_blocks_on_failure_and_allows_on_success` only passed on a working tree with uncommitted code changes (the Mac during the dry run); on a clean checkout the gate correctly allowed stopping and the test failed. `PROGRESS.md` listed CI as unverified, but no step made a session check it.
- **Layer:** `verification`.
- **Root cause:** The test ran the gate against the real repo, so its result depended on the repo's git state (a hidden input, like a test that reads the clock).
- **Harness change:** The test runs a copy of the gate in a throwaway git repo (`gate_repo`). `/start` checks the latest CI run; a red CI is the session's task (`AGENTS.md`).
- **Lesson:** L09 premature victory: a sensor that was never seen failing isn't proven.
