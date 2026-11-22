# 0047. After the client does not accept a delivery, the PM sorts the answer into one of four cases, confirmed with the client on a decision card

- Status: accepted; that the ruleset on `task/*` blocks deleting a task branch superseded by [0048](0048-default-branch-guarded-in-three-layers.md) where the plan has no rulesets (a deletion is detected instead)
- Date: 2026-11-22

## Context

[ADR 0046](0046-acceptance-record-conditions-check-and-merge-script.md) records the client's answer to a delivery as `waiting`, `accepted`, or `not accepted`, with the client's own words next to it, and merges only on `accepted`. It left a task whose delivery was not accepted stopped for the maintainer, with no way on. The acceptance row could not be asked again, since a row is never changed and a second row for the same documents was not allowed; and the work could not go back to the developer, since the `merge` step said never to send it back.

"Not accepted" covers different things, which need different answers:

- the deliverable does not do what the approved requirements say (a defect QA did not catch);
- the client wants to read the documents again, or to check once more;
- the client wants something the requirements do not have (a new wish);
- the client wants to stop.

What constrains the answer:

- [ADR 0031](0031-documents-fixed-once-implement-starts.md): after the first `implement` step, `spec`, `design`, and `conventions` do not run again inside the task. Changing the code to meet the same requirements is not changing those documents: it is what the rework of [ADR 0030](0030-deliver-rework-loop.md) does. A new wish does change the requirements.
- [ADR 0009](0009-no-answer-is-not-consent.md) and [ADR 0013](0013-confirming-translations-into-english.md): the PM never decides for the client, and makes sure of what the client meant before anything is based on it.
- [ADR 0034](0034-new-task-waits-for-unmerged-task-branches.md): a task branch that is not merged stops the next task until a person says to start anyway. A task that is given up on must not hold up every later task.
- The `task/*` ruleset of the one-time setup blocks deleting a task branch on `origin`, and a task's name is never used again.

## Options considered

1. **Leave every case to the maintainer.** Nothing new, but every "not accepted" needs a person, even when the client only wants to read again or the fix is plain.
2. **Four cases, sorted by the PM and confirmed by the client on a decision card, each with a defined way on.** One more card per "not accepted", a status for a closed task, and the PM may write that card.
3. **Let the client pick a case by a fixed word.** Simple to read, but it asks the client to classify their own answer in keyturn's terms, which ADR 0046 avoids.

## Decision

Option 2.

**Sorting and confirming.** When the newest acceptance row of the task says `not accepted`, the PM (the `merge` step of `deliver`) reads the client's words and proposes one of four cases. It writes a decision card from the template, `keyturn/client/decision-card-<n>.md` with the next free number, in the document language: what it understood the client to mean (in English-only mode, the English the client confirmed with a back-translation, ADR 0013), the four cases as options, its proposal as the recommendation, and that nothing is merged until they answer. It commits the card alone, as a `merge` commit, and the task stops, waiting for the client on that card. The client's answer on the card decides; the PM never picks a case without it (ADR 0009).

1. **A defect: the work goes back to the developer in the same task (c).** The client's reason becomes one finding in English: what they saw, which requirement or acceptance criterion it breaks (by `R-n` or `AC-n`), and what they expected, confirmed with the client as ADR 0013 says. It is recorded in the `merge` row's "Notes" of the state file, and `deliver` sends the work back as for an open finding (ADR 0030): it counts against the rework limit, and `implement` gets it with the other open findings. Then `qa`, `security-review`, `review`, and the `deliver` step run again, the acceptance guide and the delivery report are written again in a new documents commit, and the `merge` step sends them for acceptance in a new row. This does not conflict with ADR 0031: the requirements, the design, and the conventions stay as they are. If fixing it needs any of them changed, it is not a defect but a new wish (case 3), and the task stops for the maintainer as ADR 0031 says.
2. **Read or check again (b).** The same documents are asked about again: a new acceptance row for the same documents commit, at `waiting`. This is the one case where a second row for the same documents commit is added; the newest row is the one that counts (ADR 0046).
3. **A new wish.** The task is asked about again as in case 2, with the card saying that the wish is handled by the next task once this one is accepted and merged. If the client wants the wish in before this delivery is merged, the task stops for the maintainer.
4. **Stop (a).** The task is closed:
   - the state file is set to `Status: closed`, with `Current step: none`, `Stopped because: none`, `Can continue: not applicable`, the steps as they are, and a last History line `closed: <why>, in merge`; it is committed alone and pushed;
   - the pull request is closed with `task_branch.py close <task>`, with a comment, never merged;
   - the branch is kept, locally and on `origin` (the ruleset blocks its deletion anyway): it is the record of what was delivered and not accepted, and its name stays used.
   `task_state.py` treats a closed task as finished: `list` leaves it out, like a done one, and `unmerged` leaves it out when its head is the commit that last changed its state file and says closed there. So a closed task does not hold up the next one (ADR 0034), while a commit made after closing it still does, as work not merged.

**The card and the merge conditions.** The `merge` role may also commit a decision card (only the card, in a commit of its own). The conditions' check allows such a commit after the documents commit. A card counts for `accepted: decision card <n>` on a review finding only if it existed before the developer's first commit, so a card of the `merge` step never accepts a finding (ADR 0042).

**Same-session answers.** When the client answers the card while the PM is still talking to them, the answer is recorded on the card (its "Your answer"), committed as a `merge` commit, and the task goes on at once; otherwise it goes on with `resume`, like any card.

## Reasons

- Each case gets the answer it needs without a person, except where the documents would have to change, which ADR 0031 keeps for the maintainer.
- A decision card is how keyturn already asks the client to choose, with an answer that is committed and that `resume` knows how to read; the PM's proposal is a recommendation, never a choice made for the client.
- Counting a defect's round against the rework limit keeps the limit meaningful: a client cannot be sent an endless series of deliveries.
- Closing a task by its state file, and keeping the branch, leaves a record and frees the next task without deleting anything, which the ruleset forbids anyway.

## Consequences

- `deliver`'s `merge` step gets the card and the four cases; its rework gets the client's finding as one more reason the work goes back (an addition to ADR 0030's list); `implement` gets that finding in the next round.
- `spec` adds a second acceptance row for the same documents commit when the card's answer is case 2 or 3.
- The state template and `task_state.py` get `Status: closed` and the `closed` History line; `resume` says a closed task has nothing to resume; `task_branch.py` gets `close`.
- The gate lets a `merge` commit write a decision card; the conditions' check allows it after the documents commit, and reads a card that accepts a finding as it was before the developer's work.
- A defect found by the client is also a sign that QA's tests missed it; the delivery report of the next round says so under "What was verified".
