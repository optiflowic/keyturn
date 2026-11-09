# 0010. The client may accept the risk of a low threat, on a decision card

- Status: accepted
- Date: 2026-11-08

## Context

"Security" in `docs/DESIGN.md` says that every threat in the threat model must have a mitigation that is actually implemented. The phase 2 templates follow this strictly: in `templates/internal/threat-model.md` and `templates/internal/review.md`, a threat that cannot be mitigated is raised with the client on a decision card, and delivery stays blocked until a mitigation is implemented.

In practice, some low threats cost more to mitigate than they are worth, and some mitigations cover only part of a threat. The worked example already has one: T-6 in `evals/requests/task-manager/example/keyturn/internal/threat-model.md`, where someone who knows a person's email address can type wrong passwords on purpose to keep them from signing in. Sessions already signed in keep working, but repeated blocking is not prevented, and preventing it would change an approved requirement (R-8). Today the template has no place for what is left over, so the example only reports it under "Remaining risks" in the delivery report, without the client having agreed to it.

The question is whether the client may accept such a risk instead of the threat being mitigated, and under what conditions. The `security-review` skill (phase 3) needs the answer.

What constrains the answer:

- The client decides what risk they take on; a role cannot accept a risk for them (and, by ADR 0009, an unanswered card is never decided for them).
- Some changes always need the client's approval: new dependencies, new external services, changes to authentication, authorization, or data handling, and anything that deletes data ("Guardrails", 2). Threats in these areas are the ones that hurt most when they go wrong.
- High-severity findings block delivery like a failing gate.
- Every accepted risk has to stay visible to the client, not only on the day it was accepted.

## Options considered

1. **Never accept a risk.** Every threat needs a full, implemented mitigation; when one is not worth it, the only way out is to change the requirement that creates the threat. Simplest and strictest, but it forces costly mitigations or requirement changes for nuisance threats, and it pushes roles to leave threats out of the threat model, or to describe them more narrowly, so that the model passes.
2. **The client may accept a low threat, when all three conditions hold**:
   - the threat is low severity, as confirmed by the security role;
   - the client agrees on a decision card, which offers mitigating the threat as one of the options;
   - the accepted risk is listed under "Remaining risks" in every delivery report while the threat is in the threat model.

   Some threats can never be accepted, however low. Two ways to draw that line:

   - **2a. By area**: any threat in an area that always needs the client's approval ("Guardrails", 2): authentication, authorization, data handling, deleting data, dependencies, and external services. Easy to check from the entry point and the asset. It also excludes threats in those areas that only make something unavailable for a while, such as T-6.
   - **2b. By harm**: any threat that could let someone sign in as someone else or without signing in, get rights they should not have, read, change, or delete data they should not, or reach in through a dependency or external service. A low threat that only makes something unavailable for a while (for example, a short sign-in block, as in T-6) can be accepted even where it touches sign-in. Needs a judgment about the harm, which the security role makes and the client sees on the card.
3. **The security role accepts low risks itself**, and lists them in the delivery report. Fewer questions for the client, but a role would be taking on risk for the client, which only the client may do.

## Decision

Option 2 with 2b: the client may accept the risk of a low threat, or of the part of a threat that its mitigation does not cover, on a decision card, and every accepted risk is listed under "Remaining risks" in each delivery report. A threat whose harm is getting in, getting more rights, or reading, changing, or deleting data, or that comes through a dependency or an external service, is never accepted, whatever its severity: it is mitigated, or the requirement that creates it is changed.

An accepted risk is accepted only as it was described. If its severity, its threat, or the requirement it comes from changes, the acceptance no longer holds and a new card is needed.

## Reasons

- The three conditions keep the client in control: only the client accepts, only for low threats, and they see every accepted risk again at each delivery.
- Drawing the line by harm (2b) keeps out every threat that loses access, rights, or data, which is what the Guardrails areas protect, while still letting the client accept a low availability risk such as T-6. Drawing it by area (2a) would leave T-6 with no way out except changing R-8, a requirement the client approved, for a low threat that does not let anyone in.
- Accepting the leftover part of a partly mitigated threat, under the same conditions, closes a gap: without it, a small mitigation could be used to call a threat "mitigated" and leave the rest out of sight.
- Offering mitigation on the card, with its cost, makes the card a real choice instead of a request to sign off.

## Consequences

- `docs/DESIGN.md` "Security" states the exception and its conditions.
- `templates/internal/threat-model.md` gets a "Remaining risk" line per threat (none, waiting for the client, or accepted on a decision card), and the `accepted` status for a threat whose remaining risk the client accepted.
- `templates/internal/review.md`: in the threat model check, a missing or partial mitigation is a high-severity finding unless the remaining risk was accepted on an answered card.
- `templates/client/delivery-report.md`: "Remaining risks" lists every accepted risk, with the card and the date it was accepted.
- The worked example gets a second decision card, in which the client accepts the repeated blocking left over from T-6.
- The `security-review` skill (phase 3) confirms the severity, checks the conditions, and treats a card that has not been answered as "not accepted": delivery stays blocked until it is answered or the threat is mitigated.
