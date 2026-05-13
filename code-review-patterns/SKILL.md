---
name: code-review
description: Run a full codebase review using all review patterns defined in review-patterns/ folders across the repository.
---

# Code Review

Run a comprehensive code review using the review patterns defined throughout the repository.

## Steps

1. **Read the review guidance** from `review-instructions.md` (in this skill's directory) — this defines the report format, severity levels, and reviewer guidelines that all review agents must follow.

2. **Find all review pattern files** by globbing for `**/review-patterns/*.md` across the repository. Each markdown file in a `review-patterns/` folder defines a single review pattern (what to check, how to review).

3. **Determine the scope for each pattern** from the location of its `review-patterns/` folder. The parent directory of `review-patterns/` is the sub-tree that pattern should focus on. For example:
   - `infra/review-patterns/reliability.md` → scope is `infra/`
   - `packages/backend/review-patterns/db-access.md` → scope is `packages/backend/`
   - `ios/review-patterns/architecture.md` → scope is `ios/`

4. **Read all pattern files** so their full content can be included in subagent prompts.

5. **Launch one subagent per pattern file**, all in the background, in parallel (maximum 10 at a time). Each subagent must:
   - Use the **sonnet** model
   - Be a **general-purpose** subagent type
   - Run in the background (`run_in_background: true`)
   - Receive a prompt that includes:
     - The full text of `review-instructions.md` from this skill's directory (the report format and guidelines)
     - The full text of the specific review pattern file
     - An instruction to focus ONLY on files under the relevant sub-tree
     - An instruction to output the full review report as its final message

6. **Wait for all agents to complete**, then collect their reports.

7. **Produce a complete consolidated report** by reading all subagent outputs and combining them into a single deduplicated report. The report must include:

   ### Status Table
   A table showing each pattern, its area, its status (PASS/WARN/FAIL), and finding counts by severity (critical/warning/info).

   ### Critical Findings
   All critical-severity findings from all reports. If multiple reports flag the same issue, merge into one finding with the highest severity.

   ### All Findings by Area
   All warning and info findings grouped by area (e.g., `infra/`, `packages/backend/`, `ios/`, `packages/frontend/`). Within each area, list findings from all patterns that reviewed that area. Deduplicate: if two patterns report the same issue (same file and line), keep only one entry with the higher severity.

   ### Summary
   2-3 sentences on overall codebase health and key themes.

   **Important**: Include every finding from every subagent in the final report — do not omit or summarize away individual findings. The only reason to drop a finding is if it is a true duplicate of another finding (same file, same line, same issue). Preserve file paths and line numbers exactly as reported by the subagents.
