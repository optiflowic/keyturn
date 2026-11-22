# GitHub

What keyturn uses on GitHub: the workflow that runs the gate on a task's pull request, and, later, the scripts that push the task branch, open the pull request, post the reviews, and merge, with the one-time setup of a repository ([ADR 0041](../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0042](../docs/adr/0042-pm-merges-on-machine-checked-conditions.md)).

## The gate's workflow

[`workflows/keyturn-gate.yml`](workflows/keyturn-gate.yml) runs the gate on every pull request, as one check named `keyturn gate` ([ADR 0043](../docs/adr/0043-gate-finds-a-task-s-range-in-ci.md)). It fails a pull request whose branch is not a task's (`task/<task>`) or that does not go to the default branch, and otherwise runs `gates/gate.sh --task <task> --default-branch origin/<default branch>`: the gate finds the base and the other roles' commits from the branch and its state file itself.

A person adds it to the project once:

1. Copy it to `.github/workflows/keyturn-gate.yml` in the project.
2. Set `KEYTURN_COMMIT` to the full SHA of the keyturn commit to check with (the one the project's tasks run with).
3. Keep the tool steps of the profiles that `parts` in `keyturn/config.json` names, and remove the others. For a `go` part, set `go-version-file` to that part's `go.mod`.
4. Commit it on the default branch, then, in the repository's branch protection for the default branch, require the check `keyturn gate`, with GitHub Actions as its expected source.

The workflow is a protected path for the developer (the CI jobs that run the gates, "Guardrails" 1), and the agents' token has no Workflows permission, so only a person changes it.

The workflow's steps install the tools the profiles need (`profiles/<name>/README.md`, "Tools"): Go and `golangci-lint` v2 for `go`, Node.js 22 or later for `react-spa`. The gate records their versions; it does not pin them ([ADR 0037](../docs/adr/0037-gate-records-tool-versions.md)).
