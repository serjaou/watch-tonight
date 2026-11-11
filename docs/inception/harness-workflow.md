# watch-tonight harness: a simple workflow for working from two computers

**Complements:** `personal-project-brief.md` (its section 8 and the questions Q1–Q2).
**Date:** 10 Nov 2026. **Status:** proposal; nothing is implemented yet.

> **For an AI assistant reading this:** this document says *how* the project is built (the harness); the brief says *what* is built. The templates in section 5 are starting points that the owner must understand and adapt, not final files. Anything marked **(verify)** is untested. The owner wants to learn, so explain your decisions.

---

## 0. TL;DR

1. **The GitHub repo is the only shared memory.** Each tool's memory, chats and artifacts stay on the machine where they were created. Every session, on any machine, starts by reading the repo and ends by writing to it: `PROGRESS.md`, commit and push.
2. **Use harness-creator as an auditor, not as an author.** Build your harness by hand following the course, and use its validator to score it.
3. **The workflow has two cycles.** The **session** cycle lasts 30–90 min: start, work and close. The **task** cycle lasts 1–3 sessions: define, build, review, defend and merge. You step in at only two points: when you approve the spec with its acceptance tests, and at the merge.
4. **The harness grows in levels,** one per week, each tied to a lesson of the course. Start minimal: `AGENTS.md`, `PROGRESS.md` and `poe check`.
5. **The tool is Antigravity,** with a personal Google account. It is installed on the personal Mac first; the work laptop is set up later, in a separate session (§1.6).

---

## 1. Working from two computers

### 1.1 The rule

> If it isn't in the repo and pushed, it doesn't exist for the next session.

This is lesson L03 of the course (*repository as system of record*) and the basis of everything else. Consequences:

- **Antigravity's memory doesn't travel.** Its history and plans are stored in `~/.gemini/...`. If anything there is worth keeping, the agent moves it into a file in the repo.
- **Never end a session with uncommitted changes.** If the task is half done, make a WIP commit on the task branch and push it.
- **Keys (TMDB, Gemini, Atlas) don't go in the repo.** Each machine has its own `.env`, which is in `.gitignore`. The repo only has `.env.example`, and the real values live in your password manager.

### 1.2 What goes where

| Context | File | Who writes it | When it changes |
|---|---|---|---|
| Map and rules for agents | `AGENTS.md` (≤150 lines) | You; the agent may propose changes | Rarely |
| Product: what and why | `docs/product.md` (taken from sections 1–5 of the brief) | You | Rarely |
| Architecture and conventions | `docs/architecture.md`, `docs/conventions.md` | You and the agent | When the design changes |
| Decisions | `docs/decisions/NNNN-title.md` (short ADR, in your words) | You | With every relevant decision |
| Tasks and their status | `feature_list.json` | The agent sets status and evidence; you add, remove or reorder tasks | Every session |
| Spec of a task | `docs/specs/NN-slug.md` (one page at most) | The agent interviews you; you approve it | For every non-trivial feature |
| Spike questions and findings | `docs/spikes/NN-slug.md` | The agent proposes questions and records findings; you review | When an unknown blocks a spec |
| Current state and next step | `PROGRESS.md` | The agent, at the end of the session | **Every session** |
| What you learned | `LEARNING.md` | The tutor, from your answers | Per task |
| Agent failures and harness changes | `docs/harness-log.md` | You | Every time the agent fails |

**Closing rule.** Before finishing, the agent asks itself: *"What do I know now that the next session needs and isn't in the repo?"* The answer goes to the matching row. That way every task leaves code **and** context.

### 1.3 The session cycle (any machine)

```
START (5 min)                       WORK                       CLOSE (5–10 min, always)
git pull                            a single task from         PROGRESS.md: rewrite "Now"
uv sync && uv run poe check   ────▶ feature_list.json    ────▶ and add 1–3 lines to "Log"
the agent reads AGENTS.md →         (task cycle, §3.2)         feature_list.json: status + evidence
PROGRESS.md → active task →                                    ADR / LEARNING / harness-log if needed
its spec                                                       commit + push (WIP is fine)
if poe check fails, fixing it
is the task
```

