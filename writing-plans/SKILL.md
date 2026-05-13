---
name: writing-plans
description: >
  Create step-by-step implementation plans from specs or designs.
  Use when you have requirements for a multi-step task and need a concrete
  plan before writing code.
---

# Writing Plans

Turn a spec or design into a concrete implementation plan with bite-sized tasks.

Write the plan assuming the implementer has zero context for the codebase.
Document everything they need: which files to touch, complete code, how to
verify each step. Assume they are a skilled developer but unfamiliar with the
project's toolset and domain.

Save plans to `docs/plans/YYYY-MM-DD-<feature-name>.md`.

## Plan structure

Every plan starts with a header:

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about the approach]

**Tech stack:** [Key technologies and libraries]

---
```

Then a sequence of tasks, each small enough to complete in 2-5 minutes.

## Task format

````markdown
### Task N: [Short description]

**Files:**
- Create: `exact/path/to/new-file.ts`
- Modify: `exact/path/to/existing-file.ts`
- Test: `tests/exact/path/to/test-file.ts`

**Steps:**

1. [Concrete action with complete code]

```typescript
// Complete, copy-pasteable code — not "add validation here"
export function parseConfig(raw: string): Config {
  const parsed = JSON.parse(raw);
  if (!parsed.version) throw new Error('missing version');
  return parsed as Config;
}
```

2. [Verification step]

Run: `npm test -- --grep "parseConfig"`
Expected: all tests pass

3. Commit

```bash
git add src/config.ts tests/config.test.ts
git commit -m "feat: add config parser"
```
````

## Principles

- **One action per step.** "Write the function" and "write the test" are
  separate steps, not one step.
- **Exact file paths.** Always specify the full path. If modifying an existing
  file, include relevant line ranges when helpful.
- **Complete code.** Write the actual code in the plan, not descriptions of
  what to write. The implementer should be able to copy-paste.
- **Verification after each task.** Include a command to run and what the
  expected output looks like.
- **Frequent commits.** Each task ends with a commit step.
- **DRY.** If the same pattern repeats, extract it into a shared utility and
  reference it in later tasks.
- **YAGNI.** Only plan what's needed now. Don't add abstractions for
  hypothetical future requirements.
- **Encourage testing.** Include test steps where appropriate. Not every task
  needs a test (config changes, docs), but implementation tasks should have
  verification.

## Guidelines

- Read the codebase before writing the plan. Understand existing patterns,
  conventions, and project structure so the plan fits naturally.
- Order tasks so each one builds on the last. Early tasks should set up
  foundations that later tasks depend on.
- Keep the plan self-contained. The implementer should not need to search for
  additional context beyond what's in the document.
- If a task is complex enough to need more than 5 steps, split it into
  multiple tasks.

---

*Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT License, Copyright 2025 Jesse Vincent). Modified to fit this repository's style and conventions.*
