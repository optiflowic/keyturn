# 0032. The gate's base is where the task branch left the default branch, and the document roles' commits are named too

- Status: accepted; what a `conventions` commit may change superseded by [0039](0039-conventions-writes-gitignore.md) (also `.gitignore` files) and [0040](0040-profile-tools-at-conventions-versions.md) (also the files a profile installs its tools with); the state file version the document roles' commits are read from, after a redo before `implement`, superseded by [0057](0057-documents-redone-before-implement-vouched-by-the-maintainer.md); what a `spec` commit may change superseded by [0066](0066-requirements-ask-about-the-look-once.md) (also the decision cards)
- Date: 2026-11-21
- Supersedes: part of [0029](0029-role-commits-passed-as-arguments.md) (the gate's range starting at the head before the first `implement` step) and part of [0028](0028-gate-interface.md) (the design and the ADRs read at the base)

## Context

[ADR 0029](0029-role-commits-passed-as-arguments.md) starts the gate's range at the head the task's first `implement` step started from, so that `spec`, `design`, and `conventions` are before it, and names the other roles' commits inside the range with `--others`. It also decides that what the task state file says is never what decides which commits a check skips, because the developer's commits change the repository the state file is in.

`deliver` (#60) has to find that start again after a resume, and the only record of it is the state file: the first commit under "Commits", or the commits after the `conventions` row's commit. Both are read at the head. A developer who rewrites "Commits" (or the `conventions` row) moves the start later, and the range shrinks: their own commits, and the commit that rewrote the state file, fall before it and are never checked. A state-only commit made before the step that finds it would even be taken for one of `deliver`'s own. That is the hole ADR 0029 closed for the list of commits, open again for the base.

## Options considered

1. **Keep the start from the state file**, and check after the fact that the commits before it are spec's, design's, and conventions'. The check would need the same list it is meant to verify.
2. **Record the start outside the repository** (for example, in the session). Lost on every stop, which is when it is needed.
3. **Start the range where the task branch left the default branch**, `git merge-base <default branch> HEAD`, which no commit on the task branch can move: the default branch is never merged into a task branch ([ADR 0031](0031-documents-fixed-once-implement-starts.md)). Name the commits of `spec`, `design`, and `conventions` with `--others` too, as roles of their own, each checked against what it may write, like the others in ADR 0029.

## Decision

Option 3.

- `deliver` runs the gate with `--base $(git merge-base <default branch> HEAD)`, and gives `security-review` and `review` the same base. The test count is compared with that base too. Since a ref can be moved by anyone who can write to the repository, `deliver` checks the merge base against the branch's history (the parent of the commit that added the task's state file) and stops when they differ.
- From the task's first commit on, every commit is listed under "Commits" in the task state file, and `deliver` names every one that is not the developer's to the gate, the reviews included. It takes the `spec`, `design`, and `conventions` commits only from the state file as committed when the `conventions` step was recorded, which no later commit can change: those roles may write the very documents the developer is judged against, so a later line naming one of them is never trusted. The roles named by step: `spec`, `design`, `conventions`, `qa`, `security-review`, `review`, `deliver`.
- The gate checks that each named commit changes only what its role may write, and stops (exit 2) otherwise:
  - `spec`: `keyturn/client/requirements.md`, `keyturn/client/approvals.md`, `.gitattributes` at the top, and `keyturn/config.json` (created by `project-config` when the task starts);
  - `design`: `keyturn/internal/design.md`, `keyturn/internal/threat-model.md`, `keyturn/internal/adr/**`, `keyturn/client/design-summary.md`, and `keyturn/client/decision-card-*.md`;
  - `conventions`: `keyturn/internal/conventions.md`, `keyturn/internal/adr/**`, each profile's linter configs (its `protected` patterns), and `keyturn/config.json` (`parts`, added before `conventions` runs);
  - the others as in ADR 0029.
- The commits named as `spec`, `design`, or `conventions` all come before every commit that is not named; one that comes after stops the gate (exit 2), since the documents are fixed before the developer's work (ADR 0031). The gate reads QA's folders from the design, and the ADRs that approve a suppression, at the newest of them (or at the base when none is named, as before), so that the developer's commits cannot change what they are judged against.
- `security-review` and `review` read the documents they judge against at that same commit (the newest one `deliver` names as `spec`, `design`, or `conventions`), and a document change in such a commit is not a finding.

## Reasons

- The merge base is a fact of the branch, not a line in a file the developer can edit, so the range cannot be shrunk from inside it. It does not move during a task, since the default branch is never merged in.
- Naming the document roles' commits and checking what each one changes keeps the rule of ADR 0029: a named commit is skipped only if it does what its role does. A list read back from the state file after a resume still cannot hide a developer's change, except by the planned deception ADR 0029 already lists as a known gap.
- Reading the documents at the newest document commit gives the gate and the reviews the same documents the developer was given, without trusting where the state file says the work started.

## Consequences

- `gates/gate.py` knows the roles `spec`, `design`, and `conventions`, the order rule, and reads the design and the ADRs at the newest document commit. Without `--others`, it behaves as before.
- `templates/internal/state.md` lists every commit from the task's first one, and `resume` lists the state commit it resumes from whenever no line lists it.
- `skills/deliver/SKILL.md` drops the start it found from the state file. `security-review` and `review` take the documents' commit as described above.
- The worked example's state file lists the commits of `spec`, `design`, and `conventions`, and its reviews start at the merge base.
- A gate run by hand or in CI, without `--others`, is unchanged.