The protocol lives in `AGENTS.md`. In Antigravity you invoke it with two skills, `/start` and `/handoff` (§5.6).

### 1.4 Switching machines mid-task

1. **On machine A,** run `/handoff`. `PROGRESS.md` ends up with:
   - what is done and what is pending;
   - the branch;
   - the last `poe check` result;
   - what is waiting on a decision from you.

   Then commit WIP and push.
2. **On machine B:** `git pull`, switch to the branch and run `/start`.
3. **Handoff quality test.** If the agent on B has to ask you something that was already settled on A, the handoff failed. Note it in `docs/harness-log.md` and improve the `PROGRESS.md` or `AGENTS.md` template. This is the core practice of harness engineering: every failure becomes a harness improvement.

### 1.5 Windows and macOS: details that avoid problems

| Problem | Decision |
|---|---|
| `make` isn't available on Windows | Use **poethepoet**: `uv run poe check`. Tasks are defined in `pyproject.toml`, it's pure Python and works the same on both systems. It replaces the `make check` of the brief. |
| Bash hooks fail on Windows | Write them in **Python**: `uv run python scripts/hooks/stop_gate.py`. |
| CRLF/LF line endings | Add a `.gitattributes` with `* text=auto eol=lf`. |
| harness-creator's `init.sh` is bash | Replace it with `uv run poe init` (sync + check). |
| Docker for `mongodb-atlas-local` | Mark integration tests with `@pytest.mark.integration`. `poe check` runs only the fast ones and CI runs all of them, so a machine without Docker can still work. |
| Python version | Pin it in `.python-version` (3.13); `uv` installs it on each machine by itself. |
| The UI needs Node.js | Pin the Node version in `.nvmrc` (or `.node-version`). The UI lives in `web/`; once it exists, `poe check` also runs its lint, type check and tests (for example `npm --prefix web run check`). |
| A desktop app on macOS doesn't always inherit your terminal's PATH | If a hook can't find `uv`, put its absolute path in the hook command **(verify)**. |

### 1.6 Before using the work computer (important)

The work laptop is not set up yet. Antigravity will be installed on it in a separate session. Until then, work only from the personal Mac. Before you do:

- **Policy and intellectual property.** Check your contract and EcoVadis's policy on using company equipment and licences for personal projects.
  - In Spain, software that an employee creates "in the exercise of the duties entrusted to them" belongs to the employer (art. 97.4 of the Intellectual Property Law).
  - A project unrelated to your job and made in your free time is yours. Using company equipment or licences blurs that separation.
  - This is not legal advice. If in doubt, ask first.
- **Your work Claude Code loads EcoVadis configuration.** If you open it in the personal repo, these are loaded too:
  - the EcoVadis MCP servers, including the production ones;
  - the on-duty skills;
  - the rtk hook.

  This is another reason to use **Antigravity with your personal Google account on both machines**, and not to open the personal repo with the work Claude Code.
- **Separate your git identity.** In the personal repo, set `git config user.email <your personal email>`, use your personal GitHub account and no company credentials.
- **No company material in the repo** (brief, section 13). Enable `gitleaks` in pre-commit from the first commit.

---

## 2. learn-harness-engineering and harness-creator

### 2.1 The course

**What it contains:**
- 14 lessons (L01–L14) and 8 projects on an Electron/TypeScript app.
- It organises the harness into **5 subsystems**: instructions, state, verification, scope and session lifecycle.
- It ends with loops (L13) and agent graphs (L14).

**How to use it:**
- **Read the lessons and apply each one to *watch-tonight*,** instead of doing the Electron projects.
- **The exception is the idea of P01:** do the same task with and without a harness and compare the results. That small experiment is gold for interviews.
- **Also read `docs/en/harness-designs/`,** which analyses how the Claude Code, Codex, Pi and DeepSeek harnesses are built. It helps you speak with authority in interviews.

