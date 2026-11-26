# 0066. The requirements have a required "Look" section, and `spec` asks the client about the look once

- Status: accepted
- Date: 2026-11-26
- Supersedes: in [0032](0032-gate-base-is-where-the-task-branch-left.md), what a `spec` commit may change: it may also change the decision cards

## Context

In the rehearsal (#63, task `delivery-2`), the client did not accept the delivery: the web part had no styling at all, so labels stuck to their inputs and buttons were in no order. The requirements said nothing about the look, so every role passed the screens as long as they worked, and nothing gave the client a criterion to judge them by before delivery. A client who does not read code judges a deliverable by its screens, so this is a gap in keyturn, not in that request.

What constrains the answer:

- The client's attention is limited: questions are sent together, each on a short decision card, and a question is asked only when it matters ("Client attention budget" in `docs/design/documents.md`).
- `spec` proposes the most likely answer as a requirement and asks a separate question only when no reasonable proposal exists. How far the look is worked out, and whether a UI library is used, depend on the client's taste and change what they get, so they are the client's to decide; but the client may leave them to keyturn.
- Once a version of `requirements.md` is sent, it is never changed (ADR 0008). An answer that changes the requirements needs a new version and a new approval.
- A UI library is a direct dependency and goes through the same checks as any other ("Guardrails" 3, ADR 0015, ADR 0018).
- Later work builds on this question: approving a mockup before building (#197), a designer role (#198), and choosing the team at the start (#199).

## Options considered

1. **Leave the look to the request.** Nothing changes; a request that says nothing about the look gets screens nobody checked, as in the rehearsal.
2. **Always write a fixed "tidy minimum" into the requirements, without asking.** No question for the client, but how far the look goes, and whether a UI library is used, are decided for them.
3. **A required "Look" section, and one question on a decision card, sent with the first version.** The section always holds checkable criteria for a tidy minimum; the card asks how far the look is worked out and whether a UI library is used, with a recommendation; the first version proposes the recommendation.
4. **The same, but the card is sent first and the requirements only after its answer.** The requirements then say from the start what the client chose, but every project with screens gets one more exchange with the client before the first version.
5. **The same as 3, but the requirements are always sent again after the card's answer**, so that a version records the answer. Every project with screens gets a second approval round.

## Decision

Option 3.

- `templates/client/requirements.md` has a required "Look" section, after "Misuse". It has three fields and a line that names the requirements holding the look's criteria; a deliverable without screens has only the first field and a sentence:
  - **Look baseline**: `standard` (a tidy minimum) or `worked out` (worked out further), or `none (no screens)` for a deliverable without screens, which then says so in the section and needs no card. #197 adds the value `approved look: <reference and hash>`.
  - **UI library**: `none`, the name of the library the client chose, or `chosen by the architect`, when the client wants one and leaves which to keyturn: the stack is chosen only in the design, so the architect chooses the library for it, and the client agrees to it in the design summary, as to any runtime dependency.
  - **Decided on**: the decision card that asks the question, and, once it is answered, what the client chose or that they left it to keyturn.
- The look's criteria are requirements and acceptance criteria like any other (`R-n`, `AC-n`, Must), so that every role and every check that goes through the requirements covers them. They always include the tidy minimum, for example: each label sits next to or above its input, with space between them; buttons with the same role have the same size and line up; no horizontal scroll at phone width; a focused control is visibly marked. A `worked out` baseline, or a UI library, adds what it brings, as criteria a person can check.
- When the deliverable has screens, `spec` asks the client once, on one decision card with a recommendation, whether or not the request mentions the look: how far the look is worked out (the tidy minimum, or further), and whether a UI library is used, and if so which one. It sends the card with the first version of the requirements, in the same message. That version proposes the recommended answer in the section and links the card. "Leave it to you" is a valid answer: keyturn takes the recommendation, which is the best practice at that time for the deliverable, and the card records that the client left it to keyturn.
- When the client's answer is the recommendation, or leaves it to keyturn, the version they approve stands: its `Decided on: our proposal; decision card <n> decides it`, with the card answered that way, reads as decided as proposed, and the next version, if any, writes the answer in. When it is another option, the version sent does not say what the client chose: `spec` records that version as not approved, with the card's answer as the change, even when the client also wrote that they approve it, as the version's "What you need to do" tells them, and writes a new version with it.
- The question is asked once per project. A later change to requirements that already have a "Look baseline" does not ask again, unless the client asks to change the look. Requirements written before this section existed get it, and the card, with their next version.
- A commit `deliver` names as `spec` may also change the decision cards, `keyturn/client/decision-card-<n>.md`, besides what ADR 0032 lists, since `spec` commits the card about the look with the requirements and records the client's answer on it. `deliver` lists a commit that changes only that card, while a document step is current, as `spec`.
- When the client does not name the look's details, the recommendation needs no stack: the tidy minimum without a UI library, or a UI library `chosen by the architect`. A UI library the client names, or that the architect chooses, is a runtime dependency: `spec` records the choice, and `design` takes it, or chooses it, and checks it as any other. When it fails the check, the choice goes back to the client on a card, and a change to it is a change to the requirements.

## Reasons

- The client gets criteria to judge the screens by before anything is built, and every role checks them, because they are ordinary requirements and acceptance criteria.
- One card, sent with the first version, keeps to the attention budget: the client reads one message, and the most common answers (the recommendation, or "leave it to you") need no second round.
- Option 4 always costs one more exchange before the first version, and option 5 always costs a second approval, for an answer that is usually the recommendation.
- The tidy minimum is in every deliverable with screens, so a client who leaves everything to keyturn still gets screens that were checked.
- The card keeps the client's own answer, including that they left the look to keyturn, and the requirements link to it, so the record of who decided stays with the requirements.

## Consequences

- `skills/spec/SKILL.md` writes the section and the card, sends them together, and records the card's answer; `skills/design/SKILL.md` takes and checks the UI library the section names.
- A project's first card may come from `spec`, before any card from `design`; cards are numbered in the project in order, as before.
- The worked example in `evals/requests/task-manager/example/` gets the section, a look requirement, and its criteria; its approval is recorded again with the new hashes.
- How the look is built (#195) and checked (#196), and approving a mockup before building (#197), are separate work that builds on the section.
