<!--
Template: acceptance guide (client-facing). Filled in by the PM at delivery, from requirements.md.

- Write for a client who does not read code: no code, no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, AC-n) exactly as it is, in every language.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Acceptance guide: <name of what is being delivered>

Based on requirements version <n>. Delivery report: <link to delivery-report.md>.

## Summary

<!-- About three lines: what was delivered, how many "Must check" items there are, and about how long the check takes. -->

<summary>

## What you need to do

<!-- Only what the client must do now. Usually: do the "Must check" items, record each result, and accept the delivery or report what failed. -->

> [!IMPORTANT]
> - <for example: do the 4 "Must check" items below (about 15 minutes), write the result of each, and tell us whether you accept the delivery>

## Before you start

<!--
What the client needs before the first check, in numbered steps: how to open or start the deliverable, test accounts, sample data.
Never write a real password or secret here; say where to find it instead.
Leave the section with "Nothing to prepare." when there is nothing.
-->

1. <step>

## Must check

<!--
One heading per check, in priority order: the check whose failure would hurt the client most comes first.
- The acceptance criteria of every Must requirement in this delivery are "Must check". A check that covers a Must requirement is "Must check", even if it also covers a Nice to have one.
- Every acceptance criterion in this delivery appears in exactly one check, here or under "Optional". Removed criteria are left out.
- One check can cover several acceptance criteria only when the same steps check all of them. Never combine unrelated checks to stay under the limit.
- Keep "Must check" items to about five. If a delivery needs more, it is too big: split it into smaller deliveries.
  Never move a Must requirement's criterion to "Optional" to stay under the limit.
- Steps are things the client does and sees, numbered, one action per step.
- The expected result must be something the client can observe, not "works correctly".
- "Result" is filled in by the client: pass, fail (with what happened), or not checked.
-->

### Check 1: <short title>

- Covers: AC-<n> (R-<n>)
- Result: <pass | fail: what happened | not checked>

Steps:

1. <what the client does>

Expected result: <what the client sees or what happens>

## Optional

<!--
Checks for the acceptance criteria of Nice to have requirements, in the same format as "Must check".
The client may skip them; a skipped check does not block acceptance.
Leave the section with "None." when there are none.
-->

### Check <n>: <short title>

- Covers: AC-<n> (R-<n>)
- Result: <pass | fail: what happened | not checked>

Steps:

1. <what the client does>

Expected result: <what the client sees or what happens>

## If a check fails

<!-- How to report a failure and what happens next. Keep it to a few lines. -->

<for example: write what you did and what you saw in the "Result" line, and tell us. We fix it and send you only the checks affected by the fix.>