| Harness level (§3.5) | Lessons |
|---|---|
| v0 | L01–L04: what a harness is, the repo as source of truth, why a giant instruction file fails |
| v1 | L05, L06, L12: continuity between sessions, the start phase, leaving a clean state |
| v2 | L07–L10: scope control, feature lists, premature victory, end-to-end verification |
| v3 | L13: loops (goal, timer, maker-checker) |
| v4 | L11: observability |
| v5 | L14: graphs (fan-out, human approval) |

### 2.2 harness-creator

**What it does.** Node scripts that use only built-in modules:

| Script | What it does |
|---|---|
| `create-harness.mjs` | Generates `AGENTS.md`, `feature_list.json`, `progress.md`, `init.sh` and `session-handoff.md` with placeholders |
| `validate-harness.mjs` | Scores the 5 subsystems |
| `run-benchmark.mjs` | Produces an HTML report |

Its own README warns that the score is **structural**: it confirms that the pieces exist, not that the harness works.

**What role it plays here:**

- **Don't use it to create your harness.** It would generate generic placeholders and a bash `init.sh`, and skip exactly what you want to learn.
- **Use it as a sensor for your harness, like a linter.** When you finish v1, and again at v3:
  1. Run `node <path>/validate-harness.mjs --target .`; on the Mac, also `bash tools/audit-harness.sh .`.
  2. Start with the lowest-scoring subsystem.
- **Read its `templates/`.** Section 5 of this document already adapts its ideas to Python and two operating systems.
- **Read it before installing it.** `npx skills add ...` runs third-party code; it is a small amount of code.

---

## 3. The proposed workflow

### 3.1 The 5 subsystems, in files

| Subsystem | Files | Sensor (what checks it) |
|---|---|---|
| Instructions | `AGENTS.md` as a map → `docs/*.md` with the detail, read on demand | A test that requires `AGENTS.md` ≤150 lines |
| State | `feature_list.json`, `PROGRESS.md`, `docs/specs/`, `docs/spikes/` | `tests/harness/test_feature_list.py`: at most 1 `in_progress` task, `done` requires `evidence`, unique ids, valid `type`/`stories` and valid dependencies |
| Verification | `uv run poe check` = ruff + pyright + import-linter + pytest (fast tests) + UI lint, types and tests once `web/` exists; pre-commit; CI | Stop hook; CI is required to merge |
| Scope | One task at a time; spec with acceptance tests; protected paths (`tests/acceptance/`, `evals/`) | CI: if the PR touches a protected path, it requires the `tests-approved` label, which you set |
| Lifecycle | Start and close protocols in `AGENTS.md`; skills `/start` and `/handoff` | CI: if the PR changes `src/` or `web/`, it must also change `PROGRESS.md` |

### 3.2 The task cycle

```
     YOU                        AGENTS (autonomous, with a budget)                       YOU
┌──────────────────────┐   ┌──────────────────────────────────────────────┐   ┌────────────────────────┐
│ 1. DEFINE (/spec)    │   │ 2. BUILD (implementer)                       │   │ 4. DEFEND (/defend)    │
│ the agent            │──▶│    code + unit tests                         │──▶│ 3 "why?" questions     │
│ interviews you →     │   │    Stop hook: can't finish if poe check fails│   │ you answer in the PR → │
│ 1-page spec +        │   │    (at most 3 retries)                       │   │ entry in LEARNING.md   │
│ acceptance tests     │   │ 3. REVIEW (reviewer subagent, read-only)     │   │ 5. MERGE: green CI     │
│ you approve:         │   │    diff vs spec → findings → the             │   │ + review according to  │
│ status: approved     │   │    implementer fixes (at most 2 rounds)      │   │ the risk tier          │
└──────────────────────┘   └──────────────────────────────────────────────┘   └────────────────────────┘
           Every session ends with /handoff (§1.3), whichever step you're in.
```

