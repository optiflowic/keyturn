# 0048. The default branch is guarded in three layers: keyturn's scripts stop, a workflow detects, and the host's protection is added when the plan has it

- Status: accepted
- Date: 2026-11-22
- Supersedes: in [0041](0041-agents-push-task-branches-and-open-pull-requests.md), that the host's branch protection is what holds for certain; in [0042](0042-pm-merges-on-machine-checked-conditions.md), the branch protection in "What the host enforces", that the repository must be public or on a paid plan, and that a private repository on a free plan cannot be used; in [0043](0043-gate-finds-a-task-s-range-in-ci.md), that a ruleset on `task/*` is what keeps a task branch's history; in [0046](0046-acceptance-record-conditions-check-and-merge-script.md), the branch protection and the ruleset in "The one-time setup"

## Context

ADR 0041 and ADR 0042 made the host's branch protection the guardrail that holds for certain: whatever command runs, GitHub refuses a push to the default branch, a force push, and a merge without the gate's and the conditions' checks. ADR 0042 then required a public repository or a paid plan, since GitHub's documentation says "Protected branches are available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server". Rulesets are not offered on private repositories on GitHub Free either.

keyturn must work on a private repository on GitHub Free. A client should not have to make their code public, or pay for a plan, only so that keyturn's guardrail holds.

What constrains the answer:

