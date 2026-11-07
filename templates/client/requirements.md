<!--
Template: requirements (client-facing). Filled in by the PM.

- Write for a client who does not read code: no code, no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, AC-n) exactly as it is, in every language.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Requirements: <name of what is being built>

Status: <draft | waiting for approval | approved>

## Summary

<!-- About three lines: what will be built, for whom, and how the client will know it works. -->

<summary>

## What you need to do

<!-- Only what the client must do or decide now. Leave the list empty, with "Nothing right now.", when there is nothing. -->

> [!IMPORTANT]
> - <for example: read R-1 to R-6 and AC-1 to AC-9, check the priority of each requirement, and approve them, or tell us what to change>

## Background

<!-- Why this is needed and who will use it. A few sentences. -->

<background>

## Requirements

<!--
One heading per requirement: what the deliverable does, in one or two sentences.
- Number in order (R-1, R-2, ...). An ID is never changed or reused.
- Give each requirement a priority: Must or Nice to have. You only propose it; the client decides it when approving. Keep "Must" for what the deliverable is useless without.
  Never lower the priority of a needed requirement to reduce the number of checks. If one delivery would have too many "Must check" items, split the delivery instead.
- To remove a requirement, keep it, add "(removed)" to its heading, and replace the text with when and why it was removed.
-->

### R-1: <short title>

Priority: <Must | Nice to have>

<what the deliverable does>

## Acceptance criteria

<!--
One heading per check that decides whether a requirement is met.
- Each criterion covers at least one requirement, and every requirement that is not removed is covered by at least one criterion.
- The expected result must be something a person can observe, not "works correctly".
- Numbering follows the same rules as requirements.
- To remove a criterion, keep it, add "(removed)" to its heading, keep the Covers line, and replace the other lines with when and why it was removed.
-->

### AC-1: <short title>

- Covers: R-1
- When: <what the user does, or the situation>
- Expected result: <what the user sees or what happens>

## Misuse

<!--
How the deliverable could be misused or attacked, and the requirement that prevents it.
Think about other users, people who are not signed in, and wrong or harmful input.
Every entry names at least one requirement. If none prevents it, add a requirement.
If the deliverable can act on systems or data that are not the user's own (for example, a vulnerability scanner),
it must only act on targets the user is authorized to use, checked before it acts (for example, by verifying domain ownership).
Add this as a requirement.
-->

- <how it could be misused>: prevented by R-<n>

## Out of scope

<!-- What this work will not do, so there is no surprise at delivery. -->

- <what is not included>

## Changelog

<!-- One row per approved version. Version 1 is the first one the client approves. -->

| Version | Date | Change |
|---|---|---|
| 1 | <YYYY-MM-DD> | First version |
