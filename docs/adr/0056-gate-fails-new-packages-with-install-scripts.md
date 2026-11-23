# 0056. The gate fails a new package with an install script that no accepted ADR names

- Status: accepted
- Date: 2026-11-23

## Context

The gate never runs install scripts (`npm ci --ignore-scripts`), and the roles install without them ([ADR 0055](0055-installs-skip-install-scripts.md)). But nothing notices a new package that has one, so a package with a script can enter the lock file unseen, and its script runs the first time anyone installs the project without the flag: the client's own team, their CI, or a deployment. ADR 0055 lets an accepted ADR of the project allow one package's script with the line `- Allows install scripts: <package>@<version>`; the design's dependency check records install scripts ([ADR 0054](0054-newest-stable-versions-checked-against-the-runtime.md)), but only for direct dependencies, and nothing checks that record mechanically.

npm's lock file marks every package that runs scripts on install with `"hasInstallScript": true` in its entry, direct and indirect alike. Go modules have no install scripts.

## Options considered

1. **A gate check that reads the lock file at the base and the head**: offline, cheap, and it finds indirect packages too. It trusts the lock file's mark, which npm writes from the package's manifest.
2. **Ask the registry for each new package's scripts**: does not trust the lock file, but needs the network in every run, and the gate's checks read committed files only.
3. **Leave it to the review**: a mark in a large lock file diff is easy to miss.

## Decision

Option 1. This adds a field to the profiles of [ADR 0028](0028-gate-interface.md), [ADR 0037](0037-gate-records-tool-versions.md), and [ADR 0040](0040-profile-tools-at-conventions-versions.md), and a check:

- A profile has one more field, `install_scripts`: `null` (for `go`), or `{"lock", "read"}`: the lock file in the part's folder, and a command that reads its text on standard input and prints one `<package>@<version>` line per package that runs scripts on install (for `react-spa`, every entry of `package-lock.json` with `"hasInstallScript": true`, wherever it is installed, except the part's own entry, `""`).
- A new check, `install-scripts`, per part with the field, after `pinned-tools`: every line read from the lock file at the head that is not among those read at the base (a new package, or a new version of one) fails it, unless an ADR accepted at the newest commit named as `spec`'s or `design`'s, or else at the base, has the line `- Allows install scripts: <package>@<version>` for exactly that line, in the lines before its first `##` heading, next to `- Status: accepted` (ADR 0055). The value may be in backticks. A lock file missing at a commit reads as no packages.
- The lines are read there, not at the newest `conventions` commit where the suppressions' ADRs are read ([ADR 0032](0032-gate-base-is-where-the-task-branch-left.md)): only the architect writes them (ADR 0055), and a `conventions` commit, which may write ADRs and installs the profile's tools, must not allow its own tools' scripts.
- The check reads committed files only, and runs no installation and no network request.
- The part's own lifecycle scripts (`preinstall`, `install`, `postinstall`, and `prepare` in its `package.json`) are not checked: the gate and the roles never run them, and the review reads changes to `package.json`.

## Reasons

- A package with a script that nobody allowed is found in the change that adds it, by the check the developer cannot change, before the client's own installs run it.
- The lock file already has the mark for every package, indirect ones included, which the design does not list ([ADR 0018](0018-direct-dependencies-in-the-design.md)); reading it costs one small command per part.
- Reading the allowing line at the architect's newest commit keeps the rule of the suppressions' ADRs, that no ADR the developer's commits add approves anything, and adds that the role which installs the profile's tools cannot approve their scripts either.

## Consequences

- `gates/gate.py` reads `install_scripts`, and runs `install-scripts`. A profile without the field stops the gate (exit 2).
- The `react-spa` profile reads `hasInstallScript` from `package-lock.json`; the `go` profile has `"install_scripts": null`. The `react-spa` README lists the check, and what it does not find: a package whose lock entry lost its mark (the `packages` check still makes sure every package comes from the npm registry with an integrity hash, but not that its mark matches the registry), and the part's own scripts.
- A package that was at the base with a script is not checked again, so a project that already had one before keyturn needs no ADR until its version changes.
- A package's script is allowed only through the architect's ADR, as ADR 0055 says: `design` resolves each part's tree before `implement` starts and writes a line for every package in it with an install script (in a `react-spa` tree, at least `fsevents`, an optional dependency of `vite` for macOS), so that a task does not stop on this check. A package or version that an indirect release brings after the design still fails it, and with `deliver` stops the task for the maintainer ([ADR 0031](0031-documents-fixed-once-implement-starts.md)).