- **Self-correction lives in steps 2 and 3.** The deterministic sensors (Stop hook and CI) and the reviewer send the work back to the implementer without going through you.
  - You are **on** the loop, not **in** it: you define the goal, decide at the merge and, when something fails, improve the harness (`docs/harness-log.md`).
- **Orchestration arrives in two levels:**
  - In v3, the implementer invokes the reviewer as a subagent (`invoke_subagent` in Antigravity).
  - In v5, several independent tasks run in parallel, each in its own worktree.

### 3.3 Refinement, readiness and spikes

- **Stories → features → specs:**
  - **User stories (`docs/product.md`)** describe what the user gets and rarely change.
  - **Items in `feature_list.json`** are vertical slices built in 1–3 sessions. Each item has a `type` (`feature`, `spike` or `chore`) and `stories` (e.g. `["US1"]`, or `[]` for cross-cutting chores/spikes).
  - **Order in `feature_list.json` = priority.** You reorder it; the agent never does.
- **Definition of Ready (derived, not a new status):** an item is ready to build when all its `dependencies` are `done` and:
  - `type: "chore"` → no spec needed (docs, renames, configuration).
  - `type: "spike"` → has a `docs/spikes/NN-slug.md` file listing the explicit questions to answer.
  - `type: "feature"` → its spec (`docs/specs/NN-slug.md`) has `status: approved` and no open questions that change the design.
  - Do not add a `ready` status to `feature_list.json`: keeping status in one place avoids drift (L08). A small `uv run poe next` helper can compute and print the next ready item or explain what blocks it.
- **When a feature needs a spike instead:** if the `/spec` interview hits a question that neither you nor the docs can answer—and the answer changes the design or prevents writing acceptance tests—stop the spec and create a `spike`:
  - **Timebox:** 1–2 sessions.
  - **Code:** throwaway scripts in `spikes/`, never in `src/`.
  - **Output:** answers recorded in `docs/spikes/NN-slug.md`, plus an ADR in `docs/decisions/` if it led to an architectural choice.
  - **Unblocking:** the blocked feature adds the spike ID to its `dependencies`. Once the spike is `done`, resume `/spec` with real data.
- **When nothing is ready, refining is the task.** At session start, pick the first rule that matches:
  1. An item is `in_progress` or `todo` and **ready** → build it.
  2. The top unblocked `todo` feature has no spec or a `draft` spec → run `/spec` with the owner to refine it.
  3. `/spec` uncovers an unknown that blocks the design → create the `spike` entry and `docs/spikes/NN-slug.md`, and run it.
  4. No `todo` items remain → stop and ask the owner to slice the next features from `docs/product.md`. Never invent features.
- **Refine one ahead:** during `/handoff`, if no item after the active one is ready, note `Waiting on owner: refine feat-XXX` in `PROGRESS.md` so the next 30-minute session can approve it quickly.
- **When a spec turns out to be wrong mid-build:** if implementation proves the spec wrong, stop coding, set the spec back to `draft`, explain the gap and get owner approval before continuing. If a spec grows past 1 page or 3 sessions, split the feature.

### 3.4 Antigravity configuration

| Piece | Antigravity |
|---|---|
| Instructions | Reads `AGENTS.md` automatically (always on, no frontmatter) |
| Stop hook | `.agents/hooks.json` → `stop_gate.py`; replies `{"decision":"continue","reason":...}` so the agent keeps going |
| Skills | `.agents/skills/<name>/SKILL.md` → `/start`, `/handoff`, `/spec`, `/defend`. Use skills, not workflows: Antigravity workflows are deprecated |
| Reviewer | `.agents/agents/reviewer.md` (subagent; App and CLI) |
| Path rules | `.agents/rules/*.md` with `trigger: glob` (without valid frontmatter they are silently ignored) |

**To verify in v0:**
- **The Stop hook,** with two doubts:
  - that it really fires on the surface you use (App, IDE or CLI); a forum thread reports plugin hooks that don't run in the IDE;
  - which directory it runs from.
