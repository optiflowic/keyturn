<!--
Template: acceptance guide (client-facing). Filled in by the PM at delivery, from requirements.md and QA's test report.

- Write for a client who does not read code: no code, no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, AC-n) exactly as it is, in every language.
- The team that built the deliverable checked it; the test report shows how, with the evidence. This guide never asks the client to repeat a check QA ran and passed: it asks only for what QA could not check (ADR 0070 in keyturn's `docs/adr/`).
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Acceptance guide: <name of what is being delivered>

Based on requirements version <n>. Test report: <link to test-report.md>. Delivery report: <link to delivery-report.md>.

## Summary

<!-- About three lines: what was delivered, that our tester checked it and the test report shows how, how many checks we ask of you (often none), and about how long reading and checking take. -->

<summary>

## What you need to do

<!-- Only what the client must do now. Usually: read the test report, do the checks we ask of you (if any), and tell us whether you accept the delivery. Trying the deliverable yourself is optional. -->

> [!IMPORTANT]
> - <for example: read the test report (about 20 minutes), do the 1 check below (about 5 minutes), and tell us in your own words whether you accept the delivery>

## Checks we ask of you

<!--
Only the acceptance criteria that QA's test report marks `not tested` or `partly tested`, when the client can check them before accepting. A criterion that needs what comes after the delivery (for example, the client's own server) is not a check here: the test report and the delivery report say what was not checked and what the client can do.
- One heading per check, the checks of Must requirements first. One check can cover several criteria only when the same steps check all of them.
- "Why we ask you" says, in plain words, why our tester could not check it (from QA's "Untested areas"), and for "partly tested", which part the tester checked.
- "Priority" is the requirement's approved priority. A check of a Nice to have requirement may be skipped; a skipped check does not block acceptance.
- Steps are things the client does and sees, numbered, one action per step. The expected result must be something the client can observe, not "works correctly".
- "Result" is filled in by the client: pass, fail (with what happened), or not checked.
Leave the section with "None: our tester checked every acceptance criterion of this delivery. The test report shows how." when there is none.
-->

### Check 1: <short title>

- Covers: AC-<n> (R-<n>)
- Priority: <Must | Nice to have>
- Why we ask you: <why our tester could not check it>
- Result: <pass | fail: what happened | not checked>

Steps:

1. <what the client does>

Expected result: <what the client sees or what happens>

## Before you start

<!--
What the client needs to open the deliverable, for the checks above and for trying it: how to open or start it, test accounts, sample data, in numbered steps.
Never write a real password or secret here; say where to find it instead.
Leave the section with "Nothing to prepare." when there is nothing.
-->

1. <step>

## Try it yourself (optional)

<!--
What the client may want to try on their own, free and optional, with nothing to record: the main screens or commands of this delivery, how to reach each, and one or two things to try on each, in a short list.
Say that anything that is not as they expect goes into their answer.
Leave the section with "Nothing to try in this delivery." when the deliverable has nothing the client can open.
-->

- <screen or command>: <how to reach it, and what to try>

## If something is wrong

<!-- How to report a failed check, or anything not as expected in the test report or when trying it, and what happens next. Keep it to a few lines. -->

<for example: tell us what you did and what you saw, in your own words, when you answer. We fix it, check it again, and send you the new test report.>
