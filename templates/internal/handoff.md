<!--
Template: handoff notes (internal). Filled in by the developer when handing work to the next role.

- Always written in English.
- State facts: what changed, what is covered, what is left, and how to run it. Do not explain why the code is correct or what should be tested.
- QA and security never see the developer's reasoning. When the next role is QA or security, give them only "How to run".
  QA writes tests from the requirements, never from the implementation.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Handoff: <task or issue>

- From: <role>
- To: <role>
- Based on requirements version <n> and the design document: <link to design.md>
- Branch and commit: <branch> at <commit>

## Summary

<!-- About three lines: what was done, and whether anything is left. -->

<summary>

## What was done

<!--
The changes, grouped by part of the design, with the requirements each serves.
Every changed path is inside "Areas the work may change" in the design; this file is the developer's own output and the only exception.
A change outside the areas is not made: the developer stops and asks for the design to be updated first, and lists what waits under "What is left".
-->

- <part>: <what changed> (R-<n>)

## Requirements covered

<!-- One row per requirement in this task. Status is done, partly done, or not started. Explain anything other than done in "Notes". -->

| Requirement | Status | Notes |
|---|---|---|
| R-<n> | <done \| partly done \| not started> | <notes> |

## What is left

<!-- Work not done in this handoff, and why (for example, blocked by an open question). Leave "Nothing." when nothing is left. -->

- <what is left>: <why>

## How to run

<!--
Everything the next role needs to build, start, and test the deliverable: commands, configuration, test accounts, sample data.
Never write a real secret here; say where to find it.
This is the only section given to QA and security.
-->

1. <step>

## Notes for the next role

<!--
Facts the next role must know: open questions, decision cards waiting for the client, deviations from the design (with the ADR that allows them),
new dependencies, and any guardrail triggered. Not given to QA or security.
Leave "None." when there is nothing.
-->

- <note>
