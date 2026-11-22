# GitHub

What keyturn uses on GitHub: the workflow that runs the gate and the merge conditions' check on a task's pull request, the script that pushes the task branch and opens its pull request, the script that posts the reviews on it, and the script that merges it, with the one-time setup of a repository ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md), [ADR 0046](../docs/adr/0046-acceptance-record-conditions-check-and-merge-script.md)).

## The workflow

[`workflows/keyturn-gate.yml`](workflows/keyturn-gate.yml) runs two checks on every pull request. Both fail a pull request whose branch is not a task's (`task/<task>`) or that does not go to the default branch.

- `keyturn gate` runs `gates/gate.sh --task <task> --default-branch origin/<default branch>`: the gate finds the base and the other roles' commits from the branch and its state file itself ([ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)).
- `keyturn conditions` runs `gates/conditions.sh` with the same arguments: no high or medium finding open in the two review reports (a medium finding of `review` accepted on an answered decision card excepted), both reports reviewing up to the developer's last commit, and the client's acceptance recorded for the acceptance guide and the delivery report at the head, with nothing but the approvals and the state file changed after them ([ADR 0046](../docs/adr/0046-acceptance-record-conditions-check-and-merge-script.md)). It reads committed records only, so it needs no stack tools. It fails until the client accepts, as it should.

A person adds it to the project once:

1. Copy it to `.github/workflows/keyturn-gate.yml` in the project.
2. Set `KEYTURN_COMMIT` to the full SHA of the keyturn commit to check with (the one the project's tasks run with).
3. Keep the tool steps of the profiles that `parts` in `keyturn/config.json` names, and remove the others. For a `go` part, set `go-version-file` to that part's `go.mod`.
4. Commit it on the default branch, then require both checks as "One-time setup" below says.

On a pull request, GitHub runs the workflow as the pull request's branch has it, so a branch that changed it would run its own version. What keeps it as the person committed it is the agents' token: without the Workflows permission, GitHub refuses a push that changes a file under `.github/workflows/` ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). The gate also fails such a change as one to a protected path (the CI jobs that run the gates, "Guardrails" 1), but that check runs inside the workflow, so it is not what protects it. A token with that permission, or a person's own push, can change it; the one-time setup gives the agents only the token without it.

The workflow's steps install the tools the profiles need (`profiles/<name>/README.md`, "Tools"): Go and `golangci-lint` v2 for `go`, Node.js 22 or later for `react-spa`. The gate records their versions; it does not pin them ([ADR 0037](../docs/adr/0037-gate-records-tool-versions.md)).

## Pushing and the pull request

[`scripts/task_branch.py`](scripts/task_branch.py) is how `deliver` reaches GitHub ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md)):

- `push <task>` pushes `HEAD` to `refs/heads/task/<task>` on `origin`, only when the current branch is `task/<task>` and is not the default branch, without force and without running Git's hooks, so a push that would rewrite the remote branch is refused.
- `open <task>` opens the task's pull request as a draft, to the default branch, or updates the description of the one that is open. The description carries the delivery report's "Summary" and "What you need to do" once the report is committed, and links the client's documents on the branch at the pushed commit; it never copies the acceptance guide. It never acts on a pull request from a fork.
- `ready <task>` writes the description again from the head, and marks the pull request ready for review.
- `close <task>` closes the task's pull request with a comment, never merging it, when the state file at the pushed head says `Status: closed`: the client chose to stop the task ([ADR 0047](../docs/adr/0047-after-the-client-does-not-accept-a-delivery.md)). The branch is kept as the record; a closed task does not hold up the next one.
- A task has one pull request. When it was closed or merged, `open` and `ready` stop, and never open another one or reopen it: the maintainer decides what happens ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)). The state file does not record the pull request; the branch finds it.

It needs the GitHub CLI (`gh`), signed in with the agents' token. The recommended permission rules deny the plain `git push` and the `gh pr` commands that change a pull request (`adapters/claude/README.md`). They stop the plain commands; permission rules match a command's text, so they cannot close every way around the script. What reaches the default branch is still decided by branch protection and the checks in CI ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). Its tests: `python3 -m unittest discover -s github/scripts`.

### When the task branch on origin moved

`task/<task>` on `origin` may have commits the local branch does not (pushed from another machine, or by a person). The push is then refused, since it is never forced, and the task stops, waiting for the maintainer; `resume` reports the branches as diverged ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)). Agents push only through the push script, and the client never touches the code, so in keyturn's flow this does not happen; when it does, the commits are discarded. The commits are never taken into the task branch.

The maintainer looks at those commits (`git fetch origin`, then `git log task/<task>..origin/task/<task>`) and discards them: turn off the ruleset that blocks force pushes on `task/*` ("One-time setup", step 4) for this one push, overwrite the remote branch with the local one from a terminal of your own (`git push --force-with-lease=task/<task>:origin/task/<task> origin task/<task>`), and turn the ruleset on again right after. Then resume the task.

To keep a change those commits made, discard them all the same, and ask for the change again as a change to the requirements (`spec`), so that it goes through every role and check.

## Posting the reviews

