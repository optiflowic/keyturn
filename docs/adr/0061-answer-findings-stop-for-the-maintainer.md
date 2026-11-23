# 0061. A review finding at a design answer stops the task for the maintainer, and never sends the work back

- Status: accepted
- Date: 2026-11-24
- Supersedes: in [0030](0030-deliver-rework-loop.md), what sends the work back (a finding of `review` located at a design answer does not)

## Context

`review` reports a design answer ([ADR 0058](0058-design-answers-during-implement.md)) that changes what the design decides as a high finding located at the answer. A design answer may also be one that the developer cannot build within the areas the work may change and the conventions. The rehearsal of the MVP run found one: a lint rule of the conventions kept the handlers from the store. `review` now reports such an answer too.

Neither finding can be fixed inside the task. The developer may not change `keyturn/internal/design-answers.md`. An entry is never changed. A later entry may not contradict an earlier one, so `design` cannot replace it either. Before this decision, `deliver` sent every open high finding back to `implement` ([ADR 0030](0030-deliver-rework-loop.md)), so the task went round to the rework limit, each round ending the same way. [ADR 0060](0060-design-answers-for-qa-and-threat-ratings.md) met the same problem for the security review's rating findings, which are the architect's, not the developer's.

## Options considered

1. **Handle it as a rating finding.** The finding never sends the work back and is never given to `implement`. The task stops for the maintainer, who decides how it goes on.
2. **Keep sending it back.** No change, but no round can fix it, and the rounds are spent until the limit.
3. **Let `design` replace the answer on its own.** This would stop the loop, but it changes the rule that answers never contradict each other, without anyone outside the task deciding. Withdrawing an answer is a separate decision, by the maintainer only (#181).

## Decision

Option 1. `review` titles every finding located at an answer `A-<n> cannot stand as an answer`. In `deliver`, such a finding never sends the work back on its own and is never given to `implement`. When one is open, the task stops for the maintainer, as for a rating finding: anything else that sends the work back is sent back first, and the task stops instead of going on with `implement`. Only `review` closes the finding, after its own check.

## Reasons

- The answer is the architect's work, not the developer's. Sending it to the developer spends rounds that cannot fix it.
- The maintainer is the only one outside the task who may decide what happens to an approved document's answer, as for ratings in ADR 0060.
- The finding stays high and open until `review` closes it, so the merge conditions still block the delivery ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)).

## Consequences

- `review` titles answer findings in a fixed form; `deliver` stops for the maintainer on them.
- Until the maintainer can have an answer withdrawn (#181), the maintainer's choices are the ones they already have for a stopped task, for example stopping it.
- Nothing under `gates/` or `github/` changes.
