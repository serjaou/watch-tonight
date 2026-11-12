---
name: defend
description: >-
  Optional Socratic "Defend it" session and LEARNING.md updater. Use only when
  the owner types /defend, optionally with a feature id, a commit or a commit
  range to discuss.
---

# "Defend It" learning session (`/defend [target]`)

Optional: the owner runs it when they want to check they can defend a set of changes. It is not a workflow step (ADR 0004).

1. Work out which changes to discuss from the target:
   - **none:** the current branch: `git diff origin/main`, plus new files from `git status --short`;
   - **a feature id** (`feat-007`): its commits, found with `git log --all --grep=feat-007`. If none mention it, ask the owner for the commit or range;
   - **a commit or range** (`a1b2c3`, `main~3..main`): `git show <commit>` or `git diff <range>`.
2. Read [LEARNING.md](../../../LEARNING.md), then formulate **3 Socratic "why" questions** about concrete decisions in those changes (Python idioms, type annotations, library choices, architectural trade-offs, or edge cases).
3. **Ask one question at a time** and wait for the owner's answer before the next. Never give the answer first.
4. After the owner answers:
   - Validate or deepen each answer with a **C# / .NET comparison** and point out any subtle Python pitfalls.
   - Update [LEARNING.md](../../../LEARNING.md):
     - Add/promote the covered concepts in the **Concept Map** (`Practised` → `Can explain`).
     - Prepend a new entry in the **Learning Log** (`YYYY-MM-DD · <target> <name>`) summarizing the concepts, C# comparison, pitfalls, and the 3 questions defended.
