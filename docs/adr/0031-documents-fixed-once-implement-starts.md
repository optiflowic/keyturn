# 0031. During the MVP, a task runs alone, and its requirements, design, and conventions are fixed once `implement` starts

- Status: accepted; that every question from `implement` for `design` stops the task superseded by [0058](0058-design-answers-during-implement.md) (a question that only a gap in the design raises is answered inside the task, without changing the design)
- Date: 2026-11-21

## Context

The gate checks every commit from the head the task's first `implement` step started from, and fails a commit that changes a protected path, unless `deliver` names it as `qa`, `security-review`, `review`, or `deliver` and it changes only what that role may write ([ADR 0029](0029-role-commits-passed-as-arguments.md)). The requirements, the design, the ADRs, the threat model, the conventions, and the client's documents are all protected paths, and `spec`, `design`, and `conventions` are not roles the gate can be told about.

Those documents change inside a task when:

- the client answers a decision card or agrees to a decision, and `design` records the answer;
- the client approves a new version of the requirements, or asks for a change;
- `implement` asks a question that the design, the requirements, or the conventions must answer (`implement` step 6), or `qa` or `security-review` finds that the design must change (an interface it does not describe, a new card for a risk).

[ADR 0009](0009-no-answer-is-not-consent.md) says that the work that does not depend on a waiting card goes on, so `implement` could start while a card waits, and its answer would arrive later inside the gate's range.

Separately, the roles' documents live at fixed paths (`keyturn/internal/review.md`, `security-review.md`, `test-report.md`, the threat model's "Status" lines). When an earlier delivery is merged and the default branch is merged into a task branch, those documents conflict, or the merge produces a version the merge checks of `review` and `security-review` report as a finding (#60).

## Options considered

1. **Let the gate be told about `spec`, `design`, and `conventions` commits too**, each limited to its documents. Changes inside a task would then pass, but the gate reads QA's folders and the accepted ADRs at the base ([ADR 0028](0028-gate-interface.md)), so a design change of QA's folders, of the areas, or of the ADRs inside the range would need rules of its own, and the developer would be judged against documents that changed under them.
2. **Fix the documents before `implement` starts, and stop when they would need to change after.** `implement` starts only when the requirements are approved, every decision card is answered, and every decision the client must agree to is agreed. A need to change the requirements, the design, or the conventions after that stops the task, and the maintainer decides. Simple, and the developer is judged against one set of documents for the whole task. The cost is that `implement` waits for every answer, not only for the ones its work depends on.
3. **Restart the task's checks from the new documents**: move the gate's base past the change. The developer's earlier commits would then leave the gate's range unchecked.

For the documents at fixed paths:

- **Per-task paths** for the roles' documents (for example `keyturn/internal/<task>/review.md`): no conflicts, but every skill, template, and the gate change, before the MVP has shown which documents need it.
- **One task at a time, from the latest default branch, never merging the default branch into it**: no conflicts while a task runs; the cost is that tasks do not run side by side.

## Decision

Option 2, and one task at a time, during the MVP ([ADR 0025](0025-mvp-first.md)).

- A task starts from the latest default branch, and the default branch is not merged into its branch while it runs. A new task starts only when no other task is running or stopped.
- The `design` step is finished only when nothing it sent waits for the client: every card is answered, every decision that needs agreement is agreed, and the design is updated with the answers. Until then, the task stops in the `design` step, waiting for the client, and the steps after it wait. So `implement` starts only once every answer is in. (The requirements are approved before `design` starts, as `design` already requires.)
- After the first `implement` step has started, `deliver` does not run `spec`, `design`, or `conventions` again. A question or a finding that needs one of them (from `implement`, `qa`, or `security-review`) stops the task, and the maintainer decides how to go on (for example, to finish the task without that part, or to start a new task from the changed documents).
- Both are known limitations of the MVP. After it, per-task paths for the roles' documents and changes to the documents inside a task are decided again.

## Reasons

- The gate's checks rely on documents that do not change inside its range. Fixing them before `implement` starts keeps that true without new rules in the gate.
- Within one task, `conventions` and `implement` depend on the design, so there is little work that a waiting card does not block. With one task at a time, there is nothing else to go on with, which is the case [ADR 0009](0009-no-answer-is-not-consent.md) already covers: the task stops with the card as an open question, and resumes after the answer. No card is decided on the client's behalf.
- A question after `implement` started is expected to be rare when the design step finished with every answer in. When it happens, a person is better placed than a rule to judge whether the task can finish without it.
- Never merging the default branch avoids the conflicts on the roles' documents, and the gate stops on a merge in its range anyway ([ADR 0029](0029-role-commits-passed-as-arguments.md)).

## Consequences

- `skills/deliver/SKILL.md` checks that no other task is running or stopped before it starts one, keeps the `design` step in progress while anything waits for the client, and stops for the maintainer when a role needs a document changed after `implement` started.
- The task state file can record a wait for the client's agreement to the design summary, as it records a wait for a card or for approval, so that `resume` can tell when it is given.
- Tasks run one after another. A client with several deliveries waits for each.
- The delivery report made during the MVP says that the task's documents were fixed when `implement` started.
