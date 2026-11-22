# 0041. Agents push the task branch, open the pull request, and post the reviews on it, through scripts; never the default branch, never a force push

- Status: accepted
- Date: 2026-11-22
- Supersedes: [0036](0036-minimal-permission-rules.md); and the part of [0033](0033-delivery-documents-from-the-records.md) that says a person opens the pull request and merges it

## Context

keyturn works with the client on the Git host (GitHub first, other hosts later). The client reads only the documents: the requirements, the design summary and the decision cards, the acceptance guide, and the delivery report. The code goes to the client as a pull request, the review roles review it there, and the PM merges it when nothing stops it ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)).

The MVP so far did the opposite: no role and not `deliver` pushed, opened a pull request, or merged; a person did all three from a terminal of their own ([ADR 0033](0033-delivery-documents-from-the-records.md), [ADR 0036](0036-minimal-permission-rules.md)). That leaves the client doing a developer's chores, and leaves the reviews out of the place where the code is.

What constrains the answer:

- The guardrail stays: destructive commands and direct pushes to the default branch are blocked ("4. The environment limits the damage" in `docs/design/guardrails.md`). A force push rewrites what others already have, so it is blocked too.
- A Claude Code permission rule matches the text of a command, not the branch it acts on: a bare `git push` on the default branch cannot be told from the same command on a task branch (ADR 0036). Deny rules win over allow rules, so a rule cannot allow `git push` on task branches only.
- The rules stop the command as written, not the same program run another way (ADR 0036). What blocks a push to the default branch for certain is the host's branch protection.
- During the MVP, the agent and the client may use one account on the host, so the host cannot tell which of them acted.

## Options considered

1. **Keep ADR 0036: a person pushes, opens, and merges.** Nothing new to build, but the client handles branches and pull requests, and the reviews never reach the pull request.
2. **Let agents run `git push` and `gh` as they like, with deny rules for the default branch's name and the force flags.** Little to build, but a bare `git push`, a refspec such as `HEAD:main`, or a `+` in a refspec slips through text rules, and every project's default branch has its own name.
3. **Agents act on the host only through keyturn scripts that each do one thing, the plain commands stay denied, and the host's branch protection is what holds for certain.** The push script pushes `HEAD` to `refs/heads/task/<task>` only, after checking that the current branch is that task branch, and never with force; another script opens or updates the task's pull request; another posts a review's findings on it. A script is code to write and test, but it checks the branch, which a rule cannot.

## Decision

Option 3.

- **Agents may**: push the task branch `task/<task>`; open the pull request from it to the default branch, and update it; post the findings of `review` and `security-review` on it, as comments.
- **Agents may not**: push to the default branch, push with force (or any refspec that rewrites a branch), delete a remote branch, or push any other branch.
- **How**: through keyturn's scripts for the host, in `github/` ("Repository Layout"). The skills say only "push the task branch", "open the pull request", and "post the findings", not which host or tool. The recommended permission rules (`adapters/claude/permission-settings.json`) keep denying the plain `git push` and `gh pr merge`, and the commands that discard work, as ADR 0036 listed them; the scripts are the only way to the host.
- **When**: `deliver` pushes the task branch after every state commit, so that the work is on the host at every step boundary and a task can be resumed on another machine ("Resuming Work"). It opens the pull request as a draft with its first push, the reviews post their findings on it, and `deliver` marks it ready for the client, with the same script, when the acceptance guide and the delivery report are committed. Its description links to the client's documents; the files stay the source of truth ("Documents").
- **What holds for certain** is on the host, set once by a person before the first task ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)): branch protection on the default branch (a pull request is required, force pushes are blocked, and administrators are bound too), and a token for the agent that cannot change that protection or the CI workflow.
- The rules are still in the person's local settings, as ADR 0036 decided, and are still checked by hand before the end-to-end run (#63) until #119 decides how they are checked automatically.

## Reasons

- The client sees the work where it is delivered, and reads the reviews next to the code, without handling branches.
- A script can check the current branch and the target before pushing; a text rule cannot. Keeping the plain commands denied means the agent does not have two ways to the host, one checked and one not.
- Branch protection is enforced by the host whatever command ran, so the guardrail no longer depends on the shape of a command.
- Pushing at every step boundary keeps the task's state outside the machine, as "Resuming Work" asks.

## Consequences

- #139 builds the push and pull request scripts, the permission rules, and the steps in `deliver`; #140 posts the reviews.
- ADR 0036's options and reasons still explain the deny list; its decision that no step pushes is replaced. ADR 0033's procedure stays, except its last sentence.
- A command written another way (for example, `git -C . push`), or a script of the agent's own, is still not stopped by the rules during the MVP; branch protection stops it reaching the default branch, and the sandbox (#119) closes the rest.
- Other hosts (GitLab and others) are not in the MVP. The same decision applies to them: their scripts go next to GitHub's, and the skills do not change.
- Pushing needs network access and the agent's token during the run; the delivery report already says how the agents ran.