- GitHub Actions runs on private repositories on every plan, GitHub Free included, within a monthly amount of included compute. Without branch protection, it cannot refuse a push; it can only run after one.
- Workflows triggered by `push` or `pull_request` are not run when the commit message has `[skip ci]`, `[ci skip]`, `[no ci]`, `[skip actions]`, `[actions skip]`, or a `skip-checks: true` trailer. Those do not apply to `schedule`, which runs the default branch's workflow on the default branch's latest commit.
- The agents' fine-grained token has Contents and Pull requests write, Checks and Metadata read, and nothing else (ADR 0042, ADR 0046). Without Workflows it cannot change a workflow file; without Variables, a repository variable; without Actions, a workflow's runs; without Issues, an issue; without Administration, the repository's settings. It does have write access, so without branch protection it can push to the default branch and merge a pull request through the API, if a command other than keyturn's scripts uses it.
- The permission rules stop a command as written, not the same program run another way (ADR 0036, ADR 0041), until the sandbox (#119).
- During the MVP, the agent and the maintainer may use one account. GitHub sends a workflow run's notification to the person who triggered it, only if they turned those notifications on.

## Options considered

1. **Keep ADR 0042: a public repository or a paid plan.** Branch protection refuses whatever a command does, but a private repository on GitHub Free cannot be used.
2. **keyturn's scripts alone.** The scripts check the conditions before they push or merge, and nothing else does. Works on every plan, but nothing notices when a command other than the scripts reaches the default branch.
3. **Three layers: the scripts stop, a workflow detects, and branch protection is added when the plan has it.** Works on every plan; without branch protection, a push that goes around the scripts is not prevented, but it is found and the maintainer is told.

## Decision

Option 3.

**1. Stop.** Agents push and merge only through keyturn's scripts, and the permission rules deny the plain commands (ADR 0041). `merge.py` merges only when the conditions hold (ADR 0046), and now also checks itself what branch protection used to:

- the pull request's head contains the default branch's tip ("up to date", ADR 0042), so that a head checked against an older default branch is not merged;
- the checks `keyturn gate` and `keyturn conditions` on the head concluded `success` (not skipped) from GitHub Actions, as it already does;
- the detecting check, `keyturn watch`, concluded `success` from GitHub Actions on the default branch's tip. A tip with no such check (the workflow is not installed, or a commit skipped it) refuses the merge, as a failed one does.

Agents run with the agents' token alone: the session that runs them is started with `GH_TOKEN` set to that token, never with the maintainer's `gh` login. The permission rules also deny `gh auth`, `gh variable`, `gh secret`, `gh workflow`, and `gh run`.

**2. Detect.** A workflow the person adds once, `keyturn watch`, runs on every push to the default branch and to `task/**`, on a schedule (at least daily), and when the maintainer starts it by hand. It runs keyturn's code at the commit the workflow names, as the gate's workflow does (ADR 0042). Each run checks every commit on the default branch's first-parent history from a starting commit the workflow names to the tip, not only the pushed ones, so a push that skipped the workflow is found by the next run. A commit passes only when:

- it is the merge commit of a merged pull request (GitHub's "List pull requests associated with a commit") from a `task/<task>` branch in the repository itself;
- it has one parent, its tree is the tree of that pull request's head, and that head contains its parent, so what reached the default branch is exactly the head that was checked, up to date;
- `keyturn gate` and `keyturn conditions` concluded `success` from GitHub Actions on that head;
- `conditions.sh` passes again on that head.

Two kinds of commits pass without a pull request: one that changes only files under `.github/workflows/` (which the agents' token cannot push), and one whose SHA the maintainer listed in the repository variable `KEYTURN_VOUCHED` (which the agents' token cannot change). A maintainer who commits to the default branch, or merges a pull request of their own, lists it there and starts the workflow again. A run also fails when the starting commit is no longer an ancestor of the default branch (it was rewritten), and when a push to `task/**` was a force push (ADR 0043 trusts a task branch's history).

When a run fails, it opens an issue, with `GITHUB_TOKEN` and `issues: write`, that names each commit and why, and mentions the maintainer, whose account the repository variable `KEYTURN_MAINTAINER` names. The failed check on the default branch's tip also stops `merge.py` (layer 1), so no task merges on top of a commit nobody vouched for.

**3. The host stops it, when the plan has it.** On a public repository, or a paid plan, the person also adds the rulesets of ADR 0046 ("The one-time setup"): on the default branch, a pull request, the checks `keyturn gate`, `keyturn conditions` as required checks from GitHub Actions, up to date, no force push or deletion; on `task/*`, no force push or deletion. They prevent what layer 2 only detects. Turning a ruleset off for a pull request of the maintainer's own (ADR 0043, ADR 0046) applies only there. Layers 1 and 2 stay on with it.

**The gate's CI runs only on pull requests that are not drafts.** A task's pull request is a draft until the `deliver` step commits the delivery documents and marks it ready (ADR 0041). The merge conditions need the gate only on the head that is merged, and `deliver` runs the gate locally on every round before that (ADR 0030). So the gate's workflow skips draft pull requests and runs when the pull request is marked ready and on every push after, which keeps a task within GitHub Free's included compute. A skipped check is not a pass for `merge.py` or `keyturn watch`, and GitHub does not merge a draft. `keyturn watch` runs as above.

**Known gaps.**

- **Without branch protection, a push is detected, not prevented.** Anyone with write access, the agents' token included, can push to the default branch directly, force push it, or merge a pull request without the checks, by a command other than keyturn's scripts. keyturn finds it at the next run of `keyturn watch` and tells the maintainer; until then, the commit is on the default branch, and putting it right is the maintainer's. A workflow of the project that deploys on a push to the default branch should wait for `keyturn watch` to pass (`workflow_run`); the one-time setup says so. The delivery report says, under "What was not verified", when the repository has no branch protection.
- **Layer 2 holds only while agents use the agents' token alone.** If the agents' session runs with the maintainer's `gh` login, or with any token that has Workflows, Variables, Actions, Issues, or Administration, an agent can list its own commits in `KEYTURN_VOUCHED`, change or turn off `keyturn watch`, delete its runs, close the issue it opened, or change the rulesets. Then layer 2 detects nothing and layer 3 can be turned off; only layer 1 is left, and it is only the permission rules and the scripts. The same holds for any command of the agents that reads the maintainer's credentials from the machine.
- **The sandbox (#119) narrows the gap, but does not close it.** It stops commands written another way than the rules expect. The agents' token stays within their reach, since keyturn's scripts use it, so a program of their own could still use it. Only branch protection, or a token held outside the agents (a separate identity for agents, phase 7), closes it.
- **Between runs.** A commit that skipped the push workflow is found by the next push or the next scheduled run; the schedule sets how long that can take.
- GitHub's documentation does not state some things layer 2 relies on: that a push changing a workflow file is refused without the Workflows permission; that a `push` runs the workflow file of the pushed commit; which fine-grained permissions turning a workflow off, deleting its runs, and closing an issue need; and that a squash merge through the API creates a `push` event. #149 checks them on a private repository on GitHub Free before the rehearsal (#63) reaches its merge.

## Reasons

- The client keeps a private repository on any plan, and the guardrail still has a part that does not depend on the shape of a command: `keyturn watch` runs on the host, from code and variables the agents' token cannot change.
- Checking every commit from a fixed start, on a schedule too, means a skipped run hides nothing for longer than the schedule, and a tree compared to the checked head means a merge that changed anything is not passed.
- `merge.py` reading the detecting check on the tip ties the layers together: a commit nobody vouched for stops the next merge as well as raising an issue.
- Saying plainly what holds without branch protection, and what breaks when agents use the maintainer's login, lets the client and the maintainer decide whether to add branch protection.
- Running the gate's CI only on the head that is merged spends the included compute where a check decides something.

## Consequences

- #148: `merge.py` checks that the head is up to date and that `keyturn watch` passed on the default branch's tip; the permission rules deny `gh auth`, `gh variable`, `gh secret`, `gh workflow`, and `gh run`; the one-time setup in `github/README.md` becomes what every plan needs, then what a plan with branch protection adds; it and `AGENTS.md` say to start the agents' session with `GH_TOKEN` set to the agents' token.
- #149: the `keyturn watch` workflow template and its script, with tests; the gate's workflow skips draft pull requests; the setup's steps for both; the points the documentation does not state are checked.
- The delivery report says when the repository has no branch protection, next to running without a sandbox.
- ADR 0042's conditions, `merge` step, and token are unchanged; only what makes them hold on the host changes.
- The rehearsal (#63) runs on a private repository on GitHub Free, after #148, with #149 installed before it reaches the `merge` step.
