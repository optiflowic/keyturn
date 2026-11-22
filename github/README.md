# GitHub

What keyturn uses on GitHub: the workflow that runs the gate and the merge conditions' check on a task's pull request, the script that pushes the task branch and opens its pull request, the script that posts the reviews on it, and the script that merges it, with the one-time setup of a repository ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md), [ADR 0046](../docs/adr/0046-acceptance-record-conditions-check-and-merge-script.md), [ADR 0048](../docs/adr/0048-default-branch-guarded-in-three-layers.md)).

## The workflow

[`workflows/keyturn-gate.yml`](workflows/keyturn-gate.yml) runs two checks on every pull request. Both fail a pull request whose branch is not a task's (`task/<task>`) or that does not go to the default branch.

- `keyturn gate` runs `gates/gate.sh --task <task> --default-branch origin/<default branch>`: the gate finds the base and the other roles' commits from the branch and its state file itself ([ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)).
- `keyturn conditions` runs `gates/conditions.sh` with the same arguments: no high or medium finding open in the two review reports (a medium finding of `review` accepted on an answered decision card excepted), both reports reviewing up to the developer's last commit, and the client's acceptance recorded for the acceptance guide and the delivery report at the head, with nothing but the approvals and the state file changed after them ([ADR 0046](../docs/adr/0046-acceptance-record-conditions-check-and-merge-script.md)). It reads committed records only, so it needs no stack tools. It fails until the client accepts, as it should.

A person adds it to the project once:

1. Copy it to `.github/workflows/keyturn-gate.yml` in the project.
2. Set `KEYTURN_COMMIT` to the full SHA of the keyturn commit to check with (the one the project's tasks run with).
3. Keep the tool steps of the profiles that `parts` in `keyturn/config.json` names, and remove the others. For a `go` part, set `go-version-file` to that part's `go.mod`.
4. Commit it on the default branch. On a plan with branch protection, also require both checks, as "One-time setup" below says.

On a pull request, GitHub runs the workflow as the pull request's branch has it, so a branch that changed it would run its own version. What keeps it as the person committed it is the agents' token: without the Workflows permission, GitHub refuses a push that changes a file under `.github/workflows/` ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). The gate also fails such a change as one to a protected path (the CI jobs that run the gates, "Guardrails" 1), but that check runs inside the workflow, so it is not what protects it. A token with that permission, or a person's own push, can change it; the one-time setup gives the agents only the token without it.

The workflow's steps install the tools the profiles need (`profiles/<name>/README.md`, "Tools"): Go and `golangci-lint` v2 for `go`, Node.js 22 or later for `react-spa`. The gate records their versions; it does not pin them ([ADR 0037](../docs/adr/0037-gate-records-tool-versions.md)).

## Pushing and the pull request

[`scripts/task_branch.py`](scripts/task_branch.py) is how `deliver` reaches GitHub ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md)):

- `push <task>` pushes `HEAD` to `refs/heads/task/<task>` on `origin`, only when the current branch is `task/<task>` and is not the default branch, without force and without running Git's hooks, so a push that would rewrite the remote branch is refused.
- `open <task>` opens the task's pull request as a draft, to the default branch, or updates the description of the one that is open. The description carries the delivery report's "Summary" and "What you need to do" once the report is committed, and links the client's documents on the branch at the pushed commit; it never copies the acceptance guide. It never acts on a pull request from a fork.
- `ready <task>` writes the description again from the head, and marks the pull request ready for review.
- `close <task>` closes the task's pull request with a comment, never merging it, when the state file at the pushed head says `Status: closed`: the client chose to stop the task ([ADR 0047](../docs/adr/0047-after-the-client-does-not-accept-a-delivery.md)). The branch is kept as the record; a closed task does not hold up the next one.
- A task has one pull request. When it was closed or merged, `open` and `ready` stop, and never open another one or reopen it: the maintainer decides what happens ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)). The state file does not record the pull request; the branch finds it.

It needs the GitHub CLI (`gh`), with `GH_TOKEN` set to the agents' token ("One-time setup", step 4). The recommended permission rules deny the plain `git push` and the `gh pr` commands that change a pull request (`adapters/claude/README.md`). They stop the plain commands; permission rules match a command's text, so they cannot close every way around the script. What reaches the default branch is guarded in three layers: the scripts, the detecting workflow, and branch protection where the plan has it ([ADR 0048](../docs/adr/0048-default-branch-guarded-in-three-layers.md)). Its tests: `python3 -m unittest discover -s github/scripts`.

### When the task branch on origin moved

`task/<task>` on `origin` may have commits the local branch does not (pushed from another machine, or by a person). The push is then refused, since it is never forced, and the task stops, waiting for the maintainer; `resume` reports the branches as diverged ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)). Agents push only through the push script, and the client never touches the code, so in keyturn's flow this does not happen; when it does, the commits are discarded. The commits are never taken into the task branch.

