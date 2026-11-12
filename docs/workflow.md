# Owner's Workflow & SDLC Guide

A 1-page reference for how you and the agents work together in 30–90 minute sessions: Antigravity on the Mac, Claude Code on the Windows laptop (ADR 0003). The rules agents follow live in [AGENTS.md](../AGENTS.md); this page explains them for you.

---

## 1. The Golden Rule of Context

> **Chat history is disposable; the git repository is the state machine.**

Each tool keeps its chat history on the machine where it ran. Everything the next session needs **must** be in the repo, pushed, before you close the laptop:

| Memory Type | File | Who Updates It |
|---|---|---|
| **Short-term session state** (branch, progress, blockers) | [PROGRESS.md](../PROGRESS.md) | Agent at `/handoff` (end of every task or session) |
| **Backlog, status & verification evidence** | [feature_list.json](../feature_list.json) | Agent updates status/evidence; you own scope & order |
| **Feature requirements & acceptance tests** | `docs/specs/NN-slug.md` | Agent interviews you via `/spec`; only you set `status: approved` |
| **Timeboxed investigation answers** | `docs/spikes/NN-slug.md` | Agent records findings during a spike |
| **Architectural decisions ("why")** | `docs/decisions/NNNN-title.md` | Written when a non-obvious design choice is made |
| **Your Python & AI learning progress** | [LEARNING.md](../LEARNING.md) | Tutor via `/tutor` and `/defend` (when you run them) |
| **Agent failures & harness improvements** | [docs/harness-log.md](harness-log.md) | Logged whenever a gate, handoff, or actor fails |

---

## 2. The Session Cycle (30–90 min)

1. **Start (`/start`):** pulls, runs `uv sync` + `uv run poe check`, checks the last CI run, reads `PROGRESS.md` and `feature_list.json`, and reports in ≤8 lines. If the next item is ready, it gets going; otherwise it waits for you.
2. **Work:** the agent runs one ready task end to end (section 3), or interviews you with `/spec` if nothing is ready.
3. **Close:** the agent runs `/handoff` itself at the end of each task. If you stop mid-task or switch machines, type **`/handoff`** so the work is committed and pushed.

---

## 3. The Task Cycle (ADR 0004)

**You decide at the gates; the agent does everything in between.**

```
YOU                         AGENT (autonomous)                                              YOU
[1. /spec: approve] ──▶ [2. build ─ Stop hook ─ 3. /review + fixes ─ 4. /handoff + PR] ──▶ [5. review PR, merge]
```

| Step | Who | What happens |
|---|---|---|
| **1. Define (`/spec`)** | You + agent | The agent interviews you (only questions that change the design or the acceptance tests, most important first) and drafts `docs/specs/NN-slug.md` with acceptance tests. If an unknown blocks the design, it proposes a `spike` first. **You set `status: approved`**: that's the goal and the stop condition. |
| **2. Build** | Agent | Writes code and unit tests. The **Stop hook** (`stop_gate.py`) won't let it finish a turn that changed code while `uv run poe check` fails (after 3 attempts it stops and asks you). |
| **3. Review (`/review`)** | Agent | The read-only **reviewer subagent** compares the branch with the spec; the agent fixes the findings (max 2 rounds) and reports any it didn't fix. |
| **4. Close (`/handoff`)** | Agent | Updates `PROGRESS.md` and `feature_list.json` (with command + output `evidence`), commits, pushes the branch and opens a PR (or gives you the link). Then it stops. |
| **5. Merge** | You | Review the PR, wait for green CI, merge. The next task starts from the updated `main`. |

**The agent also stops and asks you** when the spec looks wrong, an unknown changes the design, or a review finding changes the scope.

**Want to watch each step?** Say **"step by step"** (for a task or the whole session): the agent stops after each phase and waits for you.

**Learning on demand:** `/tutor <topic>` explains a concept with a C# comparison, and `/tutor quiz` checks retention. `/defend [feat-XXX | commit | range]` asks you 3 "why" questions about those changes and logs them in `LEARNING.md`. Both are optional; run them whenever you want, e.g. while reviewing a PR.

---

## 4. Quick Command & Actor Reference

The source of every skill is in `.agents/`. Claude Code loads the same files through thin stubs in `.claude/` (ADR 0003).

| What you type | What runs | Purpose |
|---|---|---|
| `/start` | [.agents/skills/start/SKILL.md](../.agents/skills/start/SKILL.md) | Pull, run `poe check`, check CI, read state, report and continue if ready |
| `/spec` | [.agents/skills/spec/SKILL.md](../.agents/skills/spec/SKILL.md) | Interview you to create/refine a 1-page spec or propose a spike |
| `/review` | [.agents/skills/review/SKILL.md](../.agents/skills/review/SKILL.md) + [reviewer.md](../.agents/agents/reviewer.md) | Read-only reviewer (branch vs spec); the agent fixes findings. Runs automatically within a task |
| `/handoff` | [.agents/skills/handoff/SKILL.md](../.agents/skills/handoff/SKILL.md) | Persist state to `PROGRESS.md` & `feature_list.json`, commit, push, PR. Runs automatically at task end |
| `/tutor <topic>` | [.agents/skills/tutor/SKILL.md](../.agents/skills/tutor/SKILL.md) | Explain a concept in our code with a C# comparison (or `/tutor quiz`) |
| `/defend [target]` | [.agents/skills/defend/SKILL.md](../.agents/skills/defend/SKILL.md) | Optional: 3 Socratic "why" questions on a branch, feature or commit + update `LEARNING.md` |
| *(Automatic on stop)* | [.agents/hooks.json](../.agents/hooks.json) (Antigravity) and [.claude/settings.json](../.claude/settings.json) (Claude Code) → [stop_gate.py](../scripts/hooks/stop_gate.py) | Blocks the agent from ending a coding turn while `uv run poe check` fails (up to 3 retries) |
| *(Automatic on PR)* | [.github/workflows/](../.github/workflows/) | `CI`: `uv run poe check`. `PR gates`: fails if `tests/acceptance/` or `evals/` changed without your `tests-approved` label |
| `uv run poe check` | [pyproject.toml](../pyproject.toml) | Runs `ruff check`, `ruff format --check`, `pyright`, `lint-imports`, and fast `pytest` |
