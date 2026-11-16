---
name: spec
description: >-
  Write or refine the spec (about 1 page) and acceptance tests for a feature by
  interviewing the owner, or spawn a spike when an unknown blocks design. Use
  before implementing a feature without an approved spec, or when the owner
  types /spec.
---

# Feature Specification & Refinement (`/spec`)

1. Read [docs/product.md](../../../docs/product.md), [feature_list.json](../../../feature_list.json), and any existing draft in `docs/specs/`.
   - **Slicing rules (owner, 2026-11-16, feat-012):**
     - Every item is a **vertical slice**: a user, the API or a test can observe it working end to end. It is never one layer on its own.
     - The first slice of a new area is the **thinnest path that runs end to end**; later slices deepen it.
     - **Relevance and priority over counts** (owner, 2026-11-16):
       - Write the acceptance tests that matter most for the slice, ordered by priority: the riskiest and most product-critical behaviours (P1–P7) first.
       - Size guides, not caps: about 1 page, up to about 10 acceptance tests, a few sessions.
       - Propose a split into new items (in the **Proposed** section of `docs/backlog.md`, for the owner to approve) when the feature holds behaviours that could ship separately.
       - If the feature came from `docs/backlog.md`, copy its **Notes** into the spec's design notes or open questions.
       - Never drop relevant detail or a relevant test just to meet a number.
2. Interview the owner to complete `docs/specs/NN-slug.md` (about 1 page):
   - Ask **only questions whose answer changes the design or the acceptance tests**, most important first, each with your **recommended option**. Ask as many rounds as the feature needs; when a sensible default exists, state it instead of asking.
   - If a question cannot be answered without experimentation (e.g. third-party API behavior, DB index limits) and changes the design, stop and create a timeboxed `spike` entry in `feature_list.json` + `docs/spikes/NN-slug.md` that the feature depends on.
3. Draft the spec using this structure:
   ```markdown
   ---
   id: feat-XXX
   stories: [US1]
   status: draft   # draft -> approved (set by the owner only)
   ---
   # <Feature Title>

   ## Goal
   One or two sentences.

   ## Acceptance tests (written or approved by the owner)
   - [ ] Given ..., when ..., then ... -> tests/acceptance/test_<slug>.py::test_<name>

   ## Out of scope
   - ...

   ## Design notes (with C# comparison where helpful)
   - ...

   ## Open questions (must be empty before status: approved)
   - None
   ```
4. **Never set `status: approved` yourself.** Present the draft spec (and proposed acceptance test) to the owner and ask for their approval.
