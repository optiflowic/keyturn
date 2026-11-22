# 0044. `resume` pushes what only the local task branch has; a closed or merged pull request, or a task branch that moved on `origin`, stops for the maintainer

- Status: accepted
- Date: 2026-11-22

## Context

`deliver` pushes the task branch and updates its pull request after every state commit ([ADR 0041](0041-agents-push-task-branches-and-open-pull-requests.md)). A push can still fail, or never run: the network is down, the session ends between the commit and the push, or the push of the finishing commit fails after the task is set to done. The work is then only on the local branch, and the task cannot be resumed on another machine; a task that is done locally but not on `origin` was not resumable at all, since `resume` had nothing to do for a done task.

Two other cases have no rule yet:

- The task's pull request was closed, or merged, by someone. `open` found only open pull requests, so it would have opened a second one.
- `task/<task>` on `origin` has commits the local branch does not (pushed from another machine, or by a person). The push is refused, since it is never forced. The work cannot go on until someone decides what those commits are.

## Options considered

1. **Leave it to the next state commit.** Every later push sends what was left behind, but a task that is done, or waits for the client, has no next state commit, so its work can stay off `origin` for good.
2. **`resume` pushes first; the script stops on a closed or merged pull request; a moved remote branch stops for the maintainer, who discards the commits.** A little more in `resume` and the script, and a procedure for the maintainer.
3. **Recover by itself: reopen the pull request, and merge or rebase onto the remote branch.** No stop, but an agent would decide what a person's commit or a closed pull request means, and a rebase changes the hashes the state file lists.

## Decision

Option 2.

- **`resume` pushes first.** Whatever the task's status (done included), after it brings the task branch up to date, `resume` pushes the commits that only the local branch has, with the push script, only when that is a fast-forward of `task/<task>` on `origin`; then it goes on (or, for a done task, stops). If the push fails, it stops and reports, and records nothing. A done task whose branch is no longer on `origin` (deleted after the merge) is not pushed again.
- **A closed or merged pull request is never replaced or reopened.** The script stops, and the maintainer is asked what to do.
- **A task branch that moved on `origin` stops the task**, waiting for the maintainer, who looks at the commits and discards them: they turn off the ruleset that blocks force pushes on `task/*` ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md), set up by #141) for this one push, overwrite the remote branch with the local one from a terminal of their own, and turn the ruleset on again right after. The commits are never taken into the task branch. To keep a change they made, the maintainer discards them all the same and asks for the change again as a change to the requirements (`spec`).
- **The state file does not record the pull request.** The branch `task/<task>` finds it.
- **The description of the pull request** carries the delivery report's "Summary" and "What you need to do", and links the client's documents; it never copies the acceptance guide. It is written again when the pull request is marked ready.

## Reasons

- The work reaches `origin` at the first chance, also for tasks that have no later step, so "Resuming Work" holds after any interruption.
- A fast-forward never rewrites what others have; anything else is a person's decision.
- Agents push only through the push script, and the client never touches the code, so in keyturn's flow a task branch on `origin` does not move by itself. Taking such commits in would need the gate to accept a merge, and commits that are no role's, in a task's range; a change to the requirements gets the same result through every role and check.
- A closed pull request, or a commit from elsewhere, may mean something only a person knows (the client stopped the delivery, the maintainer fixed something by hand); guessing would act on the client's behalf.
- The pull request is found from the branch, so recording it would be a second source that can disagree.

## Consequences

- `resume`, the push script, and `deliver`'s stop message change in #139; the maintainer's procedure is in `github/README.md`.
- #141 adds the ruleset step to the one-time setup. Taking commits in is not in the MVP; it is recorded as an enhancement in #118.
- A task whose pull request was closed stays stopped until the maintainer reopens it, or decides otherwise.
