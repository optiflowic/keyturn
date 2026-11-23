# 0054. Versions are the newest stable releases past a waiting period, confirmed from official sources, and each dependency is checked for supply-chain risks and against the runtime version the design names

- Status: accepted
- Date: 2026-11-23

## Context

A rehearsal run (#63) produced a design with "Node.js 22 or later" and `jsdom` 31.0.1, whose `engines` asks for `^22.22.2 || ^24.15.0 || >=26.0.0`. Node.js 22.13 meets the design and fails the dependency. The `design` skill checks each dependency for existence, maintenance, known vulnerabilities, and license, but not whether it works with the runtime; and the runtime had only a lower bound, copied from the profile's README ("Node.js 22 or later", "Go 1.24 or later"). The gate's workflow template installed Node.js 22 whatever the design said.

The toolchain is not a dependency: approving the stack covers it ([ADR 0015](0015-dependency-kinds.md)). That says who approves it, not which version is used. Nothing said how versions are chosen, so each role chose from what it remembered. And the newest release is also the one most likely to be a hijacked one: a stolen publishing token, a new maintainer who took over a package, or a look-alike name. Most such releases are found and withdrawn within days, and the dependency check ("Guardrails" 3) looked at none of these risks.

## Options considered

1. **Keep the lower bounds, and check each dependency's `engines` against them**: little to change, but a lower bound admits every later release, and the check cannot say which one the project runs.
2. **The newest stable releases past a waiting period, checked for supply-chain risks, one runtime version per part in the design, and a compatibility check against it**: every version is the newest stable release at that time, the runtime the newest LTS release; the design names one version of each part's runtime, and each dependency is checked against it and against the other dependencies.
3. **Let each project choose its own versions with the client**: the right place for a client's own choice, which #133 adds; but the default, when the client leaves it to keyturn, still needs a rule.

## Decision

Option 2, as the rule for keyturn and for the projects it works on:

- Every version is the newest stable release at that time that was published at least the waiting period ago: the runtime, the libraries, and the tools (linters, formatters, test tools, and the gate's tools). The waiting period is 7 days; a project changes it with an accepted ADR of its own. A release that fixes a known vulnerability of the one before it does not wait.
- Before anything is adopted (the runtime, a library, or a tool), its supply-chain and security risks are checked: a name made to look like a popular one, the release date against the waiting period, a recent change of the people who publish it, scripts that run on install, its provenance (for npm, a provenance attestation; for Go, the checksum database), and, as before, known vulnerabilities, maintenance, and license. A release that fails is not used: another release or another option is taken, or, when none passes or the choice changes what the client gets, the client is asked on a decision card. A missing provenance, or install scripts a package needs, is recorded and weighed with the rest, not a failure on its own.
- The runtime (for example Node.js or Go) takes the newest LTS release past the waiting period, or the newest stable release when it has no LTS release (Go has none).
- A different version is used only when the client names one, when versions do not work together (a library's `engines` or peer dependencies, or a tool that does not support a newer one yet), or when the newer release fails the supply-chain check, and the reason is recorded. A reason that comes from how a profile's tools work together (for example, `typescript` 6.0, since `typescript-eslint` does not support 7 yet) is written in the profile's `README.md`, and the project's design links to it from that dependency's check. A reason of the project's own goes in the project's ADR.
- Each version is confirmed from its official source at that time (the project's releases, or its package registry), never from memory.
- `design` names one version of each part's runtime in `design.md`'s "Stack", and checks the runtime and each new dependency for these risks, and each dependency against that runtime version and against the other dependencies, as part of the dependency check.
- `conventions` chooses a tool no profile names at its newest stable release. Before it installs the profile's tools, it checks that the runtime on `PATH` is the design's version or a later release of the same major version, and stops for the person otherwise; and it stops for the architect when the install reports a tool that does not support the design's runtime version.
- The profiles name the runtime as "the version the design names" instead of a lower bound, and the gate's workflow template installs that version, set by the person who copies it.

## Reasons

- The waiting period and the supply-chain items catch the attacks a vulnerability database cannot list yet: a hijacked release is new, often comes from a new publisher, and often runs an install script. Waiting a week costs little for a new project, and a fix for a known vulnerability does not wait.
- One version, checked against every dependency, finds a mismatch while the design is written, before `conventions` installs the tools and the gate fails on them.
- The newest stable releases carry the fixes of the older ones, and the newest LTS release of a runtime has the longest support; a project starts on what will be supported longest.
- A version confirmed from its official source does not depend on what a model remembers, which is often out of date.
- An exception with its reason in an ADR keeps a pinned older version visible, so it can be moved forward when the reason goes away.

## Consequences

- The checks are done by `design`, from the registry's data, and recorded in "Check"; the gate does not check them yet. It already runs `npm ci --ignore-scripts` and accepts only packages from the npm registry with an integrity hash (`react-spa`). Which of the items the gate checks mechanically (the release age, install scripts, provenance) is decided in its own issue.
- The `design` skill, its template, and the worked example have a runtime line in "Stack"; the dependency check has one more item.
- The `conventions` skill chooses tools without a profile at the newest stable release, and stops on a tool that does not support the runtime.
- The `react-spa` and `go` profiles' READMEs and install messages, and the gate's workflow template and `github/README.md`, no longer fix a lower bound.
- Nothing yet makes the project or the gate run the version the design names: the gate still uses the runtime on `PATH` ([ADR 0037](0037-gate-records-tool-versions.md), [ADR 0040](0040-profile-tools-at-conventions-versions.md)). Fixing the version in the project, protecting it, and running the gate in it stay for #133, together with the client's own choice of the runtime.