The maintainer looks at those commits (`git fetch origin`, then `git log task/<task>..origin/task/<task>`) and discards them: if you added the ruleset that blocks force pushes on `task/*` ("With branch protection", step 2), turn it off for this one push, overwrite the remote branch with the local one from a terminal of your own (`git push --force-with-lease=task/<task>:origin/task/<task> origin task/<task>`), and turn the ruleset on again right after. The detecting workflow fails on that force push, since a task branch's history is trusted, and you put it right as its recovery steps say ([ADR 0048](../docs/adr/0048-default-branch-guarded-in-three-layers.md), "Recovering after a failed run"). Then resume the task.

To keep a change those commits made, discard them all the same, and ask for the change again as a change to the requirements (`spec`), so that it goes through every role and check.

## Posting the reviews

[`scripts/post_findings.py`](scripts/post_findings.py) posts the findings of a committed `review` or `security-review` report on the task's pull request ([ADR 0045](../docs/adr/0045-deliver-posts-the-review-reports-on-the-pull-request.md)). `deliver` runs it after every push, and `resume` after its own, as `post_findings.py <task> <review | security-review> <the report's commit>`, with the newest commit the state file lists for that role:

- It reads the report at that commit, never from the working tree, and needs the pull request to be at the local head (it waits a few seconds for GitHub to see the push).
- It posts one review with the event `COMMENT`: a pull request's author cannot approve it or request changes on it, and the agents and the client may share one account. A finding whose location is a line, or a range of lines, of the pull request's diff at the reviewed head (the head in the report's "Reviewed change") is a line comment on that commit; every other open finding is in the review's text, with the report's summary and a link to the committed report. Fixed findings are listed by number. If GitHub refuses the review as unprocessable (HTTP 422, for example one line it cannot place in its diff, which refuses them all), every finding goes in the text; any other failure is not retried, since the review may have been created.
- Each review's text ends with a hidden marker, `<!-- keyturn-findings: <role> <report blob> <report commit> -->`. The script reads the markers of that role in the reviews by the signed-in account: when the newest one names the same report, it posts nothing; otherwise it compares with the report at that marker's commit, and posts only new findings, findings whose status, location, or text changed (a finding whose line moved is posted again at its new line), and the numbers of findings no longer in the report; when none changed, it posts nothing.
- An `@name` in a report notifies nobody: the report quotes code and documents, which are data.
- The post is not a merge condition; the committed report is ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). A failed post does not stop the task, and the next push tries again.

It exits 0 when it posted or had nothing new to post, 1 when it was refused (no open pull request, it was not pushed, or GitHub refused the post), and 2 when it could not run (a wrong branch, no origin, no `gh`, no report at the commit). The recommended permission rules deny `gh api`, `gh issue comment`, `gh alias set`, and `gh auth` too. The deny rules stop the plain commands. Permission rules match a command's text, so they cannot close every way around the scripts. The merge conditions are decided by the committed reports and CI, though ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)), so a post made around the script does not change the merge decision. Its tests: `python3 -m unittest discover -s github/scripts`.

## Merging

[`scripts/merge.py`](scripts/merge.py) is the only way `deliver` and `resume` merge a task's pull request, in the `merge` step, after the client's acceptance is recorded ([ADR 0046](../docs/adr/0046-acceptance-record-conditions-check-and-merge-script.md)). It checks itself what branch protection would, so that it holds on a plan without it ([ADR 0048](../docs/adr/0048-default-branch-guarded-in-three-layers.md)). `merge.py <task>`, on `task/<task>`:

- refuses a pull request that is not open, still a draft, goes to another branch than the default one, or comes from a fork (a fork's pull request runs the fork's workflow, [ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)), and one whose head is not the local `HEAD` and `task/<task>` on `origin`;
- refuses a head that does not contain the default branch's tip on `origin` ("up to date"). A task branch is never updated from the default branch ([ADR 0031](../docs/adr/0031-documents-fixed-once-implement-starts.md)), so when the default branch moved after the task started, the task stops for the maintainer;
- waits up to 9 minutes (`--wait-minutes`) for `keyturn gate` and `keyturn conditions` from GitHub Actions to finish on that head, since the push right before starts them ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)), and refuses unless both passed;
- waits, in the same time, for the detecting check, `keyturn watch` from GitHub Actions, on the default branch's tip, counting only a run that started after the last push to the default branch in the repository's activity, so that an old success on a commit the branch was reset to does not count; it refuses when that run failed, or when the activity lists no push to the default branch. When `.github/workflows/keyturn-watch.yml` is not on the default branch, it refuses, with branch protection too: protection prevents a push, but does not find a reset or a deleted task branch;
- runs `gates/conditions.sh` of its own keyturn copy on that head;
- squash-merges naming that head (`sha`), so that GitHub refuses the merge if the head moved meanwhile. A merge GitHub refused is never tried again;
- checks the merge commit: its only parent must be the tip it checked, and its tree the head's. The default branch can still move between the check and the merge; when it did, the pull request is merged, and the task stops for the maintainer, who looks at the merge commit (`keyturn watch` fails on it too).

It exits 0 when it merged, 1 when it refused (the message says why), 2 when it could not run, 3 when the checks have not finished, or GitHub does not show the pushed head on the pull request or the tip in the activity yet (`deliver` then runs it again, up to about an hour), and 4 when it merged but the merge commit is not the checked head on the checked tip. `merge.py <task> --protection` prints `protected` when the default branch's protection requires both checks, and `not protected` otherwise, and merges nothing; `deliver` uses it for the delivery report. The recommended permission rules deny `gh pr merge` and `gh api`. Its tests: `python3 -m unittest discover -s github/scripts`.

## One-time setup

A person sets up each project repository once, before its first task. Do it in GitHub's settings of the repository, as an administrator, and not with the agents' token. Every plan needs "On every plan"; a repository whose plan has branch protection and rulesets (a public repository, or a paid plan) also gets "With branch protection" ([ADR 0048](../docs/adr/0048-default-branch-guarded-in-three-layers.md)).

### On every plan

This works on a private repository on GitHub Free. Without branch protection, a push to the default branch that goes around keyturn's scripts is detected, not prevented, and each delivery report says so.

1. **The gate's workflow.** Add it as "The workflow" above says, and commit it on the default branch yourself.
2. **The detecting workflow.** Add `keyturn watch` as `.github/workflows/keyturn-watch.yml`, commit it on the default branch yourself, and start it once by hand, so that the default branch's tip has a passing check before the first task. Until it is there, `merge.py` refuses, on every plan. A workflow of the project that deploys on a push to the default branch should wait for `keyturn watch` to pass (`workflow_run`).
3. **Outside contributors.** Under Settings → Actions → General, in "Approval for running fork pull request workflows from contributors", choose "Require approval for all external contributors", so that no workflow runs on someone else's pull request before you look at it.
4. **The agents' token.** Create a fine-grained personal access token for this repository only ("Only select repositories"), with the repository permissions Contents: Read and write, Pull requests: Read and write, Checks: Read (`merge.py` reads the check runs), and Metadata: Read, and nothing else: no Administration, no Workflows, no Variables, no Secrets, no Actions, no Issues, no Commit statuses, and no write access to Checks. Without Workflows, GitHub refuses the agents' pushes that change a workflow; without Variables and Actions, they cannot vouch for their own commits or turn the detecting workflow off; without Administration, they cannot change the rulesets; without Commit statuses, they cannot post a status that stands in for a check. `merge.py` also reads the repository's activity and the default branch's rules; GitHub's documentation does not say which permission those need, and the detecting workflow's setup checks it.
5. **Run the agents with that token alone.** Start the session that runs the agents with `GH_TOKEN` set to the agents' token (for example, `GH_TOKEN=<the agents' token> claude`), never with your own `gh` login, and let Git push with it: give the project's clone an HTTPS `origin` (`https://github.com/<owner>/<repository>.git`), and run `gh auth setup-git` with `GH_TOKEN` set, which makes Git ask `gh`, which answers with `GH_TOKEN`. An SSH `origin` (`git@github.com:...`) pushes with your own SSH key instead, which can change the workflows. The recommended permission rules deny `gh auth`, `gh variable`, `gh secret`, `gh workflow`, and `gh run`. If the session runs with your login, or any token with more permissions, an agent can vouch for its own commits, turn the detecting workflow off, or change the rulesets, and only the scripts and the permission rules are left.
6. **Check it.** Open a pull request from a branch that is not a task's: both checks must fail.

