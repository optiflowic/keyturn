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
Name each profile and its folder exactly as in the form below (for example `go` for `api/`, `react-spa` for `web/`):
deliver writes the gate's `parts` in keyturn/config.json from this line, and stops when it cannot read it.
The runtime line names one exact version per part, never a lower bound (ADR 0054 in keyturn).
-->

- Stack profile: <`profile` for `folder/`, one per part, separated by commas | `profile` alone, for the whole repository | No profile: the stack>
- Runtime: <runtime and exact version for `folder/`, one per part, separated by commas (for example Go 1.27.4 for `api/`, Node.js 26.13.1 for `web/`)>, confirmed from the official sources on <date>
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
Every direct dependency and external service the work adds or relies on: what the project's manifest names itself (for Go, the `require` entries in go.mod without an `// indirect` comment), including the peer dependencies a direct dependency requires.
Indirect dependencies are not listed: the lock file fixes them and is always committed (for example package-lock.json for npm; for Go, go.mod, whose `// indirect` entries fix them, with go.sum for their checksums), and the gate's dependency scan checks them (ADR 0018 in keyturn). Until the gate has a dependency scan, nothing checks them, and the delivery report lists them under "What was not verified".
"Kind" says what each dependency is (see ADR 0015 in keyturn):
- runtime: a library or tool that is part of the deliverable or builds it (for example React, or Vite). Never a profile tool, even if the stack profile recommends it.
- profile tool: a development tool the stack profile names, that only checks, formats, or tests the code and is not part of the deliverable (for example a linter or a test tool).
- other tool: a development tool no stack profile names. While no profile exists, every development tool is an other tool.
Do not list the language toolchain and standard library (covered by approving the stack) or the gate's scanners (installed by the gate, never added to the project).
- A new runtime dependency, a new other tool, or a new external service always needs the client's approval before it is used, under "Must agree" in design-summary.md.
- A new profile tool is approved by the stack profile, and is listed in design-summary.md for information only.
- Every new dependency, of every kind, is checked for existence, maintenance status, known vulnerabilities, license, whether it works with the runtime version and the other dependencies, and its supply chain (a look-alike name, the release date against the waiting period, a recent change of publishers, install scripts, provenance), and the result is recorded in "Check" (ADR 0054 in keyturn).
- "New" is "no" only for a dependency the project already has. A runtime library the stack profile suggests is still new the first time the project adds it, and needs the approval and the check.
Leave the section with "None." when there are none.
-->

| Name | Version | Kind | Purpose | Serves | New | Check |
|---|---|---|---|---|---|---|
| <name> | <version> | <runtime \| profile tool \| other tool> | <what it is used for> | R-<n> | <yes \| no> | <result of the dependency check, or "existing"> |

## Look

<!--
Required. How the screens are built to meet the requirements' "Look" section (ADR 0067 in keyturn).
- Without screens (the requirements say "Look baseline: none (no screens)"): write "None (no screens)." and nothing else.
- Requirements approved before their "Look" section existed: write "None: the requirements have no "Look" section." and nothing else
  (the question is under "Open questions").
- Look baseline and UI library: exactly as the requirements' "Look" says. A UI library is also listed under "Libraries and external services",
  with its kind and check; for "chosen by the architect", the one you chose.
- Styling method: with a stack profile whose README names styling methods, one it approves; otherwise one from the stack's documentation.
  A method that needs a package is a dependency like any other.
  It has an ADR, with the realistic options. When the client left the look to keyturn, the ADR records the best practice at that time
  for the stack, checked in its current documentation, with the date (also when the requirements' "Decided on" names a card answered that way).
- Token file: the one file that holds every token, inside "Areas the work may change". With a UI library, the library's theme takes
  its values from it.
- Checked widths: the phone and desktop widths at which the look's criteria are met; the developer builds for them and QA checks at them.
  Name the breakpoints too, if the layout changes at a width: the code may repeat them as literals, in media queries only.
- Tokens: every token, in four groups: spacing steps; type (families, sizes, line heights, weights); colors (text, background, borders,
  the focused control, and what the baseline adds); component shapes (control height, radius, borders, the focus outline).
  The developer writes the token file with exactly these tokens and values.
- How the look's criteria are met: one row per acceptance criterion of the look, with the tokens and the rule that meet it.
- The code uses the tokens for every spacing, type size, color, radius, control height, border width, and shadow; literal values
  of those kinds appear only in the token file (0, auto, inherit, and percentages are not such values). A token the code needs
  and this table lacks is a question for the design, not a value the developer picks; once implement has started,
  a design answer may add it, on the scale the tokens already have (ADR 0068 in keyturn).
-->

- Look baseline: <standard | worked out>, from the requirements' "Look"
- UI library: <none | name and version, see "Libraries and external services">
- Styling method: <for example, CSS Modules with the tokens as CSS custom properties>, see <link to the ADR>
- Token file: `<path>`
- Checked widths: phone <n> px, desktop <n> px<; breakpoint: <n> px, if any>

### Tokens

| Token | Value | Used for |
|---|---|---|
| `<name>` | <value> | <what it is used for> |

### How the look's criteria are met

| Criterion | How |
|---|---|
| AC-<n> | <the tokens and the rule that meet it> |

## Areas the work may change

<!--
The files and folders the developer may change, as paths or glob patterns relative to the repository root, one per row.
The gate compares the changed files with this list and flags anything outside it (phase 4). A change outside these areas needs an updated design first.
Never list the protected paths here: gate scripts, stack profiles, the CI jobs that run the gates, linter configs, conventions, and tests written by QA (the folders in "QA's tests").
-->

| Path | What changes | Serves |
|---|---|---|
| `<path or glob>` | <what changes there> | R-<n> |

## QA's tests

<!--
The folders where QA writes its tests, as glob patterns relative to the repository root, one per row. See ADR 0017 in keyturn's docs/adr/.
- Each is a folder of its own, outside every path in "Areas the work may change": the developer may not change QA's tests, and the gate checks this by path alone (phase 4).
  Never list one of these folders, or a path inside it, under "Areas the work may change".
- Use the folder name the stack profile sets. Without a profile, name a folder that the stack's test runner finds.
- The developer's own unit tests are not listed here: they stay next to the code, inside the developer's areas.
-->

| Path | What is tested there |
|---|---|
| `<folder>/**` | <for example, the API through HTTP, or the pages in a browser> |

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
