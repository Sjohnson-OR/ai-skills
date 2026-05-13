---
name: brainstorming
description: >
  Turn feature ideas into technical designs before implementation.
  Use when the user wants to build something new, add functionality,
  or make significant changes — before writing any code.
---

# Brainstorming

Turn ideas into designs through collaborative dialogue before writing code.

Start by understanding the project context, then ask questions to refine the
idea. Once the design is clear, present it and get user approval before moving
to implementation.

## Process

### 1. Explore project context

Before asking any questions, get oriented:

- Check relevant source files, docs, and recent commits.
- Identify existing patterns and conventions in the codebase.
- Note constraints (language, framework, deployment model) that will shape the design.

### 2. Ask clarifying questions

Understand the idea well enough to propose concrete approaches.

- Ask **one question per message** — don't overwhelm.
- Prefer **multiple choice** when the options are known; open-ended is fine when they aren't.
- Focus on: purpose, constraints, success criteria, and scope.
- Keep going until you could explain the feature to another engineer.

### 3. Propose approaches

Present 2–3 realistic options with trade-offs.

- Lead with your **recommended** option and explain why.
- Be honest about downsides — the user will trust you more.
- Apply YAGNI: if an option adds complexity for a hypothetical future need, say so.

### 4. Present the design

Once the user picks a direction, flesh it out into a design.

- Scale each section to its complexity — a sentence for simple parts, a few
  paragraphs for nuanced ones.
- Cover what's relevant: architecture, components, data flow, error handling,
  testing approach.
- Present incrementally and check in — "Does this look right so far?"
- Be ready to revisit earlier decisions if something doesn't fit.

### 5. Hand off

After the user approves the design:

- Ask if they'd like the design saved to a file (e.g. `docs/plans/<topic>.md`).
- If the user wants to move to implementation, use the `writing-plans` skill to
  create a step-by-step implementation plan from the approved design.
- Or stop here if the user just wanted a design.

## Guidelines

- **No code before approval.** Don't write implementation code until the design
  is accepted. Exploring the codebase to inform the design is fine.
- **Stay practical.** Propose things that work in the current codebase, not
  ideal-world rewrites.
- **Cut scope aggressively.** A smaller, well-understood design beats a
  sprawling one. Features can always be added later.
- **Adapt to the situation.** Simple changes need a short conversation. Complex
  systems need more. Use your judgment on how much process is appropriate.

---

*Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT License, Copyright 2025 Jesse Vincent). Modified to fit this repository's style and conventions.*
