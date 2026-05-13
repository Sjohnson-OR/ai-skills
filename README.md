# ai-skills

A collection of Claude Code skills for automating common engineering workflows.

## What are skills?

Skills are reusable prompt files that extend Claude Code with specialized behaviors. Drop a skill folder into `~/.claude/skills/` and Claude Code picks it up automatically.

## Skills

| Skill | Description |
|-------|-------------|
| [brainstorming](./brainstorming/) | Turn ideas into designs through collaborative dialogue before writing code |
| [cloudsmith-migration](./cloudsmith-migration/) | Migrate a project to use Cloudsmith as the primary artifact repository |
| [code-review-patterns](./code-review-patterns/) | Run a comprehensive code review using patterns defined throughout the repository |
| [github-onboarding](./github-onboarding/) | Guide through setting up GitHub: account creation, security, org access, SSH keys |
| [grafana-dashboard](./grafana-dashboard/) | Create a new Grafana dashboard as a JSON file committed to the repository |
| [gspec](./gspec/) | Spec-driven development — keep specs and code in sync |
| [optimize-dbt-athena-queries](./optimize-dbt-athena-queries/) | Diagnose and optimize expensive Athena queries in dbt models |
| [oura-api-local](./oura-api-local/) | Authenticate and query the Oura Cloud API from local tools |
| [pulumi-best-practices](./pulumi-best-practices/) | Best practices for writing reliable Pulumi programs |
| [sentry-issue-debugger](./sentry-issue-debugger/) | Fetch a Sentry issue's full context and debug production errors |
| [update-catalog-info](./update-catalog-info/) | Create or update `catalog-info.yaml` for Backstage Software Catalog |
| [vibe-cleanup-typescript](./vibe-cleanup-typescript/) | Identify and fix common code quality issues in AI-generated TypeScript |
| [writing-plans](./writing-plans/) | Turn a spec or design into a concrete implementation plan |

## Usage

Clone this repo and symlink or copy any skill into your Claude Code skills directory:

```bash
git clone https://github.com/Sjohnson-OR/ai-skills.git
cp -r ai-skills/<skill-name> ~/.claude/skills/
```

Or to get all skills at once:

```bash
git clone https://github.com/Sjohnson-OR/ai-skills.git
cp -r ai-skills/*/ ~/.claude/skills/
```

Then invoke a skill in Claude Code:

```
/<skill-name>
```
