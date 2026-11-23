# 0043. In CI, the gate finds a task's base and the other roles' commits itself, as ADR 0032 says, and never trusts the state file at the head for the document roles

- Status: accepted; the ruleset on `task/*` as what keeps a task branch's history superseded by [0048](0048-default-branch-guarded-in-three-layers.md); the version of the state file the document roles' commits are read from, after a redo before `implement`, superseded by [0057](0057-documents-redone-before-implement-vouched-by-the-maintainer.md)
- Date: 2026-11-22

## Context

The gate passing in CI is one of the conditions for merging a task's pull request ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)). In a `deliver` session, `deliver` runs the gate with `--base` and one `--others <role>:<commit>` for each commit in the range that is not the developer's ([ADR 0029](0029-role-commits-passed-as-arguments.md), [ADR 0032](0032-gate-base-is-where-the-task-branch-left.md)). In CI there is no session: the workflow has only the pull request's branch, the default branch, and the files in the repository. Without `--others`, the gate checks every commit as the developer's, so a task's range would fail on the state commits and on QA's tests.

What constrains the answer:

- ADR 0032 fixes where the base and the roles come from: the base is where the task branch left the default branch, checked against the parent of the commit that added the task's state file; the commits of `spec`, `design`, and `conventions` are taken only from the state file as committed when the `conventions` step was recorded, never from a later version, since those roles write the documents the developer is judged against.
- The other roles' commits (`qa`, `security-review`, `review`, `deliver`) are, after a resume, read back from the state file, and the gate checks that each one changes only what its role may write (ADR 0029). That is the known gap ADR 0029 records: a developer who deliberately makes a commit that looks like another role's, and lists it, gets it past the gate.
- A required check that is skipped counts as passed on GitHub ("Required status checks must have a successful, skipped, or neutral status").

## Options considered

1. **Read every role from the state file at the head.** Simple, but the head is what the developer's commits produce: a later line naming a commit as `conventions`' would hide a change to a linter config. ADR 0032 rules this out.
2. **Read every role only from the state file at the `conventions` record.** The developer cannot change it, but the later roles' commits are not in it yet, so QA's tests and the reports would fail every task.
3. **Infer the later roles from the paths each commit changes.** Needs no list, but a developer commit that changes only QA's tests, the likeliest shortcut, would be taken for QA's and skipped.
4. **Do as ADR 0032 says**: the base from the branch, the document roles from the state file at the `conventions` record, and the later roles from the state file at the head, each checked against its role's paths, exactly as `deliver` does after a resume.

## Decision

Option 4. The gate gets a second way to be called, `gate.sh --task <task> --default-branch <ref> [--head <rev>]`, instead of `--base` and `--others`:

- **The base** is `git merge-base <default branch> <head>`. It must be the parent of the commit on the branch that added `keyturn/internal/state/<task>.md`; otherwise the gate stops (exit 2): a ref was moved, or the state file was added after other work.
- **The document roles.** The gate finds the oldest version of the state file in the range whose `conventions` row is `done`, and takes every commit its "Commits" lists as `spec`, `design`, `conventions`, or `deliver`, looking each hash up only among the commits before that version, never a later one whose hash a developer made start the same way. It never reads them from a later version. From now on, the state file lists full hashes; a short one written earlier is still read, with that lookup. If the `conventions` step is not recorded yet, the developer's work has not started, and the gate stops (exit 2).
- **The later roles.** From the state file at the head, the commits listed as `qa`, `security-review`, `review`, or `deliver`. A commit listed as `implement` is the developer's.
- **What the head's state file may not do.** A line at the head that names a commit as `spec`'s, `design`'s, or `conventions`' when the version at the `conventions` record did not, or that names one commit as two roles, stops the gate (exit 2). A listed commit that is not in the range stops it too.
- **The commit no line lists.** The newest state commit cannot list itself: when the head is listed by no line and changes only the state file, it is `deliver`'s. Any other commit that no line lists is the developer's, and is checked as such.
- The gate then runs as with `--base` and `--others`: every named commit must change only what its role may write (ADR 0029, ADR 0032, ADR 0033), the document roles' commits must all come before the developer's, and a merge in the range stops it.
- **The workflow**, `github/workflows/keyturn-gate.yml`, is a template a person copies into the project once. It checks out the pull request's head with its full history, and keyturn at a full commit SHA, installs the profiles' tools, and runs the gate as one check, `keyturn gate`. It has no job-level condition, since a skipped required check counts as passed: a pull request whose branch is not `task/<task>`, or that does not go to the default branch, fails the check. It reads only `contents`, pins every action to a full commit SHA, and passes branch names to the shell through environment variables, never by interpolating them into the command. GitHub runs a `pull_request` workflow as the pull request's branch has it, so what keeps the workflow (and the keyturn commit it names) as the person committed it is the agents' token, which has no Workflows permission: GitHub refuses a push that changes a workflow file without it ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)). The gate's protected-path check on the workflow runs inside that workflow, so it cannot be what protects it.

## Reasons

- The gate in CI checks the head the host will merge exactly as `deliver` checked it after a resume, so the two cannot disagree on the same branch, and it adds no new trust in the state file.
- Reading the document roles only from the version at the `conventions` record keeps ADR 0032's rule: no commit on the branch after that point can name a change to the documents, the linter configs, or `parts` as a document role's.
- Taking the later roles from the head, rather than from their paths, keeps an unlisted change to QA's tests the developer's: the developer would have to list it on purpose, which is the gap ADR 0029 already records.
- A check that fails instead of being skipped means a required check is never passed by a pull request it did not run on.

## Consequences

- `gates/gate.py` gets `--task` and `--default-branch`, with tests: a task's range passes, with the same result as `deliver`'s call on the same branch; the unlisted head state commit is `deliver`'s; an unlisted developer commit is checked; a developer commit relabelled as `qa`'s at the head, or a later line naming a document role, stops the gate; a task before `conventions` is recorded, and a base that does not match the state file's first commit, stop it.
- `github/` holds the workflow template and how a person adds it; #141 adds the rest of the one-time setup (branch protection, the agents' token).
- The gate fails in CI on every push before the `conventions` step is recorded, which only means that the pull request cannot be merged yet.
- ADR 0029's known gap is unchanged, and closed by the sandbox (#119).
- **Pull requests from forks.** A fork's pull request runs the fork's version of the workflow, which the agents' token does not bind, so its `keyturn gate` check can pass without the gate having run. So the PM's merge script refuses a pull request whose branch is not in the repository itself, and the one-time setup (#141) requires approval before a workflow runs on a pull request from an outside contributor.
- **The task branch's history.** The version of the state file at the `conventions` record is trusted because no commit after it can change it; a force push that rewrites the branch could. The one-time setup (#141) puts a ruleset on `task/*` that blocks force pushes and deletion, as on the default branch.
- **Other pull requests.** A pull request from a branch that is not a task's fails the required check, on purpose: a check that passed on other branches would be a way around it. A maintainer's pull request (for example, one that updates the workflow or the keyturn commit it names) is merged by turning the ruleset off for that merge and on again right after, as the setup's steps say (#141). An exception for the maintainer alone, which needs an organization's repository, is phase 7.
- When #141 adds the `merge` role's commits ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)), they are later roles, read from the head the same way.
