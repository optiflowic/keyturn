<!--
Template: threat model (internal). Filled in by the architect, with the design document. The security role checks the implementation against it.

- Always written in English.
- Think like an attacker, and like a user who misuses the deliverable: other users, people who are not signed in, and wrong or harmful input.
- Cover every case in the "Misuse" section of requirements.md.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Threat model: <name of what is being built>

Based on requirements version <n> and the design document: <link to design.md>.

## Summary

<!-- About three lines: what is worth attacking, where attacks can come from, and the most serious threats. -->

<summary>

## Assets

<!-- What an attacker could want or damage: data, accounts, credentials, money, availability, other people's systems. -->

| Asset | Why it matters |
|---|---|
| <asset> | <what happens if it is read, changed, or lost> |

## Entry points

<!--
Every way input reaches the deliverable: pages, API endpoints, command-line arguments, files, messages, webhooks, configuration.
"Who can reach it" says who can use it without any check: anyone, signed-in users, administrators, or only the local user.
-->

| Entry point | Who can reach it | Input it accepts |
|---|---|---|
| <entry point> | <who> | <input> |

## Threats

<!--
One heading per threat, numbered T-1, T-2, ... An ID is never changed or reused.
- "Misuse" is yes when the threat is a case from the "Misuse" section of requirements.md, whoever the actor is (another user, someone who is not signed in, or a user with harmful input).
- Severity is high, medium, or low. High-severity findings block delivery.
- Every threat needs a mitigation that is implemented, and a way to verify it:
  a QA test for an acceptance criterion (AC-n), a gate check, or the security review. Say which, and what exactly is checked.
- If a threat cannot be mitigated, or its mitigation leaves part of it open, stop and ask the client with a decision card, and record the answer here.
  The card offers mitigating it (with what that costs) or changing the requirement that creates it.
  Accepting the risk is an option only when the threat is low and could not let anyone get in, get more rights, or read, change, or delete data they should not,
  and does not come through a dependency or an external service. The security role confirms that it is low.
  Learning whether an account exists (from a sign-up or sign-in error, a password reset, a block, or response time) counts as reading data,
  so it is never accepted. It is not a threat only for an identifier the approved requirements make public on purpose, such as a unique username;
  then record that the entry point was considered and is public by requirement. A private identifier, such as an email address, is never public this way.
  Until the threat is mitigated or the client has accepted what is left, it blocks delivery.
- "Remaining risk" is what the mitigation does not cover: none, waiting for the client (with the card), or accepted (with the card and the date of the answer).
- "Status" is updated by the security role: planned, implemented, verified (with the finding that confirmed it), or accepted (the client accepted the whole risk, so nothing is implemented).
  A mitigation that is implemented only in part, with the rest accepted under "Remaining risk", gets the status of the part that is implemented (implemented or verified).
-->

### T-1: <short title>

- Entry point: <entry point>
- Asset: <asset>
- Misuse: <yes, from R-<n> | no>
- Severity: <high | medium | low>
- Status: <planned | implemented | verified: link to the finding | accepted: link to the decision card>
- Remaining risk: <none | waiting for the client: link to the decision card | accepted on <YYYY-MM-DD>: link to the decision card>

**Threat**: <who does what, and what they gain>

**Mitigation**: <what prevents it, where in the design it lives, and the requirement it comes from (R-n); or "None: the client accepted the risk.">

<!-- Delete the paragraph below when the remaining risk is none. -->

**What is left**: <what the mitigation does not prevent, and what could happen>

**How it is verified**: <AC-n | gate check: which | security review: what is checked | none: the client accepted the risk>

## Out of scope

<!-- Threats deliberately not covered, and why (for example, the hosting environment, which the client runs). Leave "None." when there are none. -->

- <threat>: <why it is out of scope>
