<!--
Template: design document (internal). Filled in by the architect, from requirements.md and the stack profile.

- Always written in English. Be as detailed as the next roles need, and no more.
- Scale the design to the project: a small tool gets a simple structure; a multi-user system gets the boundaries and security controls it needs.
- Every meaningful decision has an ADR in internal/adr/. This document states the result and links to the ADR; the reasoning stays in the ADR.
- Check the existing ADRs before deciding. Follow an accepted ADR instead of reconsidering it.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Design: <name of what is being built>

Based on requirements version <n>.

## Summary

<!-- About three lines: the overall shape of the design and the main choices. -->

<summary>

## Stack

<!--
The stack profile used, from profiles/. If no profile fits, write "No profile" and the stack:
the gate's coverage is then limited, and the delivery report must say so.
-->

- Stack profile: <profile name | No profile: the stack>
- Repository structure: <one repository | monorepo | several repositories>, see <link to the ADR>

## Structure

<!--
One heading per part (module, package, service, or component): what it is responsible for and how it talks to the other parts.
"Serves" lists the requirements the part exists for. A part that serves no requirement should not exist.
Add a diagram only if it makes the structure easier to follow than the text.
-->

### <part name>

- Serves: R-<n>
- Location: `<path>`

<responsibility, and how it talks to the other parts>

## Data model

<!--
The data the deliverable stores or exchanges: each entity, its fields, and how entities relate.
Say who owns each record and who may read or change it (this is what the security role checks for data isolation).
Leave the section with "No stored data." when there is none.
-->

### <entity>

- Owner and access: <who owns a record, and who may read or change it>

| Field | Type | Notes |
|---|---|---|
| <field> | <type> | <notes> |

## Libraries and external services

<!--
Every dependency and external service the work adds or relies on. "Kind" says what each dependency is (see ADR 0015 in keyturn):
- runtime: a library or tool that is part of the deliverable or builds it (for example React, or Vite). Never a profile tool, even if the stack profile recommends it.
- profile tool: a development tool the stack profile names, that only checks, formats, or tests the code and is not part of the deliverable (for example a linter or a test tool).
- other tool: a development tool no stack profile names. While no profile exists, every development tool is an other tool.
Do not list the language toolchain and standard library (covered by approving the stack) or the gate's scanners (installed by the gate, never added to the project).
- A new runtime dependency, a new other tool, or a new external service always needs the client's approval before it is used, under "Must agree" in design-summary.md.
- A new profile tool is approved by the stack profile, and is listed in design-summary.md for information only.
- Every new dependency, of every kind, is checked for existence, maintenance status, known vulnerabilities, and license, and the result is recorded in "Check".
- "New" is no only for a dependency the project already has. A runtime library the stack profile suggests is still new the first time the project adds it, and needs the approval and the check.
Leave the section with "None." when there are none.
-->

| Name | Version | Kind | Purpose | Serves | New | Check |
|---|---|---|---|---|---|---|
| <name> | <version> | <runtime \| profile tool \| other tool> | <what it is used for> | R-<n> | <yes \| no> | <result of the dependency check, or "existing"> |

## Areas the work may change

<!--
The files and folders the developer may change, as paths or glob patterns relative to the repository root, one per row.
The gate compares the changed files with this list and flags anything outside it (phase 4). A change outside these areas needs an updated design first.
Never list the protected paths here: gate scripts, stack profiles, the CI jobs that run the gates, linter configs, conventions, and tests written by QA.
-->

| Path | What changes | Serves |
|---|---|---|
| `<path or glob>` | <what changes there> | R-<n> |

## Requirements coverage

<!-- One row per requirement that is not removed, so a requirement change shows which parts are affected. -->

| Requirement | Parts |
|---|---|
| R-<n> | <part names> |

## Decisions

<!-- The ADRs this design depends on. -->

- <link to the ADR>: <one line on what it decides>

## Open questions

<!--
Questions the design could not settle. A question for the client becomes a decision card.
Leave the section with "None." when there are none.
-->

- <question>: <who answers it, and what waits for the answer>
