# Harness Log Index

Records every time an agent, hook, or handoff fails or reveals a gap. Each incident has its own detail file in `docs/harness-log/<YYYY-MM-DD>-<slug>.md` (**Entry format:** Finding · **Layer** (`spec`, `context`, `environment`, `verification` or `state`) · Root cause · Harness change · Lesson).

---

| Date | Machine · Tool | Feature | Layer | Summary & Lesson | Entry |
|---|---|---|---|---|---|
| 2026-11-13 | Mac · Antigravity | `feat-014` | `state` / `verification` | Validated harness with `validate-harness.mjs` (`60/100` → `92/100`); added `init.sh`, feature `description` sensor, and aligned `AGENTS.md` headings. | [2026-11-13-feat-014-validate-harness.md](harness-log/2026-11-13-feat-014-validate-harness.md) |
| 2026-11-12 | Mac · Antigravity | `feat-007` | `verification` / `context` | `stop_gate.py` unlinks `.harness/stop_gate_attempts` when changes are reverted; `/review` uses native `TypeName: "reviewer"`. | [2026-11-12-feat-007-mac-stop-gate-and-reviewer.md](harness-log/2026-11-12-feat-007-mac-stop-gate-and-reviewer.md) |
| 2026-11-12 | Windows · Claude Code | `feat-004` | `verification` | `stop_gate.py` test ran against the real repo and failed on clean CI checkouts; moved test to a throwaway git repo (`gate_repo`) and made `/start` check CI. | [2026-11-12-feat-004-ci-git-state-test.md](harness-log/2026-11-12-feat-004-ci-git-state-test.md) |
| 2026-11-12 | Windows · Claude Code | `feat-004` | `environment` | Fresh Windows clone lacked `uv` and `pre-commit install` instructions; added "Machine setup" table to `README.md`. | [2026-11-12-feat-004-fresh-machine-setup.md](harness-log/2026-11-12-feat-004-fresh-machine-setup.md) |
| 2026-11-12 | Windows · Claude Code | `feat-004` | `verification` | Windows `cp1252` default encoding and PowerShell UTF-8 BOM broke `stop_gate.py`; forced `utf-8` / `utf-8-sig` and stripped shell encoding overrides in tests. | [2026-11-12-feat-004-windows-stop-hook-encoding.md](harness-log/2026-11-12-feat-004-windows-stop-hook-encoding.md) |
| 2026-11-12 | Windows · Claude Code | `feat-004` | `verification` | Reviewer diffed against `HEAD` and missed committed WIP changes; changed reviewer and `/defend` to diff against `origin/main`. | [2026-11-12-feat-004-reviewer-diff-target.md](harness-log/2026-11-12-feat-004-reviewer-diff-target.md) |
| 2026-11-12 | Windows · Claude Code | `feat-004` | `context` | Prose-only Stepped/Autonomous modes drifted across skills; replaced with single autonomous flow + enforced gates (ADR 0004) and deduplicated skills. | [2026-11-12-feat-004-autonomous-workflow.md](harness-log/2026-11-12-feat-004-autonomous-workflow.md) |
| 2026-11-12 | Windows · Claude Code | `feat-004` | `environment` | `.pre-commit-config.yaml` and `uv.lock` pinned different `ruff` versions; changed pre-commit to run `uv run --no-sync ruff`. | [2026-11-12-feat-004-ruff-version-pin.md](harness-log/2026-11-12-feat-004-ruff-version-pin.md) |
| 2026-11-12 | Mac · Antigravity | `feat-001` | `environment` | Antigravity ran `.agents/hooks.json` with `.agents/` as cwd and without `/opt/homebrew/bin` on `PATH`; resolved `REPO_ROOT` and `uv` paths explicitly in `stop_gate.py`. | [2026-11-12-feat-001-stop-gate-env.md](harness-log/2026-11-12-feat-001-stop-gate-env.md) |