[`scripts/post_findings.py`](scripts/post_findings.py) posts the findings of a committed `review` or `security-review` report on the task's pull request ([ADR 0045](../docs/adr/0045-deliver-posts-the-review-reports-on-the-pull-request.md)). `deliver` runs it after every push, and `resume` after its own, as `post_findings.py <task> <review | security-review> <the report's commit>`, with the newest commit the state file lists for that role:

- It reads the report at that commit, never from the working tree, and needs the pull request to be at the local head (it waits a few seconds for GitHub to see the push).
- It posts one review with the event `COMMENT`: a pull request's author cannot approve it or request changes on it, and the agents and the client may share one account. A finding whose location is a line, or a range of lines, of the pull request's diff at the reviewed head (the head in the report's "Reviewed change") is a line comment on that commit; every other open finding is in the review's text, with the report's summary and a link to the committed report. Fixed findings are listed by number. If GitHub refuses the review as unprocessable (HTTP 422, for example one line it cannot place in its diff, which refuses them all), every finding goes in the text; any other failure is not retried, since the review may have been created.
- Each review's text ends with a hidden marker, `<!-- keyturn-findings: <role> <report blob> <report commit> -->`. The script reads the markers of that role in the reviews by the signed-in account: when the newest one names the same report, it posts nothing; otherwise it compares with the report at that marker's commit, and posts only new findings, findings whose status, location, or text changed (a finding whose line moved is posted again at its new line), and the numbers of findings no longer in the report; when none changed, it posts nothing.
- An `@name` in a report notifies nobody: the report quotes code and documents, which are data.
- The post is not a merge condition; the committed report is ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). A failed post does not stop the task, and the next push tries again.

It exits 0 when it posted or had nothing new to post, 1 when it was refused (no open pull request, it was not pushed, or GitHub refused the post), and 2 when it could not run (a wrong branch, no origin, no `gh`, no report at the commit). The recommended permission rules deny `gh api`, `gh issue comment`, `gh alias set`, and `gh auth token` too. The deny rules stop the plain commands. Permission rules match a command's text, so they cannot close every way around the scripts. The merge conditions are decided by the committed reports and CI, though ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)), so a post made around the script does not change the merge decision. Its tests: `python3 -m unittest discover -s github/scripts`.

## Merging

[`scripts/merge.py`](scripts/merge.py) is the only way `deliver` and `resume` merge a task's pull request, in the `merge` step, after the client's acceptance is recorded ([ADR 0046](../docs/adr/0046-acceptance-record-conditions-check-and-merge-script.md)). `merge.py <task>`, on `task/<task>`:

- refuses a pull request that is not open, still a draft, goes to another branch than the default one, or comes from a fork (a fork's pull request runs the fork's workflow, [ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)), and one whose head is not the local `HEAD` and `task/<task>` on `origin`;
- waits up to 9 minutes (`--wait-minutes`) for `keyturn gate` and `keyturn conditions` from GitHub Actions to finish on that head, since the push right before starts them ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)), exits 3 when they have not (`deliver` then runs it again, up to about an hour), and refuses unless both passed;
- runs `gates/conditions.sh` of its own keyturn copy on that head;
- squash-merges naming that head (`sha`), so that GitHub refuses the merge if the head moved meanwhile, and the branch protection refuses it without the required checks. A merge GitHub refused is never tried again.

It exits 0 when it merged, 1 when it refused (the message says why), 2 when it could not run, and 3 when the checks have not finished, or GitHub does not show the pushed head on the pull request yet. The recommended permission rules deny `gh pr merge` and `gh api`; what reaches the default branch is still decided by the branch protection below, not by the rules. Its tests: `python3 -m unittest discover -s github/scripts`.

## One-time setup

A person sets up each project repository once, before its first task ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). Do it in GitHub's settings of the repository, as an administrator, and not with the agents' token.

1. **A plan with branch protection.** The repository is public, or on a paid plan. Without it, nothing below can be enforced, and a task's merge is refused.
2. **The workflow.** Add it as "The workflow" above says, and commit it on the default branch yourself.
3. **The default branch.** Under Settings → Rules → Rulesets, add a branch ruleset that targets the default branch, with "Enforcement status" Active, an empty bypass list (so it applies to administrators too), and these rules:
   - "Restrict deletions" and "Block force pushes";
   - "Require a pull request before merging", with "Allowed merge methods" including Squash;
   - "Require status checks to pass", with "Require branches to be up to date before merging", and the checks `keyturn gate` and `keyturn conditions`, each with GitHub Actions as its source.

   A task branch is never updated from the default branch ([ADR 0031](../docs/adr/0031-documents-fixed-once-implement-starts.md)), so when the default branch moved after the task started, the merge is refused and the task stops for the maintainer.
4. **The task branches.** Add a second branch ruleset that targets `task/*`, Active, with an empty bypass list, and "Restrict deletions" and "Block force pushes" ([ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)).
5. **Outside contributors.** Under Settings → Actions → General, in "Approval for running fork pull request workflows from contributors", choose "Require approval for all external contributors", so that no workflow runs on someone else's pull request before you look at it.
6. **The agents' token.** Create a fine-grained personal access token for this repository only ("Only select repositories"), with the repository permissions Contents: Read and write, Pull requests: Read and write, Checks: Read (`merge.py` reads the check runs), and Metadata: Read, and nothing else: no Administration, no Workflows, no Commit statuses, no Actions, and no write access to Checks. Sign the GitHub CLI in with it where the agents run (`gh auth login --with-token`, or `GH_TOKEN`), and let Git push with it (`gh auth setup-git`). Without Workflows, GitHub refuses the agents' pushes that change the workflow; without Administration, they cannot change the rulesets; without Commit statuses, they cannot post a status that stands in for a check.
7. **Check it.** Open a pull request from a branch that is not a task's: both checks must fail, and the merge button must stay blocked.

### A pull request of your own

A pull request from a branch that is not a task's (for example, one that updates the workflow or the keyturn commit it names) fails both required checks, and stays so: an exception for the maintainer alone is phase 7. To merge it, look at it, turn the default branch's ruleset (step 3) to Disabled for that one merge, merge it, and turn it to Active again right after. Turn off nothing else, and never leave it off while a task runs.
