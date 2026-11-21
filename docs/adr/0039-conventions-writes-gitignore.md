# 0039. `conventions` writes the project's `.gitignore` files

- Status: accepted
- Date: 2026-11-22

## Context

The gate protects every `.gitignore` in the repository ([ADR 0028](0028-gate-interface.md)), because what Git ignores changes what some checks see (Prettier, for example, skips the files a `.gitignore` names). [ADR 0029](0029-role-commits-passed-as-arguments.md) and [ADR 0032](0032-gate-base-is-where-the-task-branch-left.md) list what each role's commits may change, and no role may change a `.gitignore` (QA only inside its own folders). A `react-spa` project (#117) needs one from its first delivery: `npm ci` fills `node_modules/` and `vite build` writes `dist/`, and without a `.gitignore` they show as untracked in every role's `git status`, and the repository the client receives has none.

## Options considered

1. **`conventions` writes them**: the standards role already writes the files that decide what the checks see (the linter and formatter configs, [ADR 0028](0028-gate-interface.md)), before the developer starts ([ADR 0031](0031-documents-fixed-once-implement-starts.md)). The developer still may not change them.
2. **Keep them protected from every role**: the developer works with `.git/info/exclude`, which is not committed, and the delivered repository has no `.gitignore`. The gap goes into each delivery report.
3. **A person commits one before the request**: nothing changes in keyturn, but every new project needs a step outside the run.

## Decision

Option 1. A commit named as `conventions`' may also change `**/.gitignore`. This adds to what a `conventions` commit may change in [ADR 0029](0029-role-commits-passed-as-arguments.md) and [ADR 0032](0032-gate-base-is-where-the-task-branch-left.md); every other role's list is unchanged, and a `.gitignore` stays a protected path for the developer's commits.

`conventions` writes the entries a stack profile's README names (for `react-spa`, `node_modules/` and `dist/`), and the project's own build output, in a `.gitignore` in the part's folder, never inside QA's folders or the design's "Areas the work may change". A later change is a change to the conventions, with an ADR, like any other.

## Reasons

- What Git ignores is part of what the checks see, and the role that sets the checks is the one that should set it.
- `conventions` runs before `implement`, so the files are in place before the developer installs anything, and the developer never needs to change them.
- The delivered repository keeps a `.gitignore`, which a person expects in any npm project.

## Consequences

- `gates/gate.py` lets a `conventions` commit change `**/.gitignore`.
- The `conventions` skill writes the `.gitignore` entries the profile names, and checks them in its step 6.
- A `.gitignore` the developer needs for something new (a new tool's output) is a request to `conventions`, as a rule change is.
