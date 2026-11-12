---
name: spec
description: >-
  Write or refine the 1-page spec and acceptance tests for a feature by
  interviewing the owner, or spawn a spike when an unknown blocks design. Use
  before implementing a feature without an approved spec, or when the owner
  types /spec.
---

# Feature Specification & Refinement (`/spec`)

1. Read [docs/product.md](../../../docs/product.md), [feature_list.json](../../../feature_list.json), and any existing draft in `docs/specs/`.
2. Interview the owner to complete `docs/specs/NN-slug.md` (maximum 1 page):
   - Ask **only questions that change the design or acceptance criteria**, at most **5 questions at a time**, each with your **recommended option**.
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
