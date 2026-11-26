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

<!-- About three lines: what was delivered, how many "Must check" items there are, whether the screenshots under "The screens" show how the pages look, and about how long the check takes. -->

<summary>

## What you need to do

<!-- Only what the client must do now. Usually: look at the screenshots under "The screens", do the "Must check" items, record each result, and accept the delivery or report what failed. -->

> [!IMPORTANT]
> - <for example: do the 4 "Must check" items below (about 15 minutes), write the result of each, and tell us whether you accept the delivery>

## The screens

<!--
The screenshots QA took when it checked the look's criteria on the pages (ADR 0069 in keyturn's `docs/adr/`), from `keyturn/client/evidence/<task>/`, so the client can see how the pages look before opening the deliverable.
- "Covers" names the look's criteria that QA checked on these screens and passed (the test report marks them `pass`), with their requirements. Those criteria are not checks the client does by hand. A look criterion that the test report marks `not tested` or `partly tested` is a check below instead, and is not named here.
- One heading per page, in the order a person meets them. Under it, each screenshot as an image, with a short caption that says the width (for example, "On a phone (360 px wide)", "On a computer (1280 px wide)", "With the Tab key on the first field"). Link the images with a relative path from this file (for example, `evidence/<task>/<page>-<width>.png`).
- Say in one or two lines what QA checked on them, in plain words, and that the client may look at the pages themselves too.
- "Result" is filled in by the client, from the screenshots: as expected, or not as expected with what they see. A screenshot that is not as expected is reported as a failed check is.
Leave the section with "No screens in this delivery." when the deliverable has none, or when QA checked none of the look's criteria (then they are checks below).
-->

- Covers: AC-<n> (R-<n>)
- Result: <as expected | not as expected: what you see>

<what QA checked on these screens, in plain words>

### <page>

![<page> on a phone (<width> px wide)](evidence/<task>/<page>-<width>.png)

![<page> on a computer (<width> px wide)](evidence/<task>/<page>-<width>.png)

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
- Every acceptance criterion in this delivery appears in exactly one check, here or under "Optional", or under "The screens" when QA checked it on the screens and it passed. Removed criteria are left out.
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
