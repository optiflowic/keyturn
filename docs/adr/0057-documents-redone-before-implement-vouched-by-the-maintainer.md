# 0057. The maintainer may have a task's documents redone before `implement`, and vouches for the result in a repository variable

- Status: accepted
- Date: 2026-11-23
- Supersedes: in [0032](0032-gate-base-is-where-the-task-branch-left.md) and [0043](0043-gate-finds-a-task-s-range-in-ci.md), that the document roles' commits are read only from the oldest version of the state file whose `conventions` row is `done` (after a vouched redo, they are read from the vouched version)

## Context

The gate, `deliver`, and the merge conditions read the `spec`, `design`, and `conventions` commits only from the oldest version of the state file whose `conventions` row is `done` ([ADR 0032](0032-gate-base-is-where-the-task-branch-left.md), [ADR 0043](0043-gate-finds-a-task-s-range-in-ci.md)). The developer's commits come after that version, so a later line naming a document role is never trusted: it could make a developer commit that changes the design, an ADR, or a linter config pass as that role's.

A rehearsal found the case this leaves out. After `conventions` is recorded, but before the first `implement` step starts, the maintainer may decide that `design` or `conventions` (or `spec`) has to be done again. [ADR 0031](0031-documents-fixed-once-implement-starts.md) fixes the documents only once `implement` starts, so nothing forbids it, but the redone commits are listed by a later version of the state file, and the gate stops (exit 2) on every run after it.

A record on the branch cannot tell a real redo from a forged one. The developer could commit an ADR, then a state file that looks like a redo (the steps set back, the ADR's commit listed as `design`'s, `conventions` done again), and then the code; every file on the branch would read as the maintainer's redo.

## Options considered

1. **A repository variable the maintainer sets**, `KEYTURN_DOCUMENTS`, naming the state commit that records the redone documents, as `KEYTURN_VOUCHED` names commits the maintainer vouches for ([ADR 0048](0048-default-branch-guarded-in-three-layers.md)). The agents' token has no Variables permission, so the developer cannot write it. The gate's run in CI reads it; the agents cannot, so their own runs read the vouch from the state file and only repeat what CI decides.
2. **A pull request comment by the maintainer** naming that commit. Also out of the agents' reach, but the gate would need to read the pull request's comments, and the account that writes them.
3. **Trust the state file's record** when no `implement` line comes before it, and list the redo in the delivery report for the maintainer to check. Cheap, but a forged redo passes every machine check.

## Decision

Option 1.

- **The redo.** Only the maintainer decides it, while the `implement` row is `not started` and no commit is listed as `implement`'s. They tell `resume`, which records the decision in "History" (`redo of <steps> before implement, by the maintainer's decision: <what>`); `deliver` sets the first redone step and every later step back to `not started` and runs them again as usual.
- **The vouch.** Once `conventions` is recorded as `done` again, `deliver` stops before `implement`, waiting for the maintainer, with the full SHA of that state commit. The maintainer looks at the documents there and adds `<task>:<full SHA>` to the repository variable `KEYTURN_DOCUMENTS` (entries separated by spaces, commas, or new lines; one entry per task, replaced after a second redo). They then tell `resume`, which records `documents vouched for at <full SHA>, by the maintainer's decision` in "History".
- **The gate** (`--task`) and **the merge conditions** take a new option, `--documents-vouched <the variable's value>`. With an entry for the task, they read the document roles' commits from that version of the state file, never from the oldest one or from a later one, and only when that version is a commit in the range that changes only the state file, has `conventions` `done` and `implement` `not started`, and lists every commit before it, each as `spec`'s, `design`'s, `conventions`', or `deliver`'s; otherwise they stop (exit 2). A malformed entry, or two entries for the task, stops them too. Without an entry, nothing changes. Every later line that names a document role must agree with that version, as before.
- **The workflows** pass `vars.KEYTURN_DOCUMENTS` to both checks, and to `keyturn watch`, which checks a merged task's conditions again on every run ([ADR 0048](0048-default-branch-guarded-in-three-layers.md)); so an entry is kept after its task is merged. `deliver`'s own gate calls name the commits from the version that the newest vouch line in "History" names, and `merge.py` passes that line's SHA to its local conditions check. Neither can read the variable, and both only repeat the checks in CI, which read it themselves; the merge needs those checks to pass ([ADR 0046](0046-acceptance-record-conditions-check-and-merge-script.md)).

## Reasons

- What the developer's commits are judged against stays fixed by something outside the branch: a version the maintainer looked at and named, in a place only the maintainer can write.
- It reuses a mechanism the project already sets up for the same reason, the maintainer's repository variables, and needs no new permission for the workflow or the agents.
- The checks on the vouched version (a state commit before `implement`, listing every commit before it as a document role's or `deliver`'s) keep a careless vouch from naming a version after the developer's work started.

## Consequences

- `gates/gate.py` and `gates/conditions.py` take `--documents-vouched`; `github/workflows/keyturn-gate.yml` and `keyturn-watch.yml` pass the variable; `github/scripts/merge.py` passes the recorded vouch. A project that copied the workflows before this change copies them again between tasks; `deliver` stops a redo when the workflow at the task's base does not pass the variable, since updating it during the task would move the default branch; that task is closed, and started again after the workflows are updated.
- A redo sets back only steps that are `done`, and the task goes on from the first step that is neither `done` nor `skipped`, so a step waiting for the client still takes in the answer first (ADR 0031).
- Once `conventions` is recorded and the current step is `implement`, no commit is listed as a document role's any more, even before the `implement` row changes: an ADR the developer committed in a run that ended before it was recorded must not become `design`'s through a redo and a vouch.
- `deliver` has a procedure for a redo before `implement`, and stops for the vouch; `resume` records both decisions. `github/README.md` says how to add the entry.
- A redo costs the maintainer one more step, at the moment the documents are fixed. A redo after `implement` has started is still not possible inside the task (ADR 0031).
- Entries are never removed, also after their task is merged or closed, so the variable grows by one entry per task with a redo. Removing one would make `keyturn watch` fail on that task's merge commit.
- One malformed entry, or two entries for one task, stops the checks of every task, not only of the task it names. It is accepted: `keyturn watch` checks every merged task's conditions with the same variable, so its next run fails and opens an issue that mentions the maintainer, and the entry is put right at once.
- The agents' local checks trust the vouch line in "History", which the developer could forge; they never merge on it alone, since `merge.py` also needs the checks in CI, which read the variable.
