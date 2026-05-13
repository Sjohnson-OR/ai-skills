---
name: sentry-issue-debugger
description: >
  Debug and fix production errors by fetching Sentry issue details,
  stacktraces, and context via the Sentry API. Use when the user provides a
  Sentry issue URL or ID, mentions a Sentry error, or asks to debug or fix a
  production issue from Sentry. Triggered by phrases like "Sentry issue",
  "debug this Sentry error", "fix this Sentry bug", or a URL containing
  sentry.io/issues/.
---

# Sentry Issue Debugger

Fetch a Sentry issue's full context (stacktrace, request, breadcrumbs, tags)
and systematically debug the root cause in the local codebase.

## Prerequisites

The `CURSOR_SENTRY_AUTH_TOKEN` environment variable **must** be set in the shell where
Cursor runs. See [reference.md](reference.md) for step-by-step setup.

For short IDs (e.g. `PROJECT-123`), `SENTRY_ORG` must also be set.

Quick check — run in the terminal:

```bash
echo "Token: ${CURSOR_SENTRY_AUTH_TOKEN:+set}  Org: ${SENTRY_ORG:-not set}"
```

If blank, follow the setup in reference.md first.

## Workflow

### Step 1: Fetch the Sentry issue

Run the fetch script. Pass a Sentry issue URL, short ID, or numeric ID:

```bash
# Full URL
python3 <skill-directory>/scripts/fetch_sentry_issue.py "https://sentry.io/organizations/myorg/issues/12345/"

# Short ID (requires SENTRY_ORG env var)
python3 <skill-directory>/scripts/fetch_sentry_issue.py "PROJECT-123"

# Numeric ID
python3 <skill-directory>/scripts/fetch_sentry_issue.py "12345"
```

For multiple recent events (useful for spotting patterns):

```bash
python3 <skill-directory>/scripts/fetch_sentry_issue.py --events 3 "PROJECT-123"
```

The script requires network access. Use `required_permissions: ["full_network"]`
when invoking via the Shell tool.

If the script fails:
- **401/403**: Auth token is missing, expired, or lacks required scopes — see reference.md.
- **404**: Issue ID is wrong, or the token doesn't have access to that project.
- **Network error**: Check SENTRY_BASE_URL if using self-hosted Sentry.

### Step 2: Read the output and identify key facts

From the script output, extract:

1. **Exception type & message** — the what.
2. **Culprit** — the function/module Sentry blames.
3. **In-app stacktrace frames** — the where. Focus on frames marked `[APP]`.
4. **Request context** — the trigger (URL, method, body).
5. **Breadcrumbs** — the sequence of events leading up to the error.
6. **Environment & release** — is this production? Which version?
7. **Event count & first/last seen** — is it new or long-standing?

### Step 3: Map stacktrace to local code

Using the **in-app frames** from the "Key Files to Investigate" section:

1. Read each referenced source file in the local codebase.
2. Go to the exact line numbers from the stacktrace.
3. If filenames don't match local paths (common with deployed code), search
   for the function name or a unique code snippet from the context lines.
4. Check `git log` on those files — has the code changed since the release
   listed in the Sentry event? If yes, the bug may already be fixed.

### Step 4: Systematic debug analysis

Follow this protocol **strictly** — do not skip to proposing a fix.

#### 4a. Trace the execution path

Walk through the code path **from the entry point to the exception**, frame by
frame. For each in-app frame:
- What is the function's purpose?
- What inputs does it receive (from the frame's local variables and the
  previous frame)?
- What assumptions does it make about those inputs?

#### 4b. Identify the broken assumption

The exception happened because a code assumption was violated. Common patterns:
- **NoneType / AttributeError**: A value was None when the code assumed it existed.
  Why was it None? Missing DB record? Failed API call? Optional field?
- **KeyError / IndexError**: A collection didn't have the expected element.
  What determines the collection contents?
- **TypeError**: Wrong type passed. Where did the wrong type originate?
- **Timeout / ConnectionError**: External dependency failed. Is there retry logic?
  Is the timeout configured correctly?
- **ValidationError**: Input didn't match expectations. Where does validation happen?

#### 4c. Form a hypothesis

State a **specific, testable hypothesis** about the root cause before writing
any fix. Example:

> "The `user.organization` field is None when the user is a personal account
> (not part of an org). The `get_billing_info` function accesses
> `user.organization.billing_plan` without a None check, causing the
> AttributeError."

#### 4d. Verify the hypothesis

- Read the surrounding code to confirm the hypothesis.
- Check if there are guards, try/except blocks, or validations that should
  have caught this.
- Look at related code paths — does similar code elsewhere handle this case?
- Check tests — is there a test for this code path? Does it cover the edge case?

#### 4e. Check for patterns

If `--events` was used and multiple events were fetched:
- Are all events identical, or do they differ?
- Same endpoint / different endpoints?
- Same user type / different user types?
- Correlate with tags (environment, release, browser, OS).

### Step 5: Propose and implement the fix

Only after the hypothesis is confirmed:

