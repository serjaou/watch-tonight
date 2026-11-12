---
name: defend
description: >-
  End-of-task Socratic "Defend it" gate and LEARNING.md updater. Use after
  implementation and review pass and before closing/merging a feature, or when
  the owner types /defend.
---

# "Defend It" Learning Gate (`/defend`)

Goal: ensure the owner can defend every design and Python choice in the task's diff before the task is marked `done`.

1. Inspect the task's changes (`git diff origin/main`, plus new files from `git status --short`) and read [LEARNING.md](../../../LEARNING.md).
2. Formulate **3 Socratic "why" questions** about concrete decisions in the diff (Python idioms, type annotations, library choices, architectural trade-offs, or edge cases).
3. **Ask one question at a time** and wait for the owner's answer before the next. Never give the answer first.
4. After the owner answers:
   - Validate or deepen each answer with a **C# / .NET comparison** and point out any subtle Python pitfalls.
   - Update [LEARNING.md](../../../LEARNING.md):
     - Add/promote the covered concepts in the **Concept Map** (`Practised` → `Can explain`).
     - Prepend a new entry in the **Learning Log** (`YYYY-MM-DD · <feat-id> <name>`) summarizing the concepts, C# comparison, pitfalls, and the 3 questions defended.
