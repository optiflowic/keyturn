# 0055. Every role installs packages without running their install scripts; an accepted ADR of the project allows one package's script, which then runs alone

- Status: accepted
- Date: 2026-11-23

## Context

The roles install packages on the agent's machine: `implement` adds the runtime dependencies, `conventions` installs the profile's tools, and `qa` and `security-review` build the deliverable from "How to run". A plain `npm install` or `npm ci` runs each package's `preinstall`, `install`, and `postinstall` scripts there, and the project's own lifecycle scripts (`prepare` among them), with the agent's files, tokens, and network, before any check has looked at the package. A hijacked release usually acts through such a script ([ADR 0054](0054-newest-stable-versions-checked-against-the-runtime.md)). The gate already runs `npm ci --ignore-scripts`, and `conventions` already passes `--ignore-scripts` for the profile's tools; nothing said so for the other installs.

Some packages need their script to work (for example, one that builds a native module). The design's dependency check records whether a package runs scripts on install, and ADR 0054 weighs that with the rest, but nothing said who may run such a script, or where that is decided.

## Options considered

1. **Skip install scripts on every install, and allow one package's script by a fixed line in an accepted ADR of the project**: a hijacked release's script does not run on the agent's machine, and the one script the deliverable needs runs alone, for a package and version someone checked and recorded. A role must remember the flag on each install.
2. **Also set `ignore-scripts=true` in the project's `.npmrc`**: a forgotten flag is covered, since the `react-spa` profile protects `.npmrc`. But it changes how the client's own team and CI install the project after the delivery, which is a choice about the deliverable, not about the agents, and it covers only npm in that folder.
3. **Leave it to the sandbox (#119)**: the sandbox limits what a script can reach, but it is not in the MVP, and a script that runs in it still runs with the project's files.

## Decision

Option 1:

- Every role that installs packages (`implement`, `conventions`, `qa`, `security-review`, and any role that later does) installs them without running install scripts: for npm, with `--ignore-scripts` on every npm command that installs or changes packages (`npm install`, `npm ci`, `npm update`, `npm uninstall`, `npm dedupe`, `npm audit fix`), whatever "How to run" or another document says, and never `npx`, `npm exec`, `npm create`, or `npm init <initializer>`, which download a package and run it. This also skips the project's own lifecycle scripts. The stack profile's `README.md` says how for its package manager; a profile whose package manager has no install scripts (`go`) says so.
- A package's install script runs only when an accepted ADR of the project, in `keyturn/internal/adr/`, has the line `- Allows install scripts: <package>@<version>` before its first `##` heading, next to `- Status: accepted`, for exactly the version the lock file installs. The role then runs that package's script alone (for npm, `npm rebuild --ignore-scripts=false <package>@<version>`, which runs it even where a person's own npm config skips scripts), never every package's. A different version, a package without such a line, or an ADR that is not accepted, allows nothing.
- The line counts only as the architect committed it, as a suppression's ADR counts only as accepted at the base for the gate ([ADR 0038](0038-suppressions-allowed-in-a-folder.md)): `implement` reads it at the commit its work started from, `conventions` at `HEAD` before its own commit, and `security-review` at its inputs base, never from a file in the working tree; `qa` reads it at the head, which, with `deliver`, it tests only after the gate passed, so the developer has not changed an ADR (the ADR folder is protected). The developer and `conventions` never write or change the line.
- The architect writes the line, in the ADR of the decision that needs the package, or in an ADR of its own for a profile tool or an indirect package, after checking the package as the dependency check says (ADR 0054) and recording what the script does. The line's ADR needs the client's agreement only when the decision it belongs to does. A role that finds a package whose script the deliverable needs, with no such line, stops that part and asks the architect; it never runs the script to find out.
- The gate never runs install scripts. It does not check this line yet: finding a new package with an install script that no accepted ADR names is the gate's own check (#166), which reads the same line.

## Reasons

- A hijacked release acts when it is installed, before the gate, the reviews, or the dependency scan can look at it. Skipping the scripts on the agent's machine stops the most common way such a release does harm, at almost no cost: most packages need no script, and the gate already builds and tests without them.
- One fixed line, in the place where the project's decisions already live, keeps every allowed script visible and tied to a version: an upgrade needs a new check and a new line. The same line can be read by the gate, as a suppression's ADR is ([ADR 0028](0028-gate-interface.md), [ADR 0038](0038-suppressions-allowed-in-a-folder.md)).
- Running the one allowed script alone keeps an allowance for one package from running every other package's script with it.

## Consequences

- `implement`, `conventions`, `qa`, and `security-review` install with `--ignore-scripts`, and run an allowed package's script alone; `implement` writes "How to run" the same way. `design` writes the line when a dependency needs its script, and the project ADR template has it.
- The `react-spa` profile's `README.md` says how to install without scripts, how to find the packages that have them (`hasInstallScript` in `package-lock.json`), and how to run the one allowed; the `go` profile's says that Go modules have no install scripts.
- A package that does not work without its script stops that part of the work until the architect has checked it and written the line.
- A role that forgets the flag is not stopped by anything on the agent's machine during the MVP; the gate's check (#166) finds the package afterwards, and the sandbox (#119) limits what a script can reach.