- **The exact tool names** for the reviewer's `tools:` field.
- **Subagents in the IDE:** the documentation only mentions the App and the CLI.

### 3.5 The harness grows in levels

| Level | Week | What you add | Exit criterion |
|---|---|---|---|
| **v0** | 0 | `AGENTS.md`, `docs/product.md`, `PROGRESS.md`, `feature_list.json`, `pyproject.toml` with `poe check`, pre-commit (ruff, gitleaks) and CI running `poe check` | Green CI on an empty skeleton. A task started on the Mac and finished on the other machine without having to explain anything to the agent |
| **v1** | 1 | Stop hook (`stop_gate.py`), skills `/start` and `/handoff`, `feature_list.json` test, `PROGRESS.md` check in CI | The agent can't finish with failing checks. First score with harness-creator |
| **v2** | 2–3 | `/spec`, spec template, protected paths, acceptance tests first | One task done end to end with an approved spec |
| **v3** | 4 | Reviewer subagent (maker-checker); goal loop or Ralph loop for the enrichment batch; turn and cost budgets | One unattended run, with its post-mortem in `harness-log.md` |
| **v4** | 5–6 | `/defend`, `LEARNING.md` and a CI check for the "Defend it" section; cost and time traces of the agents | All PRs with the questions answered |
| **v5** | 7–9 | Per-PR review guide, risk tiers, review metrics, parallel subagents | Review minutes per PR measured |

**Don't move up a level until the current one has failed you at least once and you've fixed it.** That's how you learn harness engineering: each piece answers a real failure, not a list of best practices.

### 3.6 The harness log

`docs/harness-log.md` gets one entry per failure:

```markdown
## 2026-11-14 · Mac · Antigravity
- Failure: agent marked feat-003 done without running the integration tests.
- Root cause: AGENTS.md said "run tests" but not which ones, and nothing checked it.
- Harness change: "done" now requires `evidence` with the exact command (enforced by test_feature_list.py).
- Lesson: L09 (premature victory).
```

In six weeks, this file will be your best interview material.

---

## 4. What changes in the brief

- **Q1 (harness design):** the one in this document is proposed.
- **Q2 (main tool):** decided: Antigravity with a personal account on both machines.
- **`make check` becomes `uv run poe check`,** because of Windows.
- **The "lightweight workflow" of brief section 8** is replaced by section 3 of this document.

---

## 5. Starter templates (in English, because the repo is public)

They are starting points: read them, understand them and trim them. **If you can't explain a line, delete it.**

### 5.1 `AGENTS.md`

