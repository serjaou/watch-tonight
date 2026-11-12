# Owner's Workflow & SDLC Guide

A 1-page reference for how you and the agents work together in 30–90 minute sessions across your Mac and Windows laptops.

---

## 1. The Golden Rule of Context

> **Chat history is disposable; the git repository is the state machine.**

Antigravity's chat history (`~/.gemini/...`) stays on the machine where it ran. Everything the next session needs **must** be written into the repo before you close the laptop:

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

## 2. The Session Cycle (30–90 min, any PC)

1. **Start (`/start`)**
   - Pulls latest git changes, runs `uv sync` + `uv run poe check`, reads `PROGRESS.md` and `feature_list.json`, and tells you in ≤8 lines what is ready and what it will do today.
2. **Work (1 task at a time)**
   - Follows the Task Cycle below (either refining a spec, running a spike, or building/reviewing/defending an approved feature).
   - Anytime you see unfamiliar Python or framework code, type **`/tutor <topic>`** for a C#/.NET comparison, or **`/tutor quiz`** for a 5-question retention check.
3. **Close (`/handoff` — always run before stopping or switching PCs)**
   - Rewrites the `Now` section of `PROGRESS.md` (including `Waiting on owner: refine feat-XXX` if the next item isn't ready), updates `feature_list.json`, saves any new knowledge to docs/ADRs, commits (WIP is fine on a branch), and pushes.

---

## 3. The Task Cycle (SDLC)

Every non-trivial feature goes through 5 phases. Only **Phase 1 (Spec approval)** and **Phase 4 (Defend & Merge)** require human judgment; Phases 2 and 3 are governed by deterministic sensors and the read-only Reviewer subagent.

```
[1. DEFINE (/spec)] ──▶ [2. BUILD + Stop Hook] ──▶ [3. REVIEW (/review)] ──▶ [4. DEFEND (/defend)] ──▶ [5. HANDOFF / MERGE]
   (Human approves)        (Autonomous)               (Autonomous)             (Human answers 3 Qs)       (Green CI + push)
```

### Two Ways to Run Phases 2 & 3

| Phase | **Stepped Mode (Default now)** — *You trigger each actor to observe & learn* | **Autonomous Mode (Future / Overnight)** — *For pre-approved specs* |
|---|---|---|
| **1. Define (`/spec`)** | Agent interviews you (max 5 questions) → drafts `docs/specs/NN-slug.md` + acceptance tests. If an unknown blocks design, spawns a `spike` first. **You set `status: approved`.** | Done beforehand (you approve 1–3 specs during the week). |
| **2. Build** | You say **"Build it"**. Agent writes code + unit tests. The **Stop hook** (`stop_gate.py`) blocks the agent from finishing until `uv run poe check` passes. Agent then pauses for you. | Agent picks the next `approved` feature automatically, implements it, and loops until `uv run poe check` passes. |
| **3. Review (`/review`)** | You say **`/review`**. Spawns the read-only **Reviewer subagent** to compare `git diff` against the spec. You inspect findings and tell the agent to fix them. | Agent automatically invokes the Reviewer subagent and fixes findings (up to 2 rounds) until `"No findings"`. |
| **4. Defend (`/defend`)** | You type **`/defend`**. The Tutor asks you **3 Socratic "why" questions** about the diff (one at a time), compares with C#, and updates `LEARNING.md`. | Waiting for you in the morning before you merge the PR. |
| **5. Close (`/handoff`)** | Updates `PROGRESS.md` and `feature_list.json` (with command + output `evidence`), commits, and pushes. | Agent commits, pushes the branch, updates `PROGRESS.md`, and stops. |

---

## 4. Quick Command & Actor Reference

| What you type | What runs | Purpose |
|---|---|---|
| `/start` | [.agents/skills/start/SKILL.md](../.agents/skills/start/SKILL.md) | Pull, run `poe check`, read state, propose today's 3-line plan |
| `/spec` | [.agents/skills/spec/SKILL.md](../.agents/skills/spec/SKILL.md) | Interview you to create/refine a 1-page spec or spawn a spike |
| `/review` | [.agents/skills/review/SKILL.md](../.agents/skills/review/SKILL.md) + [reviewer.md](../.agents/agents/reviewer.md) | Run the read-only Reviewer subagent (`git diff` vs spec) |
| `/tutor <topic>` | [.agents/skills/tutor/SKILL.md](../.agents/skills/tutor/SKILL.md) | Explain a concept in our code with a C# comparison (or `/tutor quiz`) |
| `/defend` | [.agents/skills/defend/SKILL.md](../.agents/skills/defend/SKILL.md) | 3 Socratic "why" questions on the diff + update `LEARNING.md` |
| `/handoff` | [.agents/skills/handoff/SKILL.md](../.agents/skills/handoff/SKILL.md) | Persist session state to `PROGRESS.md` & `feature_list.json`, commit & push |
| *(Automatic on stop)* | [.agents/hooks.json](../.agents/hooks.json) → [stop_gate.py](../scripts/hooks/stop_gate.py) | Blocks the agent from ending a coding turn if `uv run poe check` fails (up to 3 retries) |
| `uv run poe check` | [pyproject.toml](../pyproject.toml) | Runs `ruff check`, `ruff format --check`, `pyright`, `lint-imports`, and fast `pytest` |
