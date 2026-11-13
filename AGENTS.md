# watch-tonight: agent guide
Movie recommender: free-text mood + country + streaming services → 5 movies streamable now, each with a grounded pitch about the movie (never about the user; see `docs/product.md` P2).
Python 3.13 · FastAPI · MongoDB Atlas Vector Search · Gemini · web UI (React or another common frontend framework) in web/.

The owner is learning Python and agentic engineering through this project.
Explain non-obvious Python and framework choices with a C# comparison. Prefer small, reviewable steps.
The owner uses Antigravity on a Mac and Claude Code on a Windows laptop. Everything here applies to both tools (ADR 0003).

## Map (read on demand, not all at once)
- PROGRESS.md: current state and next step. Read first.
- feature_list.json: all features and their status. Source of truth for scope.
- docs/product.md: problem, users, scope, out of scope, product rules P1–P7
- docs/conventions.md: commands, code and test conventions, what the harness tests check
- docs/architecture.md: components, layers and ports, query flow, data model, open questions (v0 draft until feat-011)
- docs/specs/: one spec per non-trivial feature
- docs/spikes/: timeboxed investigations answering design unknowns (questions first, answers with evidence)
- docs/decisions/: why things are the way they are (ADRs)
- docs/harness-log.md: past agent failures and how the harness changed
- docs/workflow.md: the owner's guide to the workflow (human-facing; the rules are here)
- .agents/: skills, reviewer subagent and Stop hook. Source of truth for both tools; `.claude/` only points here
- LEARNING.md: what the owner has learned
- docs/inception/: historical brief and harness proposal. Superseded; don't act on it

## Session start protocol
1. `git pull`, then `uv sync` and `uv run poe check`. If the check or the latest CI run of the branch fails, fixing it is the task. If a tool is missing, point the owner to "Machine setup" in README.md; don't install it yourself.
2. Read the "Now" section of PROGRESS.md, then the active feature in feature_list.json and its spec/spike doc.
3. Pick the session task (first rule that matches):
   a. An item is `in_progress` or `todo` and **ready** (see Definition of Ready) → build it.
   b. The top unblocked `todo` feature has no spec or a `draft` spec → run `/spec` with the owner.
   c. `/spec` uncovers an unknown that changes the design → create a `spike` entry and `docs/spikes/NN-slug.md`, and run it.
   d. No `todo` items remain → stop and ask the owner to slice the next features from `docs/product.md`. Never invent features.
4. Report in at most 8 lines: branch, check and CI result, the item and whether it is ready, a 3-line plan, blocking questions. If the item is ready and the next step is clear, continue; otherwise wait for "go".

## Workflow (ADR 0004)
- Run a ready task end to end without asking: build → `uv run poe check` → `/review` → fix findings (at most 2 rounds) → `/handoff` → PR → report and stop. Start the next task only after the owner merges.
- Stop and ask the owner when a human decision is needed: the spec looks wrong, an unknown changes the design, the check is still red after 3 attempts, or a review finding changes the scope.
- If the owner says "step by step" (for a task or the session), stop after each phase and wait.
- `/defend` and `/tutor` run only when the owner asks; they are not workflow steps.

## Working rules
- One feature at a time, in `feature_list.json` order (only the owner reorders it).
- **Definition of Ready** (derived, never a status in `feature_list.json`): all `dependencies` are `done`, and:
  - `type: "chore"` → no spec needed;
  - `type: "spike"` → explicit questions listed in `docs/spikes/NN-slug.md` (throwaway code in `spikes/`, never `src/`, 1–2 sessions max);
  - `type: "feature"` → spec in `docs/specs/NN-slug.md` has `status: approved` and no open design-changing questions.
- If implementation proves an approved spec wrong, stop coding, set the spec back to `draft`, explain the gap and get owner approval. If a spec exceeds 1 page or 3 sessions, split the feature.
- Never edit tests/acceptance/ or evals/ unless the owner asks for it in this session. CI fails a PR that touches them until the owner adds the `tests-approved` label; never add it yourself.
- Never commit to or push `main`, never commit secrets, never add a dependency without explaining why.
- Done = acceptance tests pass (or spike questions answered in `docs/spikes/`) + `uv run poe check` passes + evidence recorded. Paste commands and outputs; don't just claim.
- Stay in scope. Record ideas outside the feature as new "todo" entries in feature_list.json instead of doing them.

## Session end protocol (`/handoff`: at the end of every task, and when the owner ends the session, even mid-task)
1. Rewrite the "Now" section of PROGRESS.md. If no item after the active one is ready, add `Waiting on owner: refine feat-XXX` (refine one ahead). Add 1–3 lines to the top of "Log" (date · machine · tool).
2. Update the feature's status and evidence in feature_list.json.
3. Ask: "What do I know now that the next session needs and is not in the repo?" Save it where it belongs (ADR, conventions, spec, PROGRESS.md, harness-log).
4. Commit (WIP is fine) and push the feature branch. When the task is complete, open a PR to `main`. Report what is still unverified.

## Commands
- `uv run poe check`: lint, format check, types, architecture rules and fast tests (backend and, once it exists, web/). Must pass before stopping.
- `uv run poe test-all`: also runs the integration tests (needs Docker).
- `uv run poe fmt`: format. More commands (one test, single steps) in docs/conventions.md.
