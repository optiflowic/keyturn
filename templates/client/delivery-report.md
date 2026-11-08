<!--
Template: delivery report (client-facing). Filled in by the PM at delivery, from the gate logs, the test report, and the security and review findings.

- Write for a client who does not read code: no code, no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, AC-n) exactly as it is, in every language.
- Report only what the records show. If something was not checked, say so under "What was not verified"; never write it as verified.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Delivery report: <name of what is being delivered>

Based on requirements version <n>. Acceptance guide: <link to acceptance-guide.md>.

## Summary

<!-- About three lines: what was delivered, whether every check passed, and the most important thing that was not verified or remains a risk. -->

<summary>

## What you need to do

<!-- Only what the client must do or decide now. Usually: do the acceptance check, and decide whether the remaining risks are acceptable. -->

> [!IMPORTANT]
> - <for example: do the "Must check" items in the acceptance guide, read "Remaining risks", and accept the delivery or tell us what to change>

## What was delivered

<!--
One row per requirement in this delivery. Removed requirements are left out.
- Status is "delivered", "partly delivered", or "not delivered". Explain anything other than "delivered" in "Notes".
- "Covered by" lists the acceptance criteria that cover the requirement. Whether each one was tested is in "What was verified" and "What was not verified".
-->

| Requirement | Status | Covered by | Notes |
|---|---|---|---|
| R-<n>: <short title> | <delivered \| partly delivered \| not delivered> | AC-<n> | <notes> |

## What was verified

<!--
One row per kind of check that ran. Use these rows, and add others only if they ran.
Name who did each check in plain words, as in the rows below, not with internal role names:
- Automated checks (the gate): the mechanical checks (tests, lint, formatting, and, where the stack profile has them, scans for known vulnerability patterns, vulnerable dependencies, and leaked secrets).
- Independent tester (QA): tests written from the requirements only, never from the code.
- Security reviewer: a review from an attacker's point of view, against the threat model.
- Code reviewer: design fit, readability, and conventions.
"How" says, in plain language, how the check was done. "Result" says what passed and what was found and fixed. "Details" links to the internal record.
-->

| Check | Done by | How | Result | Details |
|---|---|---|---|---|
| <what was checked> | Automated checks | <for example: ran the automated tests, the code style checks, and a scan for leaked passwords> | <result> | <link to the gate log> |
| Behavior matches the requirements | Independent tester | <for example: automated tests written from the requirements only, one or more per acceptance criterion> | <for example: all 9 acceptance criteria pass> | <link to the test report> |
| Security issues tools cannot find | Security reviewer | <for example: tried to reach another user's data and checked every threat in the threat model> | <result> | <link to the security findings> |
| The code follows the design and is easy to maintain | Code reviewer | <for example: read the changes against the design and the coding conventions> | <result> | <link to the review findings> |

## What was not verified

<!--
Everything that was not checked, and why: checks the stack profile cannot run, a stack without a profile (gate coverage is limited),
acceptance criteria QA could not test, threats without a verified mitigation, and checks that only the client can do by hand.
Never leave this section empty: if everything listed in the stack profile ran, say what the profile itself cannot check.
-->

- <what was not verified>: <why>

## Remaining risks

<!--
Problems that are known but not fixed, and risks that follow from "What was not verified".
For each: what could happen, how likely and how serious it is in plain words, and what the client can do about it.
Leave the section with "None known." only when there is nothing to report.
-->

- <risk>: <what could happen>. <what you can do>

## Guardrails triggered

<!--
Every safety guardrail that stopped or flagged something during the task, and how it was resolved:
for example, a change outside the approved scope, an attempt to weaken a check, the rework limit, or a budget limit.
Leave the section with "None." when nothing was triggered.
-->

- <what was triggered>: <how it was resolved>

## Models and tools used

<!-- The AI models and tool versions used, so the delivery can be traced and repeated. -->

| Used for | Model or tool | Version |
|---|---|---|
| <role or check> | <name> | <version> |
