# Checkpoint · 16 November 2026

A pause after the first six days of `watch-tonight`, to catch up on everything we did, learn from it, and check that it's reliable.

**Status:** frozen snapshot, written on 2026-11-16 by Claude Code (Opus 5.5) on the Windows laptop. These documents won't be updated. Current state always lives in [PROGRESS.md](../../PROGRESS.md), [docs/architecture.md](../architecture.md) and the decision records.

---

## What's inside

There are two documents:

1. **A learning guide** in eight parts. It goes from the big picture down to real code, in plain English. Read one part per sitting.
2. **[A review](review.md)** of the work so far. It answers two questions: can we trust the work done on the Mac with Antigravity, and which learning did we skip? It also gives feedback and advice.

## The learning guide

| Part | What you'll learn | Time |
|---|---|---|
| [1 · The big picture](01-big-picture.md) | Why the project exists, what it does, the three stages of the first six days, where we are | 10 min |
| [2 · How we work: the harness](02-the-harness.md) | What a harness is, the task cycle, three strengths of gate, what failed and what we learned | 20 min |
| [3 · The architecture](03-the-architecture.md) | Offline vs online, one search followed through its 7 steps, layers and ports, the 8 decisions in one line each | 20 min |
| [4 · Spikes on the foundations](04-spikes-foundations.md) | How to read a spike critically; the TMDB, Atlas and embedding spikes, and what an independent check found in each | 25 min |
| [5 · The LLM spike](05-spike-llm.md) | Choosing the LLM: cost, reliability, terms of service, retries with feedback, Pydantic AI | 15 min |
| [6 · The recommendation-quality spike](06-spike-recommendation-quality.md) | The quality gate, outside data, the profile and "mirror schema", the ranking formula, measuring the judge | 25 min |
| [7 · Inside the code](07-inside-the-code.md) | Six worked code examples with C# comparisons: the Stop hook, the Bayesian score, closed vocabularies, validator + retry, filtered vector search, the hybrid score | 30 min |
| [8 · Concepts and questions](08-concepts-and-questions.md) | A glossary of the AI-engineering concepts, and 27 questions to test yourself or start a `/defend` session | reference |

**Suggested plan:** parts 1–3 on day one (the context), parts 4–6 over the next two days (the spikes, the most important part), part 7 with the code files open, and part 8 whenever you want to test yourself.

**Each part starts with a "Key ideas" box and ends with "Questions to think about".** If you only have five minutes, read the boxes.

## How to take notes and challenge things

- Write your questions and disagreements anywhere you like. A simple option: a file `docs/checkpoint-2026-11-16/notes.md` that you keep for yourself.
- To discuss a point with the agent, quote the part and section, for example: *"In Part 6, section 6, why does the formula use min-max?"*
- To turn a topic into a learning record, use `/tutor <topic>` (explains it with a C# comparison) or `/defend <task id>` (asks you three "why" questions). See [Part 8](08-concepts-and-questions.md#how-to-turn-these-into-learning-records).

## Why Markdown and not an HTML page

All the other project documents are Markdown, so these files work the same way: GitHub shows them with diagrams and tables on both machines and on a phone, you can annotate them in the repo, and an agent can read them when you ask questions about them.