1. **Explain the root cause** clearly to the user.
2. **Propose the minimal fix** — address the specific broken assumption.
3. **Consider defensive improvements** — should there be broader null checks,
   validation, or error handling in the surrounding code?
4. **Check for similar patterns** elsewhere in the codebase that might have
   the same vulnerability.
5. **Suggest test cases** that would have caught this — and ideally write them.

### Step 6: Verify the fix

- Ensure the fix handles the specific exception from the Sentry event.
- Run existing tests to confirm nothing is broken.
- If the codebase has type checking (mypy, pyright), run it.
- Check that the fix doesn't silently swallow errors that should propagate.

### Step 7 (optional): Hand off to GitHub Copilot for a fix PR

If the user prefers Copilot to implement the fix as a PR instead of fixing
locally, create a Copilot coding agent task directly via the `gh` CLI.

**Prerequisites**:
- The repository must have `.github/workflows/copilot-setup-steps.yml`
  configured and the Copilot coding agent enabled in repo settings.
- `gh` CLI version **2.80.0+** is required (the `agent-task` command was
  added in that release). Check with `gh version` and upgrade if needed.

#### 7a. Check for linked Jira tickets

The fetch script (Step 1) outputs a **Linked Jira Tickets** section when a
Jira integration is configured. Look for it in the output:

```
## Linked Jira Tickets

- **FOO-123**: Some ticket title ([link](https://jira.example.com/browse/FOO-123))
```

If a linked Jira ticket exists, note its key (e.g. `FOO-123`). You will
use it in the branch name and task description.

#### 7b. Write the analysis to a temp file

Create a markdown file with the full diagnosis. Include all context Copilot
needs — it cannot access Sentry, only the task description and the repo.

**If a Jira ticket is linked**, include it at the top of the description:

```markdown
## Jira Ticket
- **Ticket**: FOO-123
- **Link**: https://jira.example.com/browse/FOO-123

## Sentry Issue
- **Link**: <permalink from Sentry>
- **Error**: `<ExceptionType>: <message>`
- **Culprit**: `<file:line>` in `<function>`
- **Environment**: <env> | **Release**: <version>
- **Events**: <count> occurrences since <first_seen>

## Root Cause Analysis
<The hypothesis from Step 4c, confirmed in Step 4d. Be specific about
which function, which line, and what assumption is violated.>

## Proposed Fix
<Numbered list of specific changes. Reference exact file paths and line
numbers. Describe what each change should do.>

## Files to Change
<Bullet list of file paths with one-line description of the change>

## Test Cases to Add
<Describe test scenarios that should be added to prevent regression>
```

If no Jira ticket is linked, omit the "Jira Ticket" section.

Write this to a temp file:

```bash
cat > /tmp/sentry-fix-ISSUE_ID.md <<'ISSUE_BODY'
... the markdown above ...
ISSUE_BODY
```

#### 7c. Create a Copilot coding agent task

Use `gh agent-task create` to submit the task directly. This is the
preferred method — it works even when the repository has issues disabled
and directly starts the Copilot coding agent without requiring an
intermediate issue.

**Branch naming**: If a Jira ticket is linked, use it as a prefix in the
branch name so the PR is automatically linked to the Jira ticket:

```bash
# With linked Jira ticket (e.g. FOO-123):
gh agent-task create \
  -F /tmp/sentry-fix-ISSUE_ID.md \
  -R OWNER/REPO \
  --base-branch main \
  --branch FOO-123-fix-short-description-of-error

# Without a linked Jira ticket:
gh agent-task create -F /tmp/sentry-fix-ISSUE_ID.md -R OWNER/REPO
```

The branch name should follow the pattern `TICKET-KEY-fix-brief-slug`,
e.g. `FOO-123-fix-nullable-lock-fields`.

This requires `gh` CLI **2.80.0+** with network access. Use
`required_permissions: ["full_network"]` when invoking via the Shell tool.

The command returns a URL to the agent session (linked to a draft PR).
Report this URL to the user. Copilot will work on the task in the
background and open a PR for review (typically takes a few minutes).

**Useful follow-up commands:**

```bash
# Follow the agent's progress in real-time
gh agent-task view <session-id> --log --follow

# List recent agent tasks
gh agent-task list
```

#### 7c (alternative): Create a GitHub issue and assign to Copilot

If `gh agent-task` is unavailable (e.g., older `gh` version that cannot be
upgraded), fall back to creating an issue assigned to Copilot. Note: this
requires the repository to have issues enabled.

```bash
# With linked Jira ticket:
gh issue create \
  --title "FOO-123: Fix <concise description of the error>" \
  --body-file /tmp/sentry-fix-ISSUE_ID.md \
  --assignee "@copilot"

# Without linked Jira ticket:
gh issue create \
  --title "Fix: <concise description of the error>" \
  --body-file /tmp/sentry-fix-ISSUE_ID.md \
  --assignee "@copilot"
```

Report the created issue URL to the user. Copilot will create a branch,
implement the fix, and open a PR for review.
