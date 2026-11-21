# 0034. A new task waits while a task branch is not merged into the default branch, unless the person says to start anyway

- Status: accepted
- Date: 2026-11-21

## Context

During the MVP, a new task starts only when no other task is running or stopped, from the latest default branch ([ADR 0031](0031-documents-fixed-once-implement-starts.md)). A task that is done is not running or stopped, but its delivery ends at its branch: a person opens the pull request and merges it ([ADR 0033](0033-delivery-documents-from-the-records.md)). Until they do, a new task starts from a default branch without that work, and the roles' documents at fixed paths (`keyturn/internal/review.md`, `test-report.md`, the client's documents) are written on both branches, so the second merge conflicts (#60).

`deliver` cannot tell whether that is what the person wants: they may have set the earlier delivery aside on purpose.

Pull requests may be merged with a merge commit, a fast-forward, or a squash. A squashed branch's head is not an ancestor of the default branch.

## Options considered

1. **Start anyway.** Nothing waits, and the conflicts come later, on the person's merge.
2. **Never start while a task branch is not merged.** The person must merge or delete the branch first, even when they meant to set it aside.
3. **Stop and ask, and start only when the person says to start anyway.** The person decides, knowing which branches are not merged and what that means.

## Decision

Option 3. Before a new task starts, `deliver` lists every local and remote `task/<task>` branch that is not merged into the default branch, with `task_state.py unmerged <default branch>`. A branch counts as merged when its head is an ancestor of the default branch, or when the default branch has the task's state file exactly as the branch's head has it (a squash merge carries the branch's last state commit, and `deliver` commits the state file after every step). If any branch is listed, `deliver` stops, tells the person which branches and why it matters, and starts the task only when the person answers that it should start anyway. A running or stopped task still stops a new one, whatever the person answers ([ADR 0031](0031-documents-fixed-once-implement-starts.md)): it is finished with `resume` first, or set aside by deleting its branch.

## Reasons

- The person knows whether the earlier delivery is waiting for a merge or set aside; `deliver` does not, so it asks instead of guessing either way.
- Comparing the state file covers squash merges without reading pull requests, which `deliver` does not use during the MVP.
- A request to deliver something is not an answer to this question, so only an explicit answer lets the task start.

## Consequences

- `skills/resume/scripts/task_state.py` gets the `unmerged` command, with its tests.
- `skills/deliver/SKILL.md` runs it before choosing the new task's name, after the check for running or stopped tasks.
- A task branch with work committed after its squash merge counts as not merged, which is right: that work is not on the default branch.
- After the MVP, per-task paths for the roles' documents may make this check unnecessary; it is decided again then.
