---
name: gspec
description: Spec driven development
---

# gspec

## tl;dr;

- Human edits spec.md
- LLM edits spec-interpreted.md to match spec.md
- LLM edits code to match spec-interpreted.md

## Structure

In every non-trivial folder in the project, there should be a:
- spec.md
- spec-interpreted.md

### spec.md

This is human written. Never modify this. 
This is the high level specification of the requirements for code in this folder

### spec-interpreted.md

This is written and updated by you. Update this to match spec.md. 
This is allowed to be more verbose than spec.md, and contain more detailed design decisions. 
It is not allowed to contradict spec.md. 

## Workflow

1. In the relevant folder, read spec.md and spec-interpreted.md and update spec-interpreted.md if they are not in sync. 
2. Read spec-interpreted.md and update the code in the folder to match the spec. 

## What to work on?

The user might pass a description of what to work on. 
If not, check uncommitted changes to spec.md files. If no uncommitted changes, check the last committed changes to spec.md files, and run the workflow to keep them in sync


