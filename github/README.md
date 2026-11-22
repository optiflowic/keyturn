# GitHub

What keyturn uses on GitHub: the workflow that runs the gate on a task's pull request, the script that pushes the task branch and opens its pull request, and, later, the scripts that post the reviews and merge, with the one-time setup of a repository ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)).

## The gate's workflow

[`workflows/keyturn-gate.yml`](workflows/keyturn-gate.yml) runs the gate on every pull request, as one check named `keyturn gate` ([ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)). It fails a pull request whose branch is not a task's (`task/<task>`) or that does not go to the default branch, and otherwise runs `gates/gate.sh --task <task> --default-branch origin/<default branch>`: the gate finds the base and the other roles' commits from the branch and its state file itself.

A person adds it to the project once:

1. Copy it to `.github/workflows/keyturn-gate.yml` in the project.
2. Set `KEYTURN_COMMIT` to the full SHA of the keyturn commit to check with (the one the project's tasks run with).
3. Keep the tool steps of the profiles that `parts` in `keyturn/config.json` names, and remove the others. For a `go` part, set `go-version-file` to that part's `go.mod`.
4. Commit it on the default branch, then, in the repository's branch protection for the default branch, require the check `keyturn gate`, with GitHub Actions as its expected source.

On a pull request, GitHub runs the workflow as the pull request's branch has it, so a branch that changed it would run its own version. What keeps it as the person committed it is the agents' token: without the Workflows permission, GitHub refuses a push that changes a file under `.github/workflows/` ([ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)). The gate also fails such a change as one to a protected path (the CI jobs that run the gates, "Guardrails" 1), but that check runs inside the workflow, so it is not what protects it. A token with that permission, or a person's own push, can change it; the one-time setup (#141) gives the agents only the token without it.

The workflow's steps install the tools the profiles need (`profiles/<name>/README.md`, "Tools"): Go and `golangci-lint` v2 for `go`, Node.js 22 or later for `react-spa`. The gate records their versions; it does not pin them ([ADR 0037](../docs/adr/0037-gate-records-tool-versions.md)).

## Pushing and the pull request

[`scripts/task_branch.py`](scripts/task_branch.py) is how `deliver` reaches GitHub ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md)):

- `push <task>` pushes `HEAD` to `refs/heads/task/<task>` on `origin`, only when the current branch is `task/<task>` and is not the default branch, without force and without running Git's hooks, so a push that would rewrite the remote branch is refused.
- `open <task>` opens the task's pull request as a draft, to the default branch, or updates the description of the one that is open. The description carries the delivery report's "Summary" and "What you need to do" once the report is committed, and links the client's documents on the branch at the pushed commit; it never copies the acceptance guide. It never acts on a pull request from a fork.
- `ready <task>` writes the description again from the head, and marks the pull request ready for review.
- A task has one pull request. When it was closed or merged, `open` and `ready` stop, and never open another one or reopen it: the maintainer decides what happens ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)). The state file does not record the pull request; the branch finds it.

It needs the GitHub CLI (`gh`), signed in with the agents' token. The recommended permission rules deny the plain `git push` and the `gh pr` commands that change a pull request, so the script is the only way (`adapters/claude/README.md`). Its tests: `python3 -m unittest discover -s github/scripts`.

### When the task branch on origin moved

`task/<task>` on `origin` may have commits the local branch does not (pushed from another machine, or by a person). The push is then refused, since it is never forced, and the task stops, waiting for the maintainer; `resume` reports the branches as diverged ([ADR 0044](../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)). The maintainer looks at those commits (`git fetch origin`, then `git log task/<task>..origin/task/<task>`) and chooses:

- **Discard them.** Turn off the ruleset that blocks force pushes on `task/*` (from the one-time setup, #141) for this one push, overwrite the remote branch with the local one from a terminal of your own (`git push --force-with-lease=task/<task>:origin/task/<task> origin task/<task>`), and turn the ruleset on again right after. Then resume the task.
- **Take them in.** `deliver` takes them into the task branch, and the gate checks them as the developer's commits, since they are no role's. This is built in #141; until then, discard them, or set the task aside.