```markdown
# watch-tonight: agent guide

Movie recommender: free-text mood + country + streaming services → 5 movies streamable now, each with a grounded reason.
Python 3.13 · FastAPI · MongoDB Atlas Vector Search · Gemini · web UI (React or another common frontend framework) in web/.

The owner is learning Python and agentic engineering through this project.
Explain non-obvious Python and framework choices with a C# comparison. Prefer small, reviewable steps.

## Map (read on demand, not all at once)
- PROGRESS.md: current state and next step. Read first.
- feature_list.json: all features and their status. Source of truth for scope.
- docs/product.md: problem, users, scope, out of scope
- docs/architecture.md: components, data model, layers (domain → application → infra/api)
- docs/conventions.md: code style, testing, naming
- docs/specs/: one spec per non-trivial feature
- docs/spikes/: timeboxed investigations answering design unknowns
- docs/decisions/: why things are the way they are (ADRs)
- docs/harness-log.md: past agent failures and how the harness changed
- LEARNING.md: what the owner has learned

## Session start protocol
1. `git pull`, then `uv sync` and `uv run poe check`. If the check fails, fixing it is the task.
2. Read the "Now" section of PROGRESS.md, then the active feature in feature_list.json and its spec/spike doc.
3. Pick the session task (first rule that matches):
   a. An item is `in_progress` or `todo` and **ready** (see Definition of Ready) → build it.
   b. The top unblocked `todo` feature has no spec or a `draft` spec → run `/spec` with the owner.
   c. `/spec` uncovers an unknown that changes the design → create a `spike` entry and `docs/spikes/NN-slug.md`, and run it.
   d. No `todo` items remain → stop and ask the owner to slice the next features from `docs/product.md`. Never invent features.
4. State in 3 lines what you will do in this session. Wait for "go" unless the item is ready and the next step is clear.

## Working rules
- One feature at a time, in `feature_list.json` order (only the owner reorders it).
- **Definition of Ready** (derived, never a status in `feature_list.json`): all `dependencies` are `done`, and:
  - `type: "chore"` → no spec needed;
  - `type: "spike"` → explicit questions listed in `docs/spikes/NN-slug.md` (throwaway code in `spikes/`, never `src/`, 1–2 sessions max);
  - `type: "feature"` → spec in `docs/specs/NN-slug.md` has `status: approved` and no open design-changing questions.
- If implementation proves an approved spec wrong, stop coding, set the spec back to `draft`, explain the gap and get owner approval. If a spec exceeds 1 page or 3 sessions, split the feature.
- Never edit tests/acceptance/ or evals/ unless the owner asks for it in this session.
- Never push to main, never commit secrets, never add a dependency without explaining why.
- Done = acceptance tests pass (or spike questions answered in `docs/spikes/`) + `uv run poe check` passes + evidence recorded. Paste commands and outputs; don't just claim.
- Stay in scope. Record ideas outside the feature as new "todo" entries in feature_list.json instead of doing them.

## Session end protocol (always, even mid-task)
1. Rewrite the "Now" section of PROGRESS.md. If no item after the active one is ready, add `Waiting on owner: refine feat-XXX` (refine one ahead). Add 1–3 lines to the top of "Log" (date · machine · tool).
2. Update the feature's status and evidence in feature_list.json.
3. Ask: "What do I know now that the next session needs and is not in the repo?" Save it where it belongs (ADR, conventions, spec, PROGRESS.md).
4. Commit (WIP is fine on a feature branch) and push. Report what is still unverified.

## Commands
- `uv run poe check`: lint, types, architecture rules and fast tests (backend and, once it exists, web/). Must pass before stopping.
- `uv run poe test-all`: also runs the integration tests (needs Docker).
- `uv run poe fmt`: format.
```

### 5.2 `PROGRESS.md`

```markdown
# Progress

## Now
- **Active feature:** feat-004 Ingest 500 movies from TMDB (branch `feat/004-ingest`)
- **State:** fetching works; idempotent upsert not done yet.
- **Last check:** `uv run poe check` green, 2026-11-14 21:10 (unit tests only; integration tests not run on this machine)
- **Next step:** make the upsert idempotent using `source_hash` (spec, section 3).
- **Waiting on owner:** decide whether to store review snippets (TMDB terms, see docs/spike.md).
- **Unverified:** behaviour with BO provider data.

## Log (newest first, 1–3 lines each)
- 2026-11-14 · Windows · Antigravity · feat-004: TMDB client with retries (tenacity); 12 unit tests.
- 2026-11-13 · Mac · Antigravity · feat-004: spec approved; acceptance test written by the owner.
```

### 5.3 `feature_list.json` (the first version is the spike checklist)

```json
{
  "features": [
    {
      "id": "feat-001",
      "type": "chore",
      "name": "Repo skeleton and harness v0",
      "stories": [],
      "status": "in_progress",
      "dependencies": [],
      "spec": null,
      "evidence": ""
    },
    {
      "id": "feat-002",
      "type": "spike",
      "name": "Spike: TMDB terms, rate limits and watch-provider coverage for ES, US and BO",
      "stories": ["US1"],
      "status": "todo",
      "dependencies": ["feat-001"],
      "spec": "docs/spikes/02-tmdb-and-providers.md",
      "evidence": ""
    },
    {
      "id": "feat-003",
      "type": "spike",
      "name": "Spike: Atlas free tier, vector-search pre-filters and the atlas-local image",
      "stories": ["US1", "US2"],
      "status": "todo",
      "dependencies": ["feat-001"],
      "spec": "docs/spikes/03-atlas-vector-search.md",
      "evidence": ""
    }
  ]
}
```

