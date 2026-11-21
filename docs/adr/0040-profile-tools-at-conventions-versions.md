# 0040. The gate keeps a profile's tools at the versions `conventions` installed

- Status: accepted
- Date: 2026-11-22

## Context

The `react-spa` profile (#117) runs its tools from the project's `node_modules`, at the versions its lock file names. The developer may change `package.json` and `package-lock.json` (they add the runtime dependencies), so a developer change can install an older `typescript-eslint`, `eslint-plugin-react-hooks`, or `vitest`, and quietly shrink the rule sets or change how the tests run, while every check still passes. [ADR 0037](0037-gate-records-tool-versions.md) records the versions and leaves pinning until after the MVP. The second review of #117 asked whether the profile's tools should be kept at the versions `conventions` set; the maintainer decided that the gate keeps them there. `go`'s tools are binaries outside the project, so for them the versions stay recorded only.

Until now, no `conventions` commit could change a manifest or a lock file ([ADR 0029](0029-role-commits-passed-as-arguments.md), [ADR 0032](0032-gate-base-is-where-the-task-branch-left.md)), so in a new project the developer installed the profile's tools.

## Options considered

1. **Protect `package.json` and `package-lock.json`**: no version can change, but the developer cannot add the runtime dependencies either.
2. **Compare the profile's tools in the lock file**: `conventions` installs the profile tools and commits the manifest and the lock file; the gate reads the versions of the profile's tools from the lock file at the newest `conventions` commit and at the head, and fails when one differs. The developer still adds runtime dependencies.
3. **Leave it to the review**: nothing to build, but a version number in a large lock file diff is easy to miss.

## Decision

Option 2.

- A profile has one more field, `pinned`: `null` (for `go`), or `{"files", "lock", "read"}`: the files in the part's folder its tools are installed with (for `react-spa`, `package.json` and `package-lock.json`), the lock file among them, and a command that reads that lock file's text on standard input and prints one `<tool> <version>` line per profile tool it finds. This adds to the list of profile fields of [ADR 0028](0028-gate-interface.md) and [ADR 0037](0037-gate-records-tool-versions.md).
- A new check, `pinned-tools`, per part with `pinned`, after `suppressions`: the lines read from the lock file at the head equal those at the reference, the newest commit in the range named as `conventions`' (or, without one, the base). A version that changed, and a tool added or removed, fail it. A lock file missing at a commit reads as no tools.
- A commit named as `conventions`' may also change the `pinned` files in each part's folder. This adds to what a `conventions` commit may change in [ADR 0029](0029-role-commits-passed-as-arguments.md), [ADR 0032](0032-gate-base-is-where-the-task-branch-left.md), and [ADR 0039](0039-conventions-writes-gitignore.md).
- `conventions` installs every profile tool the design lists, at the design's version, and commits those files; the developer never changes a profile tool's version. A newer version is a change to the conventions, with an ADR.

## Reasons

- The role that sets the rules also sets the versions of the tools that run them, and the developer cannot weaken them by changing a version, as "Guardrails" 1 asks.
- The developer keeps the manifest and the lock file for the runtime dependencies, which the design's areas give them.
- The check reads two committed files and runs no installation, so it adds little time to a run.

## Consequences

- `gates/gate.py` reads `pinned`, runs `pinned-tools`, and lets a `conventions` commit change each part's `pinned` files. A profile without the field stops the gate (exit 2).
- The `react-spa` profile reads the versions of the tools its README names and of the packages in the `@typescript-eslint/`, `@vitest/`, and `@eslint/` scopes, which an npm `overrides` entry could change without changing the tool's own version. Other indirect dependencies are not kept.
- The `conventions` skill installs the profile tools, and `implement` never changes them. A project whose profile tools the developer installed before this change fails `pinned-tools` once, until `conventions` commits them.
- Pinning each tool to a version the profile itself names, and pinning `go`'s tools, stay after the MVP (#118).
