# 0075. The design summary shows the client how the options compare for whoever maintains the deliverable

- Status: accepted
- Date: 2026-11-28

## Context

[ADR 0073](0073-design-weighs-maintainability-after-delivery.md) has the design weigh how easily the client's people can maintain each tool or approach after delivery against its fit. The ADR of each such choice records the weight and compares every realistic option on five signals (use, modern, documentation, people, stability), from current sources with their dates. The design summary, which the client reads, says only who the design assumed maintains the deliverable and the weight that gave, and, when the chosen option is less known than another, that it is and why.

So the client, who is the one whose people maintain the deliverable, sees the result of the comparison only when the choice is less known. When they agree to a decision, or read one for information, they cannot see how widely each option is used, whether the stack's current documentation still recommends it, or whether their people are likely to know it, unless they open the decision record, which is in English and written for the roles.

What constrains the answer:

- The client does not read code, and their attention is limited ("Client attention budget" in `docs/design/documents.md`): the summary must stay short and in plain words.
- The comparison's signals change over time; what the client reads must carry the date it was checked, as the ADR does.

## Options considered

1. **Keep it as it is.** The summary stays shortest, but the client agrees without seeing the comparison that was made for their people.
2. **Copy the ADR's table into the summary.** Complete, but long and technical: five signals per option, with sources, for every decision.
3. **One short field per decision, in plain words.** The weight, and for the chosen option and each compared option one line on how widely it is used, whether the stack's current documentation still recommends it, and whether people are easy to find who know it, with the date checked; documentation and stability only when they decided the choice.

## Decision

Option 3. Each decision whose ADR has a "Maintainability after delivery" section gets a field of its own in the design summary, under "Must agree" and under "For information" alike, between "Other options we considered" and "What it means for you":

- a first line with the weight: how much maintainability counted against fit for this decision, and why (who maintains the deliverable, as "Summary" says, or the client's answer);
- one line for the chosen option and one for each option the ADR compared (not for one ruled out on fit, which "Other options we considered" covers), each saying in plain words how widely it is used, whether the stack's current documentation still recommends it, and how easy it is to find people who know it, and, only when they decided the choice, its documentation and its stability;
- the date the signals were checked, or that they could not be checked, and why.

A less known choice is still said, and why, in "What it means for you" (ADR 0073). The field names no source the client would have to open; the decision record has them.

## Reasons

- The client's people carry the cost of the choice after delivery, so the client should see the comparison made for them when they agree to it, not only when the choice is less known.
- Three signals in plain words (used, recommended, known by people) are what a client who does not read code can weigh; the other two matter to them only when they decided the choice.
- A field of its own keeps it apart from "Why", which ties the decision to the requirements, and from "What it means for you", which the client agrees to.
- The date tells the client the comparison is current, as ADR 0073 requires of the ADR.

## Consequences

- `templates/client/design-summary.md` has the field, and `skills/design/SKILL.md` step 7 writes it, and its step 6 checks it.
- The worked example's design summary in `evals/requests/task-manager/example/` shows it for every decision.
- The design summary gets a few lines longer per decision; a design with many decisions should group them as the design skill's "Keeping it small" already says.
- "Architect" in `docs/design/roles.md` and the design summary's row in `docs/design/documents.md` say it.
