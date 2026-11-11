<!--
Template: conventions (internal). Filled in by the standards role, from the stack profile and the design document.

- Always written in English.
- Anything a tool can check is a tool rule, in a config file the gate runs. Only what no tool can check goes into the reviewer checklist.
- This file and every file under "Tool rules" are protected: the developer never changes them. They change only through an ADR in internal/adr/, listed under "Changes".
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Conventions: <name of what is being built>

Based on the design document: [design.md](design.md) (requirements version <n>).

- Stack profile: <profile name | No profile: see "Assumed defaults">
- Changed only by: an ADR in <link to adr/>, listed under "Changes". The developer does not change this file or the files under "Tool rules".

## Summary

<!-- About three lines: the tools that check the code, and what the reviewer checks by hand. -->

<summary>

## Tool rules

<!--
One row per config file, or per tool that needs no file (write "none" in "File").
- "What it enforces": the rules that matter for this project, in short: the formatter, the lint rule sets, the limits
  (complexity, function length, nesting), the boundaries between parts, and the patterns forbidden by the design or the threat model.
- "Based on": where the rule comes from: the stack profile, an assumed default, a design part, a T-n, or an ADR.
Every rule fails the check; a rule that only warns is not a rule.
-->

| File | Tool | What it enforces | Based on |
|---|---|---|---|
| `<path>` | <tool> | <rules> | <profile \| assumed default \| design "<part>" \| T-n \| ADR> |

## Reviewer checklist

<!--
Only what no tool can check: the quality of names, whether comments explain why, unused abstractions, and whether the code sits in the part the design says.
One row per check, numbered C-1, C-2, ... Never change or reuse a number; mark a removed check "(removed)" and say which ADR removed it.
"Why no tool checks it" says why it cannot be a tool rule. If a tool can check part of it, the tool rule covers that part, and the row says what is left.
-->

| ID | Check | Why no tool checks it |
|---|---|---|
| C-<n> | <what the reviewer looks for> | <reason> |

## Assumed defaults

<!--
When there is no stack profile, every tool and limit chosen without one, so a later profile can replace them.
Write "None: every default comes from the stack profile." when a profile was used.
-->

- <default>: <what was assumed, and why>

## Changes

<!-- One row per version. The first version has no ADR; every later change has one. -->

| Date | ADR | What changed |
|---|---|---|
| <YYYY-MM-DD> | <none (first version) \| link to the ADR> | <what changed> |
