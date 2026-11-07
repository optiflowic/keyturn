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
- If a threat cannot be mitigated, stop and ask the client with a decision card. Record the answer here,
  and list the threat under "Remaining risks" in the delivery report.
- "Status" is updated by the security role: planned, implemented, or verified (with the finding that confirmed it).
-->

### T-1: <short title>

- Entry point: <entry point>
- Asset: <asset>
- Misuse: <yes, from R-<n> | no>
- Severity: <high | medium | low>
- Status: <planned | implemented | verified: link to the finding>

**Threat**: <who does what, and what they gain>

**Mitigation**: <what prevents it, where in the design it lives, and the requirement it comes from (R-n)>

**How it is verified**: <AC-n | gate check: which | security review: what is checked>

## Out of scope

<!-- Threats deliberately not covered, and why (for example, the hosting environment, which the client runs). Leave "None." when there are none. -->

- <threat>: <why it is out of scope>
