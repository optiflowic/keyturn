# 0062. An earlier design answer may be withdrawn, by the maintainer's decision only, with a new entry

- Status: accepted
- Date: 2026-11-24
- Supersedes: in [0058](0058-design-answers-during-implement.md), that a later entry may not contradict an earlier one (a withdrawal entry, by the maintainer's decision, voids an earlier answer, and a new answer may then take its place); in [0030](0030-deliver-rework-loop.md), what sends the work back (a withdrawal after the round's checks have run does)

## Context

`keyturn/internal/design-answers.md` holds the architect's answers to what the approved documents leave open once `implement` has started ([ADR 0058](0058-design-answers-during-implement.md)). Entries are only added, an entry is never changed or removed, and a later entry may not contradict an earlier one. `review` reports an answer that cannot stand, and the task then stops for the maintainer ([ADR 0061](0061-answer-findings-stop-for-the-maintainer.md)).

The rehearsal of the MVP run found an answer that the developer could not build: it put code where a lint rule of the conventions keeps it from reaching the store. The architect could not give another answer, because it would contradict the first. The maintainer decided to go on without the answer, but `design` could not record that either, for the same reason, so the task stopped again with no way forward but to close it.

## Options considered

1. **A withdrawal entry, by the maintainer's decision only.** `design` adds an entry that names the answer it withdraws and why. Readers take the withdrawn answer as void. No earlier entry changes, so the file still shows what was answered, and when.
2. **Let `design` change or remove the entry.** Simpler to read, but the record of what the developer built from, and of what QA and the reviewers read, is lost, and an earlier entry could change after the roles read it.
3. **Let the maintainer go on without recording it.** The task goes on, but the answers still say what to build, so `implement`, `qa`, and the reviewers keep reading the withdrawn answer as the design.

## Decision

Option 1.

- **Only by the maintainer's decision.** The maintainer tells `resume` which answer to withdraw and why, and `resume` records it in "History" as `withdraw A-<n>, by the maintainer's decision: <why>`. It is recorded only when the task stopped waiting for the maintainer after `implement` started. Never on the developer's, QA's, or a reviewer's request alone, and never on the architect's own judgment.
- **A new entry, never an edit.** `design` adds a withdrawal entry: the answer it withdraws, and why, in the architect's own words, keeping what the maintainer decided. When the gap is still open and an answer fits the limits of ADR 0058 and can be built within the areas and the conventions, the architect may write a new answer in its place, as an entry of its own, unless the maintainer decided to go on without one. That new answer may differ from the withdrawn one. When nothing takes its place by the maintainer's decision, `design` does not answer that gap again in the task, and QA does not ask about it again. No earlier entry is changed or removed.
- **What cannot be withdrawn.** A rating answer that raised a threat's rating: a rating is never lowered ([ADR 0060](0060-design-answers-for-qa-and-threat-ratings.md)). A withdrawal entry, and an answer already withdrawn. `design` does not write such a withdrawal and reports it, and the task stops for the maintainer again. `security-review` and `review` report one that is written anyway as a high finding located at it, and read the raise as standing. A rating answer that kept a rating with a reason may be withdrawn; the security review then judges the threat without that reason.
- **The readers.** `implement`, `qa`, `security-review`, and `review` read a withdrawn answer as void: nothing is built from it, tested through it, or judged against it. `review` closes a finding located at the withdrawn answer only after its own check of the withdrawal.
- **In `deliver`.** It runs `design` for the withdrawal before the current step, as for the maintainer's answer (ADR 0058). The run does not count toward the limit of two answer runs in a round. Then:
  - when the current step is `implement`, `implement` runs again in the same round, without the withdrawn answer;
  - when the round's checks have already run (the task stopped in `security-review` or `review`), the developer built and was checked with the withdrawn answer, so the work goes back in a rework round, which counts toward the rework limit ([ADR 0030](0030-deliver-rework-loop.md)).

## Reasons

- An answer that cannot stand no longer ends the task: the maintainer, the only one outside the task who may decide about the approved documents' answers, can take it back, and the architect can answer the gap again.
- Entries are still only added, so the file keeps the whole record: what each role read, and when it changed. The gate checks that the answers' commits change only that file; nothing about it changes.
- Withdrawing a raised rating would lower it, which ADR 0060 forbids. Withdrawing anything else makes no check weaker: the approved documents are still the same, and the answers still only fill what they leave open.
- Known gap, as in ADR 0058: the gate reads the `answer` commits from the head, so a developer could commit a withdrawal of their own and list it as `answer`. The gate reads nothing from the answers. Voiding an answer only takes away what was added to the design, so the reviewers judge the work against the design alone. A withdrawn raise is reported as a finding and still read as standing.

## Consequences

- `templates/internal/design-answers.md` gets a withdrawal form, and the worked example in `evals/requests/task-manager/example/` a withdrawal entry.
- `resume` records the maintainer's decision. `deliver` runs `design` for it and goes on as above. `design` writes the withdrawal and, when it can, a new answer. `implement`, `qa`, `security-review`, and `review` read the withdrawn answer as void.
- A withdrawal after the checks costs a rework round.
- The delivery report lists a withdrawal among the answers, under "Guardrails triggered".
- Nothing under `gates/` or `github/` changes, so a task running on a workflow from ADR 0058 on can go on after the plugin is updated.
