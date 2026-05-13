# ai-skills

Claude Code skills for e-commerce engineering workflows.

> General-purpose skills live in [jouzen/ai-skills](https://github.com/jouzen/ai-skills).

## What are skills?

Skills are reusable prompt files that extend Claude Code with specialized behaviors. Drop a skill folder into `~/.claude/skills/` and Claude Code picks it up automatically.

## Skills

### E-commerce

| Skill | Description |
|-------|-------------|
| *(coming soon)* | Add e-commerce specific skills here |

Skills go in [`ecomm/`](./ecomm/).

## Usage

```bash
git clone https://github.com/Sjohnson-OR/ai-skills.git
cp -r ai-skills/ecomm/<skill-name> ~/.claude/skills/
```

Then invoke in Claude Code:

```
/<skill-name>
```
