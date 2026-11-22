# 0042. The PM merges the pull request when machine-checked conditions hold, and the host's branch protection refuses a merge without them

- Status: accepted
- Date: 2026-11-22
- Supersedes: in [0030](0030-deliver-rework-loop.md), that every open medium finding sends the work back (a medium finding of `review` that the client accepted on a decision card does not); the MVP's list in [0025](0025-mvp-first.md), and "automatic merging" among its later items: delivery through a pull request, the gate in CI, and the PM's merge are part of the MVP

## Context

A task's delivery ends at a merged pull request ("Delivery Scope"). Agents now push the task branch and open the pull request ([ADR 0041](0041-agents-push-task-branches-and-open-pull-requests.md)); the question is who merges it, on what conditions, and what makes those conditions hold for certain.

What constrains the answer:

- The design said "Merging is the client's action" ("Security requirements" in `docs/design/github-integration.md`), so that agents never merge on their own. What it protects is that nothing reaches the default branch without the gates passing and the client accepting the delivery ([Principles](../design/principles.md) 10). Pressing the button is not the point.
- The client decides from the documents, not the code ([Principles](../design/principles.md) 1), and no answer is not consent ([ADR 0009](0009-no-answer-is-not-consent.md)).
- `deliver` already sends the work back on a failing gate, a failing test, and a high or medium finding ([ADR 0030](0030-deliver-rework-loop.md)), but nothing checks that the head being merged is the one that passed.
- During the MVP, the agent and the client may use the same account on GitHub. GitHub's documentation says that "Pull request authors cannot approve their own pull requests", so a required approval cannot be the client's acceptance. It also says that "Any person or integration with write permissions to a repository can set the state of any status check", unless the required check names the app expected to set it ("If the status is set by any other person or integration, merging won't be allowed"). Branch protection does not bind administrators unless "Do not allow bypassing the above settings" is on. On a personal account, protected branches in a private repository need a paid plan.

## Options considered

1. **The client merges**, as the design said. The client has to open the pull request and judge whether it may be merged; nothing checks the conditions for them.
2. **The PM merges on its own judgment** after the reviews. Fewer steps for the client, but an agent decides, which the guardrails do not allow.
3. **The PM merges only when fixed conditions hold, checked by machines in CI, and the host's branch protection makes the same checks required**, so that a merge without them is refused, whoever tries it.

## Decision

Option 3.

**The conditions.** A task's pull request is merged only when all three hold for its head commit:

1. **The gate passes in CI.** The gate runs on the pull request, finding the base and the other roles' commits itself as [ADR 0032](0032-gate-base-is-where-the-task-branch-left.md) says, without trusting the state file at the head for them (#138 records how in an ADR of its own).
2. **No high or medium finding is open.** In `keyturn/internal/review.md` and `keyturn/internal/security-review.md`, no finding of high or medium severity has "Status: open". Low findings do not stop the merge; they are in the delivery report. A medium finding of `review` (design fit, readability, conventions: nothing about security) does not stop it when the client accepted it on an answered decision card that also offered fixing it; the card says what is left as it is and why, and an unanswered card accepts nothing ([ADR 0009](0009-no-answer-is-not-consent.md)). The report records it as "Status: accepted: decision card <n>"; only the reviewer sets it, after checking that the card is answered and that the finding is still as the card described it. Such a finding is not open: it sends no work back, which replaces [ADR 0030](0030-deliver-rework-loop.md)'s rule for it, and it does not stop the merge, and it is listed under "Remaining risks" in the delivery report. A security finding is never accepted this way: a medium or high finding of `security-review`, or a threat of medium or higher severity in the threat model, is fixed. [ADR 0010](0010-accepting-the-risk-of-a-low-threat.md) is unchanged: only the risk of a low threat may be accepted. When the rework limit is reached with a security finding still open, the task stops for the maintainer, as ADR 0030 says. A card asked for during a task follows "Questions for the maintainer" in `deliver` ([ADR 0031](0031-documents-fixed-once-implement-starts.md)).
3. **The client accepted the delivery.** During the MVP, the acceptance is recorded in `keyturn/client/approvals.md` like the requirements' approval ([ADR 0008](0008-approval-records-in-a-separate-file.md), [ADR 0012](0012-stable-approval-hashes.md)): one row with the SHA-256 of the acceptance guide and the delivery report at the head (and of the translations the client read, in English-only mode), and the client's answer. A changed document makes the acceptance stale. No answer is not acceptance.

