# 0049. The scripts read the runs of keyturn's workflows and their jobs, with Actions read, instead of check runs

- Status: accepted; for the gate's workflow, reading the newest of all its runs for the commit superseded by [0051](0051-draft-checks-fail-under-other-names.md)
- Date: 2026-11-23
- Supersedes: in [0046](0046-acceptance-record-conditions-check-and-merge-script.md), that the agents' token gets Checks read because `merge.py` reads the check runs; in [0048](0048-default-branch-guarded-in-three-layers.md), that the agents' token has Checks read, and that `merge.py` and `keyturn watch` read the checks `keyturn gate`, `keyturn conditions`, and `keyturn watch` as check runs from GitHub Actions

## Context

ADR 0046 gave the agents' fine-grained token Checks read, so that `merge.py` could read the check runs of `keyturn gate` and `keyturn conditions` on a task's head, and ADR 0048 had `merge.py` read `keyturn watch` on the default branch's tip the same way, and `keyturn watch` read the gate's checks on each merged head.

A fine-grained personal access token on github.com has no Checks permission: the token's settings do not offer it, and GitHub's documentation lists the check runs' endpoints for GitHub Apps. On a private repository on GitHub Free (#149), the agents' token got `403 Resource not accessible by personal access token` from `GET /repos/{owner}/{repo}/commits/{ref}/check-runs`, and so did an attempt to create a check run.

What constrains the answer:

- The token can have Actions read. With it, on that repository, the token read `GET /repos/{owner}/{repo}/actions/workflows/{file}/runs?head_sha=<sha>` and `GET /repos/{owner}/{repo}/actions/runs/{id}/jobs`, and every way to change a run or a workflow it tried was refused with 403: disabling the workflow, deleting a run, re-running one, starting one by hand, closing an issue, creating a repository variable, a commit status, or a check run.
- A run names its workflow file (`path`), its event, the head's SHA and repository, and its conclusion; each job of it has the job's name and conclusion. A job's name is the check's name (`keyturn gate`, `keyturn conditions`, `keyturn watch`), which a ruleset requires (ADR 0048, layer 3).
- A draft's pull request run was recorded with the conclusion `skipped`, and each of its jobs `skipped`.
- A run does not name the content of the workflow file it ran. On a pull request, GitHub runs the workflow as the pull request's merge with the base has it; on a push, as the pushed commit has it (a branch whose `keyturn-watch.yml` echoed a marker printed it in its run). What keeps the file as the person committed it is that the agents' token cannot push a change to it: GitHub refused such a push with "refusing to allow a Personal Access Token to create or update workflow ... without `workflow` scope".

## Options considered

1. **Commit statuses.** The token would need Commit statuses write to post them, and could then post a status that stands in for a check. Rejected in ADR 0042 for that reason.
2. **A GitHub App for the agents**, which can have Checks read. A separate identity is phase 7 (ADR 0042, ADR 0048).
3. **The runs of keyturn's workflows, and their jobs, through GitHub Actions' API, with Actions read**, telling the workflows apart by their files, and checking that the head changes no workflow file.

## Decision

Option 3.

- The agents' token has Contents and Pull requests write, and Actions and Metadata read, and nothing else. It never has Checks (not offered), Commit statuses, Workflows, Variables, Secrets, Issues, or Administration.
- A workflow passed on a commit when the newest of its runs for that commit (by run ID), read through `GET /repos/{owner}/{repo}/actions/workflows/{file}/runs?head_sha=<sha>` and kept only where the run's `path`, without what follows an `@`, is the workflow's file and its `head_sha` is the commit, has the status `completed` and the conclusion `success`, and each of the jobs it must have, read through `GET /repos/{owner}/{repo}/actions/runs/{id}/jobs`, concluded `success`. A skipped job, a missing job, and a skipped run do not pass.
- `merge.py` reads the gate's workflow, `.github/workflows/keyturn-gate.yml`, on the pull request's head: only runs of the `pull_request` event whose head repository is the repository itself, with the jobs `keyturn gate` and `keyturn conditions`. It reads the detecting workflow, `.github/workflows/keyturn-watch.yml`, on the default branch's tip, with the job `keyturn watch`, counting only runs that started after the last push in the activity (ADR 0048).
- `keyturn watch` reads the gate's workflow on each merged head the same way.
- Both refuse a head that changes a file under `.github/workflows/` against where it left the default branch (`merge.py` against the tip, `keyturn watch` against the merge commit's parent), so the gate's run on its pull request was the default branch's workflow. The agents cannot push such a head; a person's own push could, and then the merge waits for the maintainer.
- The workflow's own `GITHUB_TOKEN` in `keyturn watch` has `actions: read`, not `checks: read`.

## Reasons

- It works with the token GitHub offers to a person on every plan, and keeps the agents from changing what they read: Actions read was refused every write it was tried with.
- A run's file, event, and head repository tell the person's workflow from any other, which a check run's name alone did not; and a job's name is still the check's name, so a ruleset's required checks (layer 3) name the same thing.
- Checking the jobs, not only the run, keeps a run whose jobs were all skipped (a draft) from counting as a pass.

## Consequences

- `merge.py` and `keyturn watch` read runs and jobs; the one-time setup in `github/README.md` gives the agents' token Actions read instead of Checks read, and the detecting workflow `actions: read`.
- A token that had Checks read in an earlier setup is not needed to change; Checks is not offered for a fine-grained token anyway.
- A workflow's file name is fixed: renaming `keyturn-gate.yml` or `keyturn-watch.yml` in a project makes every merge wait.
- A branch protection ruleset still requires the checks by the jobs' names (ADR 0048, layer 3).
