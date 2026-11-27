<!--
Template: test report (client-facing). Filled in by the PM at delivery, from QA's test report (keyturn/internal/test-report.md), the screenshots it names, and the gate's log (ADR 0070 in keyturn's `docs/adr/`).

- Write for a client who does not read code: no code, no test names, no file paths other than the images, and no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, AC-n) exactly as it is, in every language.
- Report only what QA's test report and the gate's log show. Never write a criterion as checked when QA's report does not say it was, and never add steps or observations of your own.
- The client writes nothing in this document: what they find goes into their answer about the delivery.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Test report: <name of what is being delivered>

Based on requirements version <n>. Acceptance guide: <link to acceptance-guide.md>. Delivery report: <link to delivery-report.md>.

## Summary

<!-- About three lines: how many acceptance criteria were checked and passed, how many could not be checked (and that the acceptance guide asks you to check them), and the most important thing that was not checked. -->

<summary>

## What you need to do

<!-- Only what the client must do now. Usually: read this report, look at the screenshots, and answer in the acceptance guide. Nothing here needs to be run. -->

> [!IMPORTANT]
> - <for example: read how each criterion was checked and look at the screenshots (about 20 minutes). You do not need to run anything. If something is not as you expect, say so when you answer the acceptance guide>

## How we tested

<!--
In a few lines, in plain words:
- who tested: an independent tester who wrote the tests from the requirements only, without seeing the code;
- what was tested: the version (the tested commit's short hash) and the date, from QA's report;
- how: the deliverable was started and used as a person uses it (for screens, in a real web browser, named with its version from QA's report, at the widths it gives), plus tests through the deliverable's other interfaces where QA's report has them;
- the automated checks: the tests ran again, with the code style checks, on the final version (from the gate's log), and the result.
-->

<how we tested>

## Results

<!--
One row per acceptance criterion of a requirement in this delivery that is not removed, in order.
- "Result" is one of: passed, failed, partly checked, not checked (QA's pass, fail, partly tested, not tested), in the document language.
- "Evidence" links to the criterion's heading below, and names its screenshots, or says "what we observed" when there are none.
A criterion of a requirement outside this delivery is not listed here; say in "Summary" which requirements come in a later delivery.
-->

| Requirement | Criterion | Result | Evidence |
|---|---|---|---|
| R-<n>: <short title> | AC-<n>: <short title> | <passed \| failed \| partly checked \| not checked> | <link to the criterion below> |

## How each criterion was checked

<!--
One heading per criterion in "Results", in the same order, from "Checks" in QA's test report.
- "How we checked it": the steps the tester's checks follow, numbered, as a person would do them, in plain words (from QA's "Steps").
- "What we saw": what the checks observed, in plain words (from QA's "Observed"): the text a page showed, or what the deliverable answered where no screen shows it.
- The screenshots QA's report names for the criterion, as images, each with a caption that says what it shows and at which width. Link them with a relative path from this file (for example, `evidence/<task>/ac-<n>-<what>.png`).
- For a look criterion, what was measured and what the tester judged from the screenshots, in plain words, and a link to "The screens" instead of repeating the images.
- For a criterion "partly checked" or "not checked": what was not checked and why, and the acceptance guide's check that asks you to check it, or what you can do when it needs what comes after the delivery.
-->

### AC-<n>: <short title>

- Covers: R-<n>
- Result: <passed | failed | partly checked | not checked>

How we checked it:

1. <what the tester's check did>

What we saw: <what the check observed>

![<what the screenshot shows> (<width> px wide)](evidence/<task>/ac-<n>-<what>.png)

## The screens

<!--
The screenshots QA took when it checked the look's criteria on the pages (ADR 0069 in keyturn's `docs/adr/`), from `keyturn/client/evidence/<task>/`, so the client can see how the pages look before opening the deliverable.
- One heading per page, in the order a person meets them. Under it, each screenshot as an image, with a short caption that says the width (for example, "On a phone (360 px wide)", "On a computer (1280 px wide)", "With the Tab key on the first field").
- Say in one or two lines what QA checked on them, in plain words, and which criteria they are evidence for.
Leave the section with "No screens in this delivery." when the deliverable has none, or with what QA's report says when the look was not checked.
-->

<what the tester checked on these screens, in plain words>

### <page>

![<page> on a phone (<width> px wide)](evidence/<task>/<page>-<width>.png)

![<page> on a computer (<width> px wide)](evidence/<task>/<page>-<width>.png)

## What we did not check

<!--
Everything QA's report lists under "Untested areas" that concerns this delivery, in plain words, and why:
- a criterion "partly checked" or "not checked", with the acceptance guide's check that asks you to check it;
- what needs what comes after the delivery (for example, your own server), with what you can do then;
- what the checks did not cover (for example, other web browsers), when a reader could assume it was checked.
Requirements outside this delivery are named in "Summary", not here.
Leave "None." only when QA's report lists nothing for this delivery.
-->

- <what was not checked>: <why, and what you can do>
