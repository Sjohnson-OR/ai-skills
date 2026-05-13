# Code Review Patterns Skill

Run a comprehensive, pattern-driven code review across your entire repository using parallel AI subagents.

## How it works

1. **You define review patterns** — markdown files placed in `review-patterns/` folders anywhere in your repository. Each file describes one review concern (e.g. security, reliability, naming conventions).

2. **The skill discovers all patterns** — it globs for `**/review-patterns/*.md` and infers the review scope from the pattern's location. A pattern at `infra/review-patterns/security.md` will only review code under `infra/`.

3. **One subagent per pattern runs in parallel** — each subagent reads the pattern file and explores the relevant sub-tree independently. Up to 10 subagents run concurrently.

4. **Results are consolidated** — findings from all subagents are merged into a single report, deduplicated by file and line, and grouped by area and severity.

## Usage

```
/code-review
```

The skill produces a report with:

- A **status table** — each pattern with PASS / WARN / FAIL and finding counts
- **Critical findings** — security risks or data-loss issues surfaced to the top
- **All findings by area** — warnings and info items grouped by directory
- A **summary** — 2–3 sentences on overall codebase health

## Adding review patterns to your project

Create a `review-patterns/` directory anywhere in your repository and add one markdown file per concern. The file should describe:

- **What to check** — the specific properties, patterns, or anti-patterns to look for
- **How to review** — concrete steps for the subagent (which files to glob, what to grep for, etc.)

See [`samples/`](samples/) for examples:

- [`samples/security.md`](samples/security.md) — infrastructure secrets, network security, IAM, S3 and RDS hardening
- [`samples/reliability.md`](samples/reliability.md) — health checks, auto-scaling, high availability, backups, deployment safety

### Pattern file structure

```markdown
# Review Pattern: <Name>

## What to Check

### <Category>
- Bullet points describing what good/bad looks like

## How to Review

1. Step-by-step instructions for the subagent
```

### Scoping rules

| Pattern location | Files reviewed |
|---|---|
| `review-patterns/foo.md` | entire repository |
| `infra/review-patterns/foo.md` | `infra/` only |
| `packages/backend/review-patterns/foo.md` | `packages/backend/` only |

## Files in this skill

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition and step-by-step instructions for Claude Code |
| `review-instructions.md` | Report format and reviewer guidelines passed to every subagent |
| `samples/security.md` | Sample pattern: infrastructure security |
| `samples/reliability.md` | Sample pattern: infrastructure reliability |
