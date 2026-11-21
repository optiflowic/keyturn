# 0037. The gate records the versions of the tools it ran; pinning them waits until after the MVP

- Status: accepted; leaving every tool's version free until after the MVP superseded by [0040](0040-profile-tools-at-conventions-versions.md) for the tools a profile installs in the project (kept at the versions `conventions` installed)
- Date: 2026-11-22

## Context

"Guardrails" 6 ([`docs/design/guardrails.md`](../design/guardrails.md#6-everything-is-traceable)) says the delivery report lists the tool versions that were used. The gate runs each profile's tools ([ADR 0028](0028-gate-interface.md)), but neither its output nor its log says which versions ran: `golangci-lint` comes from the person's `PATH`, and the `react-spa` tools come from the project's lock file. The same commit can then pass or fail with another version, and nobody can tell afterwards which one judged it. The second review of the `go` profile (#116) asked whether a profile should pin an exact version, and whether the delivery report should record the one used.

## Options considered

1. **Pin each tool's version in the profile**, and stop when another one is installed: the results can be repeated, but every person must install exactly that version, and every new release needs a profile change. It also needs a decision on how each stack pins its tools (a lock file, a download by the gate, or a version check).
2. **Record the versions only**: a profile names a command that prints the versions of its tools, and the gate runs it at the head and writes its output to its output and its log. Nothing is pinned, but every delivery says what judged it.
3. **Leave it to the delivery report**, which asks the person for the versions: nothing to build, but the report would hold what someone remembers, not what ran.

## Decision

Option 2 during the MVP. Pinning (option 1) is left for after the MVP, and recorded in #118.

- A profile has one more field, `versions`: a command run in the part's folder at the head, after the profile's setup, whose output lines name the tools and their versions (for example `golangci-lint has version 2.15.0 ...`, or `vitest 5.1.1`). This replaces the list of profile fields in [ADR 0028](0028-gate-interface.md) ("exactly these fields"); the other fields are unchanged.
- The gate prints one line per part after the check lines, `VERSIONS [<part>]: <line>; <line>; ...`, and adds `versions` to its log: one entry per part, with its `part`, `profile`, and `versions` (the lines). The versions are recorded, never judged: a command that fails, or a setup that failed, is recorded as `not read: ...`, and the result of the gate does not change.
- `deliver`'s last step lists, under "Models and tools used" in the delivery report, the versions each part's entry in the gate's log records.

## Reasons

- A record of what ran is enough to trace a delivery and to repeat it by hand, which is what "Guardrails" 6 asks for; it needs no new decision about how each stack installs its tools.
- Reading the versions at the head, after the setup, gives the tools the checks actually used, including those installed from the project's lock file.
- Pinning changes what a person must install, and is worth deciding once both profiles have been used on a real application.

## Consequences

- `gates/gate.py` reads `versions` from every profile, and stops (exit 2) on a profile without it. The `go` and `react-spa` profiles have it.
- A gate log from before this change has no `versions`; the delivery report then says the versions were not recorded.
- A new release of a tool can still change a result. The versions in the log show when that happened.
