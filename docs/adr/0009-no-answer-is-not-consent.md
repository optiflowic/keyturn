# 0009. An unanswered decision card is never decided on the client's behalf

- Status: proposed
- Date: 2026-11-08

## Context

Every decision card says what happens if the client does not answer ("Client attention budget" in `docs/DESIGN.md`). `templates/client/decision-card.md` already says that a change that always needs the client's approval ("Guardrails", 2: new dependencies, new external services, changes to authentication, authorization, or data handling, and anything that deletes data) is never chosen on the client's behalf. It does not say what happens to other questions on a card.

The question is whether the agent may go ahead with the card's recommendation when the client has not answered such a question, and under what conditions. The `deliver` skill (phase 3) needs the answer, because it decides what the pipeline does while a card is waiting.

What constrains the answer:

- "Ask only when it matters": low-risk choices within the approved requirements are decided by the roles and recorded as ADRs, without a card. So a question that reaches a card is, by that rule, one that matters to the client.
- If not answering has the same effect as agreeing, the client learns that cards can be ignored, which is the failure the attention budget exists to prevent.
- A task can already stop for "a question waiting for the client" and be finished later with `resume` ("Resuming Work"), so waiting does not lose work.
- Unattended and scheduled runs come later (phase 12). In phase 3, runs are started by someone who can be asked.

## Options considered

1. **Never go ahead with the recommendation.** Work that depends on the answer waits; everything else goes on. If nothing else can be done, the task stops with the card recorded as an open question, and continues with `resume` after the answer. Simple, and the client always makes the choice; the cost is that some work waits.
2. **Go ahead with the recommendation after a stated deadline, for low-risk questions only.** The card states the deadline; after it, the agent applies the recommendation and lists the choice in the delivery report so the client can still change it. Less waiting, but the agent judges what is low risk, choices made on the client's behalf may have to be undone after delivery, and the card stops being a question.
3. **A per-project setting, off by default.** Option 1 by default, option 2 when the client turns it on. Flexible, but it adds a setting, deadlines, and a "decided for you" section before there is an unattended mode that needs them.

## Decision

Option 1: an unanswered card is never decided on the client's behalf, whatever the question. Work that depends on the answer waits, and the rest goes on. Whether to go ahead with the recommendation is reconsidered, as a per-project setting, when the unattended mode is designed.

## Reasons

- A card exists only because the question matters ("Ask only when it matters"). A question that is safe to decide without the client should not be a card at all; it is decided by the role and recorded as an ADR.
- Waiting is cheap: the work that does not depend on the answer goes on, and `resume` picks up the task once the client answers.
- The rule is the same for every card, so neither the agent nor the client has to judge which questions are "low risk enough", and the Guardrails list cannot be worked around by calling a question low risk.
- The client keeps learning that a card needs an answer, which keeps cards worth reading.

## Consequences

- `docs/DESIGN.md` "Client attention budget" says that no answer is not consent, and what happens instead.
- `templates/client/decision-card.md` tells the role to state which work waits and which goes on, and never to choose an option on the client's behalf.
- The `deliver` skill (phase 3) keeps working on what does not depend on a waiting card. When nothing else can be done, it records the card as an open question in the task's state file and stops; `resume` continues once the answer is recorded. A delivery is not finished while a card about the work in it is waiting.
- A client who answers slowly delays the work that depends on the answer. The time a card waits is part of the cost data the attention budget already tracks.
- The unattended mode (phase 12) needs its own decision on this, likely a per-project setting (option 3). This ADR is superseded then if the decision changes.
