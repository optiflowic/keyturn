<!--
Template: review findings (internal). Filled in by the reviewer, or by the security role.

- Always written in English.
- Report findings; do not fix the code. The developer fixes what is reported.
- The reviewer covers design fit, readability, and conventions, and flags changes that contradict an accepted ADR.
- The security role covers what scanners miss and fills in the "Security" section. Delete that section in a reviewer's report.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# <Review | Security review>: <task or issue>

- Reviewed by: <reviewer | security>
- Reviewed change: <base commit>..<head commit>
- Compared against: <the documents used, with links: design.md, conventions.md, threat-model.md, ADRs>

<!--
List any input document that was missing and what the review did instead,
for example: "No design document: reviewed the diff for readability and conventions only."
Delete the line below when nothing was missing.
-->

Missing inputs: <document>: <what was reviewed instead>

## Summary

<!-- About three lines: the number of findings by severity, and whether any blocks delivery. -->

<summary>

## Findings

<!--
One heading per finding, numbered F-1, F-2, ... within this report.
- Location: a file and line (or range), or the design part it concerns.
- Severity: high, medium, or low. High-severity findings block delivery like a failing gate.
- Category: design fit, readability, conventions, ADR conflict, or security.
- Say what is wrong and what is expected, with the rule, requirement, ADR, or threat it is based on. Do not write the fix.
- Status is updated when the developer has fixed it and the reviewer has checked the fix: open or fixed.
Leave the section with "None." when there are no findings.
-->

### F-1: <short title>

- Location: `<file>:<line>`
- Severity: <high | medium | low>
- Category: <design fit | readability | conventions | ADR conflict | security>
- Based on: <rule, R-n, ADR, or T-n>
- Status: <open | fixed>

<what is wrong, and what is expected>

## Security

<!-- Filled in by the security role only. -->

### Threat model check

<!--
One row per threat in threat-model.md: is the mitigation implemented, and what evidence shows it (a test, a code location, a manual check).
"Remaining risk" is copied from the threat model: none, waiting for the client, or accepted (with the decision card).
A threat whose mitigation is not implemented, or only partly, is a high-severity finding above, unless the client accepted what is left on an answered decision card.
Before counting a risk as accepted, check all of these:
- the threat is low, could not let anyone get in, get more rights, or read, change, or delete data they should not, and does not come through a dependency or an external service;
- the card offered mitigating the threat as one of the options, and described the same risk that is left now;
- the threat, its severity, and the requirement it comes from have not changed since the client answered.
If any of these does not hold, the acceptance does not count: report a high-severity finding, and a new card is needed.
A card that is still waiting does not count as accepted.
-->

| Threat | Mitigation implemented | Remaining risk | Evidence |
|---|---|---|---|
| T-<n> | <yes \| no \| partly> | <none \| waiting: card \| accepted: card> | <evidence> |

### Scan triage

<!--
One row per finding from the gate's scans (SAST, dependency, secret scanning).
- Triage is real or false positive. Only the security role may mark a false positive, and the reason is required.
- A real finding is also listed under "Findings" above, with its severity.
Leave "No scan findings." when the scans ran and found nothing.
When a scan did not run (for example, before the gate has it), add a row for it with "did not run" under "Triage" and the reason, so it is never read as clean.
-->

| Tool | Finding | Location | Triage | Reason |
|---|---|---|---|---|
| <tool> | <rule or ID> | `<file>:<line>` | <real \| false positive \| did not run> | <why: required for a false positive or a scan that did not run> |
