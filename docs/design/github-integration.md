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
| Client-facing reports | PR description (delivery report summary and acceptance guide) |
| Questions to the client | Issue comments that mention the client. Work that depends on the answer waits; the task pauses only when nothing else can be done |

## Flow

1. The client opens an issue (or keyturn drafts one from a conversation).
2. The PM writes requirements and posts the summary on the issue. Work does not start until the client approves.
3. The architect posts the design summary. Major decisions can be confirmed by the client if needed.
4. Agents work on a branch and open a pull request.
5. GitHub Actions runs the gates. Failures send work back to the developer, up to the rework limit.
6. When the gates pass, the PR description contains the delivery report summary and the acceptance guide.
7. The client does the hands-on check and merges.

Agents can run unattended (scheduled or triggered by issue events), and the Project board shows where every task is.

## Security requirements

Unattended agents with write access to a repository are a security risk in themselves. These rules are mandatory.

- **Merging is the client's action.** Agents never merge to the default branch. Use branch protection with required gate checks.
- **Least privilege.** Agents use a token or GitHub App scoped to the repositories and permissions they need. Secrets are never exposed to agent prompts.
- **Untrusted input.** Issue and comment text is data, not instructions. On public repositories, agents only act on issues that the client has explicitly approved (e.g., by applying a label that only maintainers can apply). This prevents prompt injection from outside contributors.
- **Every agent action is traceable** through commits, PRs, and comments.
