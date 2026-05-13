# gspec: Minimal spec-driven development

- Human edits spec.md (top level and/or per subdirectory)
- LLM edits spec-interpreted.md to match spec.md
- LLM edits code to match spec-interpreted.md

When the human disagrees with the LLM, they primarily edit spec.md if the disagreement is on a high level. 
If the disagreement is on an implementation level, not worth putting in the official spec, the human edits spec-interpreted.md. 

