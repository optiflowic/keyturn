# 0016. Learning whether an account exists counts as reading data

- Status: accepted
- Date: 2026-11-11

## Context

[ADR 0010](0010-accepting-the-risk-of-a-low-threat.md) lets the client accept the risk of a low threat on a decision card, except a threat that could let someone get in, get more rights, or read, change, or delete data they should not, or that comes through a dependency or an external service. Those are never accepted: they are mitigated, or the requirement that creates them is changed.

An independent run of the `design` skill could not tell whether learning that an email address has an account is "reading data". Someone can learn it from a sign-up error ("this email is already used"), a sign-in error that differs for an unknown email and a wrong password, a password reset, a block after wrong passwords that only happens to real accounts, or a difference in response time. The answer decides whether the client may accept that risk, and the `design` and `security-review` skills (phase 3) need it.

What constrains the answer:

- The line in ADR 0010 is drawn by harm, and the security role judges the harm. A rule that needs a fresh judgment for each service is made by an AI each time.
- What an account's existence reveals depends on the service: little for a to-do list, a lot for a clinic or a support group. A mistake in that judgment falls on the side of accepting the risk.
- The usual mitigations are cheap: the same message whatever the reason, and responses that take the same time.

## Options considered

1. **It counts as reading data someone should not read.** Its risk is never accepted: it is mitigated, or the requirement that creates it is changed. The same rule for every service, and no judgment of sensitivity; the cost is that some services must mitigate a threat that would have mattered little to them.
2. **It does not count as reading data.** It may be accepted on a decision card when it is low, like any other threat. Fewer mitigations and requirement changes, but services where existence is sensitive rely on the severity being judged right.
3. **It depends on what existence reveals for the service**, judged by the security role. Fits each service, but it is the per-service judgment by an AI that the constraints warn against, and a wrong call accepts the risk.

## Decision

Option 1: learning whether an account exists counts as reading data someone should not read, under ADR 0010, so its risk is never accepted. It is not a threat only for an identifier that the approved requirements make public on purpose, such as a username chosen to be unique or a public profile: telling someone that such a username is taken is what the requirements ask for. The exception never covers a private identifier: a public profile does not make the email address behind it public, so revealing that an email address has an account is still a threat. This clarifies ADR 0010 and does not supersede it.

## Reasons

- A rule of "it depends on how sensitive the service is" would mean an AI judges importance each time, and a mistake falls on the side of accepting the risk. One rule for every service leaves nothing to judge.
- The usual mitigations are cheap: the same error message whatever the cause, and responses that take the same time (for example, checking a password hash even when the email is unknown). Requiring them costs little where existence matters little.
- The exception keeps the rule from fighting the requirements: when the client approved making accounts visible, there is nothing left to hide.

## Consequences

- `docs/DESIGN.md` "Security", `templates/internal/threat-model.md`, and `templates/internal/review.md` state the rule and its exception where they list the threats that are never accepted.
- The architect lists learning whether an account exists as a threat for every entry point that can reveal it (sign-up, sign-in, password reset, and any block after wrong passwords), unless the approved requirements make the identifier it reveals public on purpose; then the threat model records that it was considered and is public by requirement.
- Sign-up with unique email addresses is the hard case. A sign-up form that says "this email is already used" reveals existence, and a response that is the same whatever the cause usually needs a confirmation email: the result is sent by email, not shown on the page. That is a new external service, which needs the client's approval, or else a requirement change (for example, sign-up by invitation, or signing in with a username instead of an email address). The architect raises it with the client when the requirements are written or the design is made, not after delivery.
- The worked example in `evals/requests/task-manager/example/` signs people in with a username instead of an email address, so that usernames are public by requirement, and its threat model records that each entry point was considered (#83).
- The `design` and `security-review` skills (phase 3) follow the rule: they never offer accepting this risk on a decision card.
