# 0029. `deliver` names each role's commits to the gate and the reviews as arguments; the task state file only records them

- Status: accepted; the gate's range starting at the head before the first `implement` step superseded by [0032](0032-gate-base-is-where-the-task-branch-left.md) (it starts where the task branch left the default branch, and the document roles' commits are named too), and `resume` listing its state commit only past that head superseded by the same ADR (it always lists it); what `deliver` may write superseded by [0033](0033-delivery-documents-from-the-records.md) (also the gate's log, the acceptance guide, and the delivery report); what `conventions` may write superseded by [0039](0039-conventions-writes-gitignore.md) (also `.gitignore` files) and [0040](0040-profile-tools-at-conventions-versions.md) (also the files a profile installs its tools with)
- Date: 2026-11-21

## Context

The gate ([ADR 0028](0028-gate-interface.md)) checks every commit in its range as the developer's. In a task run by `deliver`, the range from the task's start to the developer's last commit also holds other roles' commits: QA's tests under QA's folders ([ADR 0017](0017-qa-tests-in-their-own-folder.md)), the security role's and the reviewer's reports, and `deliver`'s own state commits under `keyturn/internal/state/`. All of those are protected paths for the developer, so the gate would fail every task after the first QA step, and in each rework round (#84). `review` and `security-review` need the same list: they ask which commits in their range are another role's (#101, #107).

The task state file ([ADR 0011](0011-task-state-file.md)) keeps one commit per step, which is not enough once a step commits again in a later round. It also lives in the repository, under `keyturn/internal/`, and the developer's commits change the repository.

## Options considered

1. **A commit message trailer that each role writes** (for example `Keyturn-Role: qa`), which the gate reads. Needs no list, but every role is an agent running with the same tools, and the developer can write the same trailer on a commit of their own.
2. **Every role's commits listed in the task state file, read by the gate at the head.** One place, but the head is what the developer's commits produce: a developer who adds their own commit to the list takes it out of what the gate checks. Protecting the state file does not help when the check that would catch the edit reads the edited file.
3. **`deliver` records each role's commits in the state file, and passes the list to the gate, `security-review`, and `review` as arguments.** `deliver` knows each commit when the step that made it ends (the head before and after the step), so the list comes from the run itself, not from a file in the range. The state file stays the record that `resume` and people read.

## Decision

Option 3.

- When a role's step ends, `deliver` records every commit the step made (the commits between the head before and after it), with the role, in the task state file. The state file is a record: what is in it is never what decides which commits a check skips.
- The gate's range starts at the head before the task's first `implement` step, so spec, design, and conventions are before it.
- `deliver` runs the gate with `--others <role>:<commit>` for each commit in the range that is not the developer's: `qa`, `security-review`, `review`, or `deliver` (its own state commits), the step names of the task state file. It names them from what it recorded during the run. A resumed run has only the state file to name them from.
- The gate checks that each commit given with `--others` changes only what that role may write, so that a list read back from the state file cannot hide a developer commit:
  - `qa`: QA's folders (from the design at the base) and `keyturn/internal/test-report.md`;
  - `security-review`: `keyturn/internal/security-review.md`, and only the "Status" lines of `keyturn/internal/threat-model.md`;
  - `review`: `keyturn/internal/review.md`;
  - `deliver`: `keyturn/internal/state/**`.

  A commit that changes anything else, a commit given with `--others` that is not in the range, or, when `--others` is given, a merge commit in the range stops the gate (exit 2), and `deliver` asks a person: the list does not match the range it describes.
- With `--others`, the gate checks protected paths commit by commit, for every commit in the range that is not in `--others`, and not on the range's total diff, which holds the other roles' changes too. It checks suppressions commit by commit for every commit except the ones named as `security-review`, `review`, or `deliver`: QA's commits are checked too, so a suppression in QA's tests needs an ADR as the developer's does. A commit not in the list that changes the state file is a change to a protected path (`keyturn/internal/**`), so a developer commit that edits the list fails the gate. The test count and the profile checks still run on the whole head.
- A stop leaves a state commit that no later state commit has listed yet. When `resume` resumes a task past the head the first implement step started from, it checks that the head it resumes from changes only the state file, and, if so, lists it under "Commits" as `deliver`; its own resume commit is listed by `deliver`'s next state commit, before the next gate run. A head that changes anything else is not listed: it is a role's commit, which `deliver` records when that step ends.
- `deliver` passes the same list to `security-review` and `review`, which take another role's commits from whoever asked (#101, #107).

## Reasons

- A list read from the head is a list the developer can edit. Passing it from the run that made the commits keeps the check independent of the change being checked, which is the point of Guardrails 1.
- `deliver` already knows each step's commits when the step ends, so the list costs nothing to build and needs no new convention from the roles.
- Checking protected paths commit by commit lets QA's commits change QA's folders in any round, while a developer commit that changes them still fails, even if a later QA commit hides the change in the range's total diff.
- Keeping the state file as a record keeps `resume` and people able to see who made each commit, without making it a control.
- Checking each listed commit against what its role may write is what a resumed run can verify without trusting the state file. A commit's author and time are not used: both can be set to anything.

## Known gap

A developer who deliberately makes a commit that looks like another role's (it changes only what that role may write, such as a QA test that always passes) and adds it to the state file's list, with another commit that changes only the state file and so looks like `deliver`'s, can still get both skipped after a resume. That is planned deception, not a shortcut taken while making the checks pass, and no procedure inside the repository can tell it apart. It is a known gap of the MVP, closed by the sandbox and permission settings (#119), which keep the developer's step from writing outside its areas. Every delivery report made during the MVP lists it under "What was not verified".

## Consequences

- `templates/internal/state.md` lists every commit of a step, not one; the worked example's state file follows.
- `gates/gate.py` gets `--others <role>:<commit>`, checks each listed commit against its role's paths, checks protected paths and suppressions per commit for the rest, and stops on a merge in the range (the MVP never merges the default branch into a task branch, #60). Tests cover each case.
- `security-review` takes QA's commits from `deliver` instead of only the state file's "qa" row (#84), and its workaround is removed.
- `resume` and `deliver` read the list back from the state file after a stop, and rely on the gate's check of each listed commit.
- The gate run by hand, or in CI, without `--others`, still checks every commit as the developer's, as today.