**Who merges, and in what order.** The PM role, in a new last step of `deliver`, `merge`, after the `deliver` step:

1. The `deliver` step commits the acceptance guide, the delivery report, and the gate's log, as ADR 0033 says, and the state file records it. `deliver` pushes, and marks the pull request ready for the client with the pull request script ([ADR 0041](0041-agents-push-task-branches-and-open-pull-requests.md)).
2. `merge` waits for the client: the task stops, waiting for the client, with the acceptance in "Open questions", as it waits for an approval of the requirements. No answer is not acceptance.
3. When the client accepts, the PM records the answer in `approvals.md`, in a commit that changes only that file. The gate and the reviews name it as `merge`'s commit, like the other roles' commits (ADR 0029, ADR 0032), and a `merge` commit may change only `keyturn/client/approvals.md`. It changes neither document whose hash it records, so the acceptance still holds at the new head. If the client asks for changes instead, the task stops for the maintainer, as a change after `implement` does (ADR 0031).
4. The PM sets the state file to done, with `merge` done, in the last commit, pushes, and waits for CI on that head.
5. It checks the three conditions on that head, and merges with a keyturn script (a squash merge) that checks them again. If any does not hold, or the host refuses the merge, it records a stop (a new state commit, so the conditions are checked again on that head when the task resumes).

**What the host enforces.** A person sets this up once per repository, before the first task, from steps in `github/`:

- Branch protection on the default branch: a pull request is required; the gate's check and the conditions' check are required status checks, each with GitHub Actions as its expected source; force pushes and deletion are blocked; and the rules apply to administrators ("Do not allow bypassing the above settings").
- The CI workflow, which runs both checks, added by the person.
- The agent's token: a fine-grained token for that repository only, with Contents and Pull requests write (and Metadata read), and without Administration, Workflows, or Commit statuses. So the agent cannot change the protection, cannot change the workflow, and cannot post a status that stands in for a check.
- The repository must be on a plan that has branch protection: a public repository, or a paid plan for a private one. Without it, the task does not merge, and `deliver` stops for the maintainer.

**Same account.** With the agent and the client on one account, the host cannot tell the client's acceptance from the agent's: the row in `approvals.md` is as trustworthy as the requirements' approval is today, and the delivery report says so. A separate identity for the agents (a GitHub App), with the client's approval of the pull request as a required review, is phase 7.

**Relation to ADR 0004 and #76.** [ADR 0004](0004-independent-ai-reviewer.md) is about keyturn's own development: CodeRabbit's review is advice and the maintainer merges. It does not change. In a project that uses keyturn, the review roles' open findings are a merge condition, not advice. #76 (merging keyturn's own pull requests when fixed conditions hold, with GitHub Actions) follows the same idea, people set the conditions and machines check them, for this repository; when it is built, its ADR supersedes the part of ADR 0004 that says the maintainer merges. Its "Out of Scope" no longer says that the client merges in projects.

**Other hosts.** Not in the MVP. The same conditions apply on any host; how each host enforces them goes next to GitHub's in its own folder (the same treatment as the choices in #130's "Out of Scope").

## Reasons

- The client keeps control of what matters, the acceptance and the risks they take on, without handling the merge; the agent applies conditions people fixed, and cannot pass them by judgment.
- Branch protection with required checks pinned to GitHub Actions makes the conditions hold whatever runs the merge, and a token without Administration, Workflows, or Commit statuses keeps the agent from changing them.
- Recording the acceptance as the approval is recorded reuses what exists, and says plainly how far it can be trusted on one account.
- Matching the gate's range to ADR 0032 in CI means the head the host merges is checked the same way `deliver` checked it.

## Consequences

- "Merging is the client's action" in `docs/design/github-integration.md` becomes "Merging needs the client's acceptance", with the PM merging on these conditions.
- #138 runs the gate in CI; #141 records the acceptance, checks the conditions in CI, adds the `merge` step and the `merge` role's commits to `deliver`, the state template, and the gate, adds `accepted: decision card <n>` to the review template, and writes the setup steps.
- `task_state.py unmerged` ([ADR 0034](0034-new-task-waits-for-unmerged-task-branches.md)) keeps working, since the merge is the task's last action: the state file is set to done in the last commit before the merge, the squash merge carries it, and nothing is committed to the task branch after it.
- A private repository on a free plan cannot be used for a task until it is public or on a paid plan.
- The end-to-end run (#63) checks the setup before it starts.
