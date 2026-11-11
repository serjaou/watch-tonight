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
