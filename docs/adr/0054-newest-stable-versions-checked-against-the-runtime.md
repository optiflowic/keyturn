# 0054. Versions are the newest stable releases, confirmed from official sources, and each dependency is checked against the runtime version the design names

- Status: accepted
- Date: 2026-11-23

## Context

A rehearsal run (#63) produced a design with "Node.js 22 or later" and `jsdom` 31.0.1, whose `engines` asks for `^22.22.2 || ^24.15.0 || >=26.0.0`. Node.js 22.13 meets the design and fails the dependency. The `design` skill checks each dependency for existence, maintenance, known vulnerabilities, and license, but not whether it works with the runtime; and the runtime had only a lower bound, copied from the profile's README ("Node.js 22 or later", "Go 1.24 or later"). The gate's workflow template installed Node.js 22 whatever the design said.

The toolchain is not a dependency: approving the stack covers it ([ADR 0015](0015-dependency-kinds.md)). That says who approves it, not which version is used. Nothing said how versions are chosen, so each role chose from what it remembered.

## Options considered

1. **Keep the lower bounds, and check each dependency's `engines` against them**: little to change, but a lower bound admits every later release, and the check cannot say which one the project runs.
2. **The newest stable releases, one runtime version per part in the design, and a compatibility check against it**: every version is the newest stable release at that time, the runtime the newest LTS release; the design names one version of each part's runtime, and each dependency is checked against it and against the other dependencies.
3. **Let each project choose its own versions with the client**: the right place for a client's own choice, which #133 adds; but the default, when the client leaves it to keyturn, still needs a rule.

## Decision

Option 2, as the rule for keyturn and for the projects it works on:

- Every version is the newest stable release at that time: the runtime, the libraries, and the tools (linters, formatters, test tools, and the gate's tools).
- The runtime (for example Node.js or Go) takes the newest LTS release, or the newest stable release when it has no LTS release (Go has none).
- A different version is used only when the client names one, or when versions do not work together (a library's `engines` or peer dependencies, or a tool that does not support a newer one yet), and the reason goes in an ADR (the project's, or keyturn's for a profile).
- Each version is confirmed from its official source at that time (the project's releases, or its package registry), never from memory.
- `design` names one version of each part's runtime in `design.md`'s "Stack", and checks each new dependency against that version and against the other dependencies, as part of the dependency check.
- `conventions` chooses a tool no profile names at its newest stable release. Before it installs the profile's tools, it checks that the runtime on `PATH` is the design's version or a later release of the same major version, and stops for the person otherwise; and it stops for the architect when the install reports a tool that does not support the design's runtime version.
- The profiles name the runtime as "the version the design names" instead of a lower bound, and the gate's workflow template installs that version, set by the person who copies it.

## Reasons

- One version, checked against every dependency, finds a mismatch while the design is written, before `conventions` installs the tools and the gate fails on them.
- The newest stable releases carry the fixes of the older ones, and the newest LTS release of a runtime has the longest support; a project starts on what will be supported longest.
- A version confirmed from its official source does not depend on what a model remembers, which is often out of date.
- An exception with its reason in an ADR keeps a pinned older version visible, so it can be moved forward when the reason goes away.

## Consequences

- The `design` skill, its template, and the worked example have a runtime line in "Stack"; the dependency check has one more item.
- The `conventions` skill chooses tools without a profile at the newest stable release, and stops on a tool that does not support the runtime.
- The `react-spa` and `go` profiles' READMEs and install messages, and the gate's workflow template and `github/README.md`, no longer fix a lower bound.
- Nothing yet makes the project or the gate run the version the design names: the gate still uses the runtime on `PATH` ([ADR 0037](0037-gate-records-tool-versions.md), [ADR 0040](0040-profile-tools-at-conventions-versions.md)). Fixing the version in the project, protecting it, and running the gate in it stay for #133, together with the client's own choice of the runtime.
