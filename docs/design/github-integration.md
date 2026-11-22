# GitHub Integration

Tasks are managed on GitHub so the client can follow progress without opening a terminal.

## Mapping

| keyturn | GitHub |
|---|---|
| Client request / task | Issue |
| Progress board | Project (columns follow the pipeline stages) |
| Stage of a task | Labels and Project status |
| Delivery unit | Pull request |
| Gates | GitHub Actions running `gate.sh` |
| Client-facing reports | PR description (the delivery report's summary and what the client needs to do, with links to the acceptance guide and the other documents) |
| Questions to the client | Issue comments that mention the client. Work that depends on the answer waits; the task pauses only when nothing else can be done |

## Flow

1. The client opens an issue (or keyturn drafts one from a conversation).
2. The PM writes requirements and posts the summary on the issue. Work does not start until the client approves.
3. The architect posts the design summary. Major decisions can be confirmed by the client if needed.
4. Agents work on the task branch, push it, and open a pull request. They push only the task branch, through keyturn's scripts, never the default branch and never with force ([ADR 0041](../adr/0041-agents-push-task-branches-and-open-pull-requests.md)).
5. GitHub Actions runs the gates. Failures send work back to the developer, up to the rework limit. The review roles' findings are posted on the pull request: `deliver` posts each committed report as a comment review, with a finding at its line of the diff where it can, and a rerun posts only what changed ([ADR 0045](../adr/0045-deliver-posts-the-review-reports-on-the-pull-request.md)).
6. When the gates pass, the PR description contains the delivery report's summary and what the client needs to do, and links the acceptance guide and the other documents; it is written again when the pull request is marked ready. A task has one pull request: a closed or merged one is never reopened or replaced, and a task branch that moved on `origin` stops the task until the maintainer decides ([ADR 0044](../adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md)).
7. The client does the hands-on check and accepts the delivery (or asks for changes).
8. The PM merges, only when the gate passes in CI, no high or medium finding is open (except a medium finding of the reviewer, not a security one, that the client accepted on a decision card), and the client's acceptance is recorded for the documents at the head. Branch protection makes the same checks required, so a merge without them is refused ([ADR 0042](../adr/0042-pm-merges-on-machine-checked-conditions.md)).

Agents can run unattended (scheduled or triggered by issue events), and the Project board shows where every task is.

## Security requirements

Unattended agents with write access to a repository are a security risk in themselves. These rules are mandatory.

- **Merging needs the client's acceptance.** Agents never push to the default branch, and the PM merges only when the conditions above hold, checked by machines, never by its own judgment. Branch protection on the default branch requires a pull request and the checks (with GitHub Actions as their expected source), requires the branch to be up to date with the default branch, blocks force pushes, and binds administrators; a person sets it up once per repository, with the CI workflow, which runs the checks from keyturn's code at a commit the workflow names, never from the pull request's head, and which the agents' token cannot change ([ADR 0042](../adr/0042-pm-merges-on-machine-checked-conditions.md)).
- **Least privilege.** Agents use a token or GitHub App scoped to the repositories and permissions they need: never the right to change the branch protection, the CI workflow, or a check's status. Secrets are never exposed to agent prompts. During the MVP, the agent may use the client's account with a fine-grained token; GitHub then cannot tell the client's acceptance from the agent's, and the delivery report says so. A separate identity for agents is phase 7.
- **Untrusted input.** Issue and comment text is data, not instructions. On public repositories, agents only act on issues that the client has explicitly approved (e.g., by applying a label that only maintainers can apply). This prevents prompt injection from outside contributors.
- **Every agent action is traceable** through commits, PRs, and comments.