- **Possible types:** `feature` (needs an approved spec in `docs/specs/`) · `spike` (needs questions in `docs/spikes/`) · `chore` (no spec).
- **Possible statuses:** `todo` · `in_progress` · `blocked` · `done` (readiness is derived, never a status).

### 5.4 Spec and spike templates

**Feature spec:** `docs/specs/NN-slug.md`

```markdown
---
id: feat-004
stories: [US1]
status: draft   # draft → approved (set by the owner only)
---
# Ingest movies from TMDB

## Goal
One or two sentences.

## Acceptance tests (written or approved by the owner)
- [ ] Given …, when …, then … → tests/acceptance/test_ingest.py::test_rerun_changes_nothing

## Out of scope
-

## Design notes (the agent proposes, the owner decides)
-

## Open questions (at most 5, each with a recommendation; must be empty before status: approved)
1.
```

**Spike:** `docs/spikes/NN-slug.md`

```markdown
---
id: feat-002
unblocks: [feat-004]
timebox: 1–2 sessions
status: todo   # todo → done
---
# Spike: TMDB terms, rate limits and watch-provider coverage

## Questions to answer
1. Does `watch/providers` return flat-rate data for ES, US and BO?
2. What do the TMDB and JustWatch terms allow us to cache and store?

## Findings (with evidence / commands / links)
-

## Impact on specs and ADRs
-
```

### 5.5 Stop hook

**Antigravity:** `.agents/hooks.json`

```json
{
  "check-gate": {
    "Stop": [
      { "type": "command", "command": "uv run python scripts/hooks/stop_gate.py", "timeout": 300 }
    ]
  }
}
```

**The script:** `scripts/hooks/stop_gate.py`

```python
"""Stop hook: the agent may stop only when `poe check` passes.

It runs only when src/, web/ or tests/ differ from origin/main, so Q&A sessions are not blocked.
After MAX_ATTEMPTS failures it lets the agent stop, so a stuck agent hands control back to the owner.
"""
import json
import subprocess
import sys
from pathlib import Path

MAX_ATTEMPTS = 3
COUNTER = Path(".harness/stop_gate_attempts")  # add .harness/ to .gitignore
WATCHED = ("src", "web", "tests")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def has_code_changes() -> bool:
    committed_or_modified = git("diff", "--name-only", "origin/main", "--", *WATCHED)
    untracked_or_unstaged = git("status", "--porcelain", "--", *WATCHED)
    return bool(committed_or_modified.strip() or untracked_or_unstaged.strip())


def respond(allow: bool, reason: str = "") -> None:
    if allow:
        print(json.dumps({"decision": "allow"}))
    else:
        print(json.dumps({"decision": "continue", "reason": reason}))


def main() -> None:
    json.load(sys.stdin)  # hook payload; not used yet

    if not has_code_changes():
        respond(allow=True)
        return

    result = subprocess.run(["uv", "run", "poe", "check"], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        COUNTER.unlink(missing_ok=True)
        respond(allow=True)
        return

    attempts = int(COUNTER.read_text()) + 1 if COUNTER.exists() else 1
    if attempts > MAX_ATTEMPTS:
        COUNTER.unlink(missing_ok=True)
        respond(allow=True)  # give up; the next session's start protocol will see the failing check
        return
    COUNTER.parent.mkdir(exist_ok=True)
    COUNTER.write_text(str(attempts))

    tail = (result.stdout + result.stderr)[-3000:]
    respond(allow=False,
            reason=f"`uv run poe check` failed (attempt {attempts}/{MAX_ATTEMPTS}). Fix it before stopping.\n{tail}")


if __name__ == "__main__":
    main()
```

