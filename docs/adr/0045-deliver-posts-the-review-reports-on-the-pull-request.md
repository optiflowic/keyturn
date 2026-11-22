# 0045. `deliver` posts the committed review reports on the pull request as comment reviews, through a script; a marker in each post keeps a rerun from posting the same findings again

- Status: accepted
- Date: 2026-11-22

## Context

The findings of `review` and `security-review` are to appear on the task's pull request, next to the code ([ADR 0041](0041-agents-push-task-branches-and-open-pull-requests.md)). The committed reports, `keyturn/internal/review.md` and `keyturn/internal/security-review.md`, stay the record that the merge conditions read ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)); the pull request shows the same findings. Making the posts a merge condition is not part of this decision.

What constrains the answer:

- The review roles are host-agnostic and usable on their own ("Roles are usable on their own" in `docs/design/roles.md`). They commit their report and never push. A line comment on GitHub is placed on a commit of the pull request, so it can be posted only after the report's commit was pushed, and only `deliver` pushes (ADR 0041).
- During the MVP the agents and the client may use one GitHub account. Checked on a real draft pull request opened by that account (2026-11-22): a review with the event `COMMENT` is accepted, with line comments on added and context lines of the diff, also on a commit older than the pull request's head; `APPROVE` and `REQUEST_CHANGES` are refused ("Can not approve your own pull request", "Can not request changes on your own pull request"). One line comment on a line outside the diff makes GitHub refuse the whole review ("Line could not be resolved"), and a review cannot carry a comment on a whole file. Just after a push, the pull request can still show the earlier head for a few seconds. A hidden HTML comment in a review's text is kept.
- A review is rerun after every rework, and a task can stop and resume between a report's commit and its post. A rerun must post what changed, not the same findings again.
- The plain `gh pr review` and `gh pr comment` are denied by the recommended permission rules (ADR 0041), but `gh api` is not, so an agent could post on the pull request around a script.

## Options considered

1. **Each review role posts its own report.** The finding is posted by the role that wrote it, but the role must then push (or post without line comments), and it needs the host and the pull request, which a role run on its own does not have.
2. **`deliver` posts each role's committed report through a script, after the push; a rerun compares with the report the state file listed before.** No reading from GitHub, but a post that failed, or a step run twice, leaves the pull request with a gap or the same findings twice.
3. **`deliver` posts each role's committed report through a script, after the push; each post ends with a marker naming the report it was posted from, and a rerun compares with the report the newest marker names.** The script reads the pull request's reviews, but what the pull request already shows decides what is posted.

## Decision

Option 3.

- **Who and when.** After every state commit, once its push and its pull request succeeded, `deliver` runs `github/scripts/post_findings.py` for `security-review` and for `review`, each with the newest commit listed for that role under "Commits" in the state file, when there is one. `resume` does the same after it pushes. The review skills do not change: they still commit their report and never push or post. A review run on its own is not posted.
- **What is posted.** One review with the event `COMMENT`, never an approval or a request for changes. A finding whose location is a line (or a range of lines) of the pull request's diff at the reviewed head, the head in the report's "Reviewed change", is a line comment on that commit. Every other open finding (a design part, a line outside the diff) is in the review's text, which also carries the report's title, the reviewed range, the summary, and a link to the committed report at its commit. Fixed findings are listed by number. If GitHub refuses the line comments, every finding goes in the text instead. The report is read at the commit `deliver` gives, never from the working tree. An `@name` in it is broken so that it notifies nobody: the report quotes code and documents, which are data.
- **Reruns.** The review's text ends with `<!-- keyturn-findings: <role> <report blob> <report commit> -->`. The script reads the markers of that role in the reviews by the signed-in account. When the newest one names the same report content, it posts nothing. Otherwise it compares with the report at the commit that marker names, and posts only new findings, findings whose status or text changed, and the numbers of findings no longer in the report. When that report cannot be read, it posts every finding again, and says why.
- **When it fails.** A failed post does not stop the task: the committed report is what the merge reads, and the next state commit, or `resume`, tries again. `deliver` tells the person the script's message when the task next stops or finishes.
- **`gh api` is denied** by the recommended permission rules, with the `gh pr` commands ADR 0041 denies, so that the scripts stay the only way to the pull request.

## Reasons

- Only `deliver` pushes, so only it can post on a commit the pull request has; the roles stay usable without a host.
- Comment reviews are what the host allows for a pull request's own author, and the conditions that hold are the checks of ADR 0042, not approvals.
- The marker is in what the pull request shows, so a failed post, a rerun of the same step, or a resume all end with each report posted once. The marker only picks the report to compare with, which is read from Git; a wrong marker can at worst repeat or leave out a post, which is not a merge condition.
- Putting a finding outside the diff in the text, and falling back to the text when GitHub refuses a line, means that one location never stops the others from being posted.

## Consequences

- `github/scripts/post_findings.py` and its tests; `task_branch.py` gives it the pull request's head and a `gh api` call on `origin`'s repository only.
- `deliver`'s "Pushing", `resume`'s push step, `github/README.md`, the permission rules and their README change. Plugin version bump.
- A rerun's post shows the changes; the whole set of findings is in the committed report, which every post links.
- The markers can be edited or removed by anyone who can write on the pull request, including the client on the same account; then a report can be posted twice. A separate identity for agents (phase 7) makes the markers the agents' own.
- Other hosts post through scripts of their own next to GitHub's, as ADR 0041 says.