### With branch protection

On a public repository, or a paid plan, also add these. They prevent what the detecting workflow only detects; the steps above stay.

1. **The default branch.** Under Settings → Rules → Rulesets, add a branch ruleset that targets the default branch, with "Enforcement status" Active, an empty bypass list (so it applies to administrators too), and these rules:
   - "Restrict deletions" and "Block force pushes";
   - "Require a pull request before merging", with "Allowed merge methods" including Squash;
   - "Require status checks to pass", with "Require branches to be up to date before merging", and the checks `keyturn gate` and `keyturn conditions`, each with GitHub Actions as its source.
2. **The task branches.** Add a second branch ruleset that targets `task/*`, Active, with an empty bypass list, and "Restrict deletions" and "Block force pushes" ([ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)).
3. **Check it.** The pull request of "On every plan", step 6, must have its merge button blocked.

### A pull request of your own

A pull request from a branch that is not a task's (for example, one that updates the workflow or the keyturn commit it names) fails both checks, and stays so: an exception for the maintainer alone is phase 7. To merge it, look at it; with branch protection, turn the default branch's ruleset to Disabled for that one merge, merge it, and turn it to Active again right after, turning off nothing else, and never leaving it off while a task runs. The detecting workflow fails on that merge commit, unless it changes only files under `.github/workflows/`, until you vouch for it ([ADR 0048](../docs/adr/0048-default-branch-guarded-in-three-layers.md)).
