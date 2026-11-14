<!--
Template: test report (internal). Filled in by QA, from requirements.md and the test results.

- Always written in English.
- QA writes tests from the requirements only, never from the implementation or the developer's notes.
- Every acceptance criterion that is not removed gets a row in "Results", even if it was not tested.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Test report: <task or issue>

- Specification: <requirements version <n> | none>
- Tested commit: <branch> at <commit>
- Date: <YYYY-MM-DD>

<!--
When QA ran without a specification, keep this note and delete the line above it that names a version.
Otherwise delete the note.
-->

> [!WARNING]
> No specification was available. These tests treat the current behavior as correct: they show what the deliverable does, not what it should do.

## Summary

<!-- About three lines: how many acceptance criteria pass, fail, were partly tested, or were not tested, and the most important failure. -->

<summary>

## Results

<!--
One row per acceptance criterion that is not removed.
- Result is pass, fail, partly tested (tests ran and passed for only part of the expected result), or not tested. A "partly tested" or "not tested" row is also listed under "Untested areas" with what was not tested and why.
- "Tests" says where the tests for the criterion are (files or test names). QA's tests are only in the folders listed under "QA's tests" in design.md.
Without a specification, use one row per observed behavior instead, with a short name in place of the AC-n ID.
-->

| Criterion | Covers | Result | Tests |
|---|---|---|---|
| AC-<n> | R-<n> | <pass \| fail \| partly tested \| not tested> | `<test file or name>` |

## Failures

<!-- One heading per failed criterion: what was done, what was expected, and what happened. Leave "None." when nothing failed. -->

### AC-<n>: <short title>

- Steps: <what the test does>
- Expected: <from the acceptance criterion>
- Actual: <what happened>

## Untested areas

<!--
Everything that was not tested, and why: criteria that cannot be tested automatically (these go to the client's acceptance guide or the security review),
missing test environments, and behavior outside the acceptance criteria.
Leave "None." only when every criterion was tested.
-->

- <what was not tested>: <why>

## Test counts

<!-- Used by the gate to detect dropped tests or coverage (phase 4). Leave a value as "not measured" if the stack cannot measure it. -->

- Tests: <number, then by runner in parentheses if more than one>
- Skipped or disabled tests: <number, and which>
- Coverage: <percentage | not measured>