It's a good first Python exercise. Compare it with C#:
- `subprocess.run` plays the role of `Process.Start`.
- `pathlib.Path` plays the role of `FileInfo`.

### 5.6 Antigravity skills (sketches)

`.agents/skills/start/SKILL.md`

```markdown
---
name: start
description: Start-of-session routine. Use when the owner opens a session, switches machines, or types /start.
---
Follow "Session start protocol" in AGENTS.md. Then report in at most 8 lines:
the check result, the active feature, the next step, and any questions that block you.
```

`.agents/skills/handoff/SKILL.md`

```markdown
---
name: handoff
description: End-of-session handoff. Use when the owner says they are stopping or switching machines, or types /handoff.
---
Follow "Session end protocol" in AGENTS.md exactly. Then show the owner:
the new "Now" section of PROGRESS.md, anything you saved elsewhere and why,
the pushed commit hash, and what is still unverified.
```

`.agents/skills/spec/SKILL.md`

```markdown
---
name: spec
description: Write or refine the spec of a non-trivial feature by interviewing the owner. Use before implementing a feature that has no approved spec, or when the owner types /spec.
---
Interview the owner to fill docs/specs/NN-slug.md from the template.
Ask only questions that change the design, at most 5 at a time, each with your recommendation.
If a question cannot be answered without experimentation and changes the design or acceptance tests,
propose a timeboxed `spike` in `feature_list.json` and `docs/spikes/NN-slug.md` that the feature depends on.
Propose the acceptance tests as Given/When/Then; the owner writes or approves them.
Never set `status: approved` yourself.
```

`.agents/skills/defend/SKILL.md`

```markdown
---
name: defend
description: Learning tutor. Use before merging a branch, or when the owner types /defend.
---
Read `git diff origin/main...HEAD`. Ask the owner 3 "why" questions about decisions in it
(Python idioms, framework choices, trade-offs), one at a time. Don't give the answer first.
After each answer, correct or deepen it with a C# comparison.
Then append an entry to LEARNING.md (concepts, C# equivalent, why, alternatives, pitfalls, links)
and add the questions and answers to the PR description under "Defend it".
```

### 5.7 Reviewer subagent: `.agents/agents/reviewer.md`

```markdown
---
name: reviewer
description: Read-only code reviewer. Use after the implementer finishes a feature and `uv run poe check` passes, to compare the branch diff with the feature's spec.
tools: [view_file, run_command]   # verify exact tool names; give it no file-editing tools
model: inherit
mainAgent: false
---
You review; you never edit files or fix code.
1. Read the active feature's spec (see PROGRESS.md) and `git diff origin/main...HEAD`.
2. Report only: unmet acceptance criteria, correctness bugs, missing tests for specified behaviour,
   layer violations and scope creep. Not style: ruff and pyright already cover it.
3. For each finding give: file:line, what is wrong, the evidence, and a suggested fix.
   If there is nothing material, answer "No findings".
```

---

## 6. Next steps

1. **(1–2 h) Read L01–L04 of the course.**
2. **(2–3 sessions) Build harness v0 on the Mac with Antigravity.**
   - Create the public repo, with gitleaks from the first commit.
   - Write `docs/product.md` from the brief.
   - Use templates 5.1–5.3.
   - Ask the agent to explain every line of `pyproject.toml`.
3. **(15 min, in a separate session) Install Antigravity on the work laptop,** after resolving the points in §1.6.
4. **(1 session) Test the handoff:** start `feat-001` on one machine and finish it on the other. Note in `harness-log.md` what was missing.
5. **(1 session) Build v1:** the Stop hook, `/start` and `/handoff`.
   - Break a test on purpose and check that the agent can't finish.
   - Then run the harness-creator validator.
6. **Then do the week 1 spike of the brief:** each checklist item is an entry in `feature_list.json`.

**About uncertainty:** you don't need to decide everything now. Questions Q3–Q11 of the brief get decided during the spike, with data.
