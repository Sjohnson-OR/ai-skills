---
name: vibe-cleanup-typescript
description: Fixes common issues in AI generated Typescript code. Runs through a checklist to find and improve several known AI antipatterns.
---

# Vibe Cleanup TypeScript

This skill identifies common code quality issues in newly generated code.

When using this skill, analyze the target files and see if they have
any of the issues mentioned below. Perform fixes as needed and present
a summary at the end.

# Determining the target files

First determine which files to analyze, depending on the session context.

Common use cases for applying this skill:
 - Fixing files that were just created or edited in the current session
 - Fixing all files that are part of a pending pull request.
   - If this is the case then use `git` to find the list of files.
 - Analyzing existing files (if specifically directed)

If the user does not specify which files to analyze, then by default you should
analyze the recently modified files.

# Quality Issues

Below is a list of possible code issues. Check the target files to see if it has any
of the issues described below.

## Issue: Duplicate code

This problem happens when there is new code that does the same thing as an existing function in
the project.

To detect this problem, look at all new functions and judge whether they seem generic enough that
they are likely already in the project or can be reused. For functions like this, do a search to
find existing functionality that can be reused.

To fix: Update the function to use the existing / shared version and delete the duplicate version.

You may need to refactor the existing code to allow it to be shared. This can include adding an 'export'
keyword, or moving the function to another common file or directory that both usages can import from.
It is strongly encouraged for you to do extra refactoring work in order to avoid duplicate code.

## Issue: Overly complex inline types

This problem happens when a complex Typescript type is written inline to where it's used.
This is a form of shortcut-taking. 

If a type is not very simple, then it should be moved to the top level and given a descriptive
name. This will help with readability and code clarity.

Issue example. This has an overly complex inline type:

    const afterDeployActions: Array<{ type: 'shell' | 'pm2-start',
          - shell?: string, pm2?: { name: string; command: string } }> = [];

Fixed example. The type is moved to a new name at the top level:

    type AfterDeployAction =
         | { type: 'shell'; shell: string }
         | { type: 'pm2-start'; pm2: Pm2StartAction };

    ...

    const afterDeployActions: AfterDeployAction[] = [];

## Issue: Inlined imports

Don't use an inline `async import` expression in situations where the library can just be
imported at the top of the file. Top level imports are strongly preferred.

The `async import` style should only be used very rarely, in situations where we actually need to
delay loading of the module so that it's a dynamic load instead. If it's not required to do
a dynamic load then don't use this pattern.

Motivations:

 1. It's harder to read code and understand a file's dependencies when the `async import` pattern is used.
 2. Sometimes this pattern will transitively require the calling function to be `async` in a situation where
    it otherwise didn't need to be async.

To fix this: Move imports to be standard `import` lines at the top of the file.

(Or if the existing code is using CJS `require`, then stay consistent with the existing code and use
a top-level `require` instead)

## Issue: Other code that should not be inlined

The same issue applies to other code constructs that are unnecessarily inlined, such as defined inside
another expression or function. It's more readable and clear for these definitions to be at the top
level so that the structure hierarchy is more "flat".

Details:

 - Function definitions: These can sometimes be inlined as a lambda if they are very simple, not reused, and
   they take advantage of local variables. But most, functions should be defined at the top level with
   a `function <name>()` style declaration.

 - Type definitions (such as `type` or `interface`): These should almost never be defined inline, they should
   be at the top level.

To fix: Refactor the file to move these definitions as needed.

## Issue: Local type hacks

Another type of shortcut-taking is adding local overrides for existing Typescript types.

One example: Extending an existing type with `&`:

    // Need to add .extraField to the type:
    const data = await fetchData() & {
        extraField: '123'
    }
    use(data.extraField);

Another example: Overriding a type with `as`:

    // Need to add .extraField to the type:
    const data = await fetchData() as ExpectedDataType;
    
Both of these are antipatterns and probably create tech debt. If you need to override a type like
this, it probably means that the correct approach is to modify the existing type to have the shape that
you expect. This will keep the existing types more accurate which will be more helpful and less
confusing as the types are used across the codebase. We don't want local 'variations' of what is
essentially the same type.

## Issue: Backwards compatibility for no reason

This issue is when the code or the public API includes "backwards compatibility" versions of the code,
but they are used in a situation where the code does not actually need backwards compatibility.
This is typically done in an overabundance of caution, without taking the time to understand
if the backwards compatibility is actually needed. For example, we may be working on a brand
new section of the code which has no existing users, in which case we can freely change the new API
without issue. Or if there are existing call sites, it might be possible to simply update all those
call sites to use the new version.

Look for any "backward compatibility" exports. Some signs of these exports:
 - When the same symbol is exported in multiple names.
 - When the symbol is renamed to a different name for the public export.

Goals:

 - Whenever possible, we want each symbol to be exported only once, not multiple times.
 - Whenever possible, we want each symbol to be exported with the same name that it has in the internal code.
   It vastly helps our code understanding and maintenance if a concept/feature has the same name across the codebase.

To fix this issue:
 - Investigate every "backwards compatibility" occurence to determine if it's actually needed.
 - Eliminate any "backwards compatibility" export that is not essentially required.
 - If needed, update the call sites for any exports so they all use the same name, and
   refactor existing code to use the latest exports.
 - If unsure, ask a question to the user to confirm if any legacy exports are actually needed.

## Unnecessary comments that describe the work process

This issue describes unnecessary comments that are badly worded. Specifically,
if there are code comments that are a "journal" of the process of doing the work,
instead of describing the latest code itself.

Fix: These comments should be removed. The only comments that should be
part of the codebase are comments that are still relevant and describe
the latest code.

Example of an unnecessary comment. This describes something that happened in the process of working
on the code, instead of describing the latest code:

    // Removed fs and path imports - no longer writing to file
    ...

Example of a good comment. This describes what the latest code actually does:

    // Log a warning - all other drift types are destructive
    warnings.push(`Skipping destructive migration: ${drift.type}`);

    // Print output to stdout
    console.log(...)

## Overly verbose comments

This problem is about comments that are just overly verbose and unnecessary.

Example of an unnecessary comment:

    /**
     * Creates a wretch client configured for MOI API calls with standard timeout.
     */
    export function createMoiClient(url: string) {
      return wretch(url, { timeout: REQUEST_TIMEOUT_MS });
    }

The reason this is unnecessary is because it just describes what the code is obviously
doing already. In that example, it's very obvious that the code uses the standard
timeout, so this doesn't need to be mentioned as a comment.

So, if the code is already very simple and readable, then prefer to not add
a comment for it, especially if the comment would just repeat the same information
and not add anything.
