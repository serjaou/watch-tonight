# Owner's Workflow & SDLC Guide

A 1-page reference for how you and the agents work together in 30–90 minute sessions, on the Mac or the Windows laptop, in Antigravity or Claude Code (ADR 0003). The rules agents follow live in [AGENTS.md](../AGENTS.md); this page explains them for you.

---

## 1. The Golden Rule of Context

> **Chat history is disposable; the git repository is the state machine.**

Each tool keeps its chat history on the machine where it ran (Antigravity in `~/.gemini/`, Claude Code in its config directory). Everything the next session needs **must** be in the repo, pushed, before you close the laptop:

| Memory Type | File | Who Updates It |
|---|---|---|
| **Short-term session state** (branch, progress, blockers) | [PROGRESS.md](../PROGRESS.md) | Agent at `/handoff` (every session) |
| **Backlog, status & verification evidence** | [feature_list.json](../feature_list.json) | Agent updates status/evidence; you own scope & order |
| **Feature requirements & acceptance tests** | `docs/specs/NN-slug.md` | Agent interviews you via `/spec`; only you set `status: approved` |
| **Timeboxed investigation answers** | `docs/spikes/NN-slug.md` | Agent records findings during a spike |
| **Architectural decisions ("why")** | `docs/decisions/NNNN-title.md` | Written when a non-obvious design choice is made |
| **Your Python & AI learning progress** | [LEARNING.md](../LEARNING.md) | Tutor via `/tutor` and `/defend` |
| **Agent failures & harness improvements** | [docs/harness-log.md](harness-log.md) | Logged whenever a gate, handoff, or actor fails |

---

## 2. The Session Cycle (30–90 min, any machine, either tool)

1. **Start (`/start`)**
   - Pulls, runs `uv sync` + `uv run poe check`, checks the last CI run, reads `PROGRESS.md` and `feature_list.json`, and tells you in ≤8 lines what is ready and what it proposes. It waits for your "go".
2. **Work (1 phase at a time)**
   - Follows the Task Cycle below. Each phase ends with a report, and the agent waits for you to start the next one.
   - Anytime you see unfamiliar Python or framework code, type **`/tutor <topic>`** for a C#/.NET comparison, or **`/tutor quiz`** for a 5-question retention check.
3. **Close (`/handoff`: always run it before stopping or switching machines)**
   - Rewrites the `Now` section of `PROGRESS.md`, updates `feature_list.json`, saves new knowledge to docs/ADRs, commits (WIP is fine) and pushes the feature branch.

---

## 3. The Task Cycle (stepped, ADR 0004)

Every non-trivial feature goes through 5 phases. **You start each phase**; the agent finishes it, reports, and stops.

```
[1. DEFINE (/spec)] ──▶ [2. BUILD ("build it")] ──▶ [3. REVIEW (/review)] ──▶ [4. DEFEND (/defend)] ──▶ [5. CLOSE (/handoff)]
  you approve the spec    Stop hook enforces          read-only reviewer         you answer 3 "why"s       green check, push branch
```

| Phase | What happens |
|---|---|
| **1. Define (`/spec`)** | The agent interviews you (max 5 questions at a time) and drafts `docs/specs/NN-slug.md` with acceptance tests. If an unknown blocks the design, it proposes a `spike` first. **You set `status: approved`.** |
| **2. Build** | You say **"build it"**. The agent writes code and unit tests. The **Stop hook** (`stop_gate.py`) won't let it finish a turn that changed code while `uv run poe check` fails (it gives up after 3 attempts and hands back to you). |
| **3. Review (`/review`)** | The read-only **reviewer subagent** compares the branch diff with the spec. You read the findings and decide what to fix. |
| **4. Defend (`/defend`)** | The tutor asks you **3 Socratic "why" questions** about the diff, one at a time, compares with C#, and updates `LEARNING.md`. |
| **5. Close (`/handoff`)** | Updates `PROGRESS.md` and `feature_list.json` (with command + output `evidence`), commits and pushes the feature branch. You merge to `main` after green CI. |

Unattended or overnight runs are not designed yet (ADR 0004): they'll be designed when a real task needs one.

---

## 4. Quick Command & Actor Reference

The source of every skill is in `.agents/`. Claude Code loads the same files through thin stubs in `.claude/` (ADR 0003).

| What you type | What runs | Purpose |
|---|---|---|
| `/start` | [.agents/skills/start/SKILL.md](../.agents/skills/start/SKILL.md) | Pull, run `poe check`, check CI, read state, propose today's plan |
| `/spec` | [.agents/skills/spec/SKILL.md](../.agents/skills/spec/SKILL.md) | Interview you to create/refine a 1-page spec or propose a spike |
| `/review` | [.agents/skills/review/SKILL.md](../.agents/skills/review/SKILL.md) + [reviewer.md](../.agents/agents/reviewer.md) | Run the read-only reviewer subagent (branch diff vs spec) |
| `/tutor <topic>` | [.agents/skills/tutor/SKILL.md](../.agents/skills/tutor/SKILL.md) | Explain a concept in our code with a C# comparison (or `/tutor quiz`) |
| `/defend` | [.agents/skills/defend/SKILL.md](../.agents/skills/defend/SKILL.md) | 3 Socratic "why" questions on the diff + update `LEARNING.md` |
| `/handoff` | [.agents/skills/handoff/SKILL.md](../.agents/skills/handoff/SKILL.md) | Persist session state to `PROGRESS.md` & `feature_list.json`, commit & push |
| *(Automatic on stop)* | [.agents/hooks.json](../.agents/hooks.json) (Antigravity) and [.claude/settings.json](../.claude/settings.json) (Claude Code) → [stop_gate.py](../scripts/hooks/stop_gate.py) | Blocks the agent from ending a coding turn while `uv run poe check` fails (up to 3 retries) |
| `uv run poe check` | [pyproject.toml](../pyproject.toml) | Runs `ruff check`, `ruff format --check`, `pyright`, `lint-imports`, and fast `pytest` |
