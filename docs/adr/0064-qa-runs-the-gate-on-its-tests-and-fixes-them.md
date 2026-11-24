# 0064. QA runs the gate on its own tests and fixes what fails in them, also by the maintainer's decision, outside the rounds of rework

- Status: accepted
- Date: 2026-11-25
- Supersedes: in [0030](0030-deliver-rework-loop.md), that every failure of the gate after `implement` goes back to the developer (a run of `qa` by the maintainer's decision comes first, and does not count as a round)

## Context

QA writes its tests in folders the developer may not change ([ADR 0017](0017-qa-tests-in-their-own-folder.md)), and the gate runs every check of a part on the whole part, QA's tests included ([ADR 0028](0028-gate-interface.md)). But QA's tests first reach the gate in the round after QA wrote them: the gate runs after `implement`, and QA runs after that gate passed. QA itself ran only its tests, in the working tree.

The rehearsal of the MVP run found two ways this goes wrong. The conventions' linters reported findings in a QA test file, which `qa` never linted. And a QA test of a Go server served the web part's build output (`web/dist`), which is git-ignored: it was in the working tree, so the test passed for QA and for the developer, but the gate checks out the head in a clean worktree and runs the parts one after another, so the folder did not exist when the server's tests ran. In both cases the gate after the next `implement` failed in QA's folders, `deliver` sent the work back to the developer, who could change nothing there, and the task used up its rounds of rework and stopped.

The maintainer then decided that QA should fix its tests, and that the round should go on from the gate without counting a developer round. Nothing carried that decision out: `resume` records only the decisions ADRs 0053, 0057, 0058, 0060, and 0062 name, `deliver` runs the steps in order with no `qa` before `implement`, and `qa` reruns only after the developer's fix or a change of the requirements. The task was kept open, to be resumed with this change, and its CI runs an older keyturn commit, so the change cannot depend on a change to the gate or the workflows.

## Options considered

1. **QA runs the gate on its own commits before it reports, and fixes what fails in its work.** The gate checks out the head in a clean worktree, so it finds what QA's run in the working tree cannot (a file that is not committed, another part's build output). A QA test that fails because the deliverable does not meet its criterion is still a result, never fixed.
2. **QA runs the part's tools in the working tree before it commits.** Simpler, but the working tree has what a clean checkout does not, so the build-output case passes there.
3. **The gate builds every part before it tests any.** It would make the build-output case pass, but a test would then depend on another part's build that the profiles do not say runs first, the format and lint checks would see the build output, and the change would not reach a task whose CI runs an older gate.
4. **For the decision: send the work back to the developer with a note for QA.** It keeps the steps in order, but counts a round for work the developer does not do.

## Decision

Option 1, with the rule on what a test relies on instead of option 3, and a decision of the maintainer that runs `qa` to fix its tests.

- **QA runs the gate.** After it commits its tests and its report, `qa` runs keyturn's gate with the commit it tested as the base, the head, and each of its commits named as `qa` (`--others qa:<commit>`). It fixes what is its own: a finding in QA's folders (lint, format, vet, a type error, a suppression comment, a test file that does not compile), and a QA test that passed in its run but fails in the gate. It never adds a suppression or weakens a test to do it. It reruns its tests, writes the report again when a result changed, and commits the fix as another commit of its step, for at most three runs of the gate. A test that fails in both runs and matches its criterion stays `fail`; a failure outside QA's folders, or a drop in the test count that its report explains (a removed criterion or a withdrawn answer), is reported, not fixed.
- **Tests rely only on what the gate has.** A QA test relies only on files committed in the repository and on what its own part's setup and checks make, never on another part's build output, a file Git does not track, or data an earlier run left. When a test needs another part's output (for example, the pages a server serves), it uses what the design or the design answers give for it (for example, a folder passed to the server), with a folder the test makes; without one, QA asks a question for the design ([ADR 0060](0060-design-answers-for-qa-and-threat-ratings.md)). Whether the real build is served is then left to the client's acceptance guide. The gate is not changed.
- **In `deliver`.** Every commit of the `qa` step is listed as `qa`. When QA reports that the gate could not run on its commits, or still fails on its own work after its fixes, the task stops for the maintainer before `security-review`, so that the next round's gate does not send QA's failure to the developer.
- **The maintainer's decision.** The maintainer tells `resume` that QA fixes its tests, and `resume` records it in "History" as `QA fixes its tests, by the maintainer's decision: <what>`. It is recorded only when the task stopped in `implement` after QA committed tests, waiting for the maintainer or at the rework limit (where it is not a decision on rounds), or in the `deliver` step after its gate failed after the developer's head, and never on a role's report alone. `deliver` then runs the gate on everything up to the stop to get its failures, and runs `qa` to fix its tests with those lines and the maintainer's words, never the developer's code or reasoning. The run does not add to `Rework`. Then:
  - in `implement`, `deliver` runs the gate again on the same developer head with QA's new commits: when it passes, `implement` is done with the developer's head unchanged, `qa` is done with the report of the fix run, and the round goes on with `security-review`; when it fails only on QA tests that the new report marks `fail`, the work goes back to the developer, as for any failing test; otherwise the task stops for the maintainer again, without sending the work back;
  - in the `deliver` step, the step runs again from its gate.

## Reasons

The gate is the one place that checks what is committed in a clean checkout, so running it is the only way for QA to see what the next round's gate will see; running the tools by hand repeats it less faithfully. QA fixing its own work keeps the rule that the developer never touches QA's folders, and a test that relies only on what is committed is what every other check already assumes. Keeping the gate as it is lets the change reach a task whose CI runs an older gate. The maintainer's decision follows the form of ADRs 0060 and 0062, so that `resume` and `deliver` treat it as they treat the others, and the developer keeps the rounds the decision does not use.

## Consequences

- `qa` takes longer: the gate sets up the base and the head and runs every check of every part.
- The `qa` step may have more than one commit.
- `resume` accepts a sixth kind of decision, and `deliver` runs `qa` out of the order of the steps for it, before the current step.
- A gate failure that is only in QA's folders still goes back to the developer when nobody decides otherwise; telling such failures apart in the gate, so that `deliver` sends them to QA on its own, is a separate change.
- Whether another part's real build is served is not tested by QA, and is for the acceptance guide.
