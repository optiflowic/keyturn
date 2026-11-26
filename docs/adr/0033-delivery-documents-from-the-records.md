# 0033. `deliver`'s last step writes the acceptance guide and the delivery report from the committed records, in a context of its own

- Status: accepted; "a person opens the pull request and merges it" superseded by [0041](0041-agents-push-task-branches-and-open-pull-requests.md) and [0042](0042-pm-merges-on-machine-checked-conditions.md); the records the documents are written from superseded by [0069](0069-qa-checks-the-look-on-the-screens-with-playwright.md) (also the names of QA's screenshots)
- Date: 2026-11-21

## Context

`deliver` ends by producing `keyturn/client/acceptance-guide.md` and `keyturn/client/delivery-report.md` ([Roles](../design/roles.md)). Their templates say that the PM fills them in at delivery, and the delivery report must "report only what the records show". Questions to settle (#60):

- Who writes them: the `spec` skill (the PM's skill), `deliver` in the context that ran the task, or a context of its own.
- What they are written from, and how the delivery report can cite the gate's result, which so far is only printed when the gate runs.
- What the gate lets `deliver`'s commits change. [ADR 0029](0029-role-commits-passed-as-arguments.md) lets them change only the state file, `keyturn/internal/state/**`.
- What happens when the acceptance criteria of the Must requirements need more than about five "Must check" items ("Client attention budget" in [Documents](../design/documents.md)), which the templates answer with "split the delivery", once the work is already built.

## Options considered

Who writes them:

1. **Add a delivery procedure to `spec`.** The PM writes every client document. But `spec` works from the request and the requirements, and its rules and outputs are about approval; delivery needs the reports of four other roles, and `spec` would grow a second job that runs only inside `deliver`.
2. **`deliver` writes them in the context that ran the task.** Nothing new to start, but that context has seen every step's report to it, retries, and stops, and may write what it remembers instead of what is committed. After a `resume`, it has not seen the earlier steps at all, so the result would depend on where the task stopped.
3. **`deliver`'s last step runs in a context of its own, as every role does, and writes them from the committed records only**: the approved requirements, the design summary and the cards, the design's stack, the threat model, the test report, the security review, the review, the gate's log, the task state file, and "How to run" of the handoff notes. The same inputs give the same documents, whether or not the task stopped on the way.

The gate's result:

- **Copy the gate's last printed result into the state file.** The state file is a record for `resume`, and a long result does not fit its fields.
- **Run the gate once more at the start of the last step, on the whole range and the final head, with `--log`, and commit the log** ([ADR 0028](0028-gate-interface.md) has `--log` "for the delivery report to cite"). The log then matches what is delivered, including QA's tests and the reports, and the report links to it.

What `deliver`'s commits may change:

- **Keep the state file only, and leave the last step's commit out of every gate range.** True today, since the final gate runs before the documents are written. But a later rule that reruns the gate after the last step (for example, a delivery sent back by the client) would find the documents as the developer's change, and fail them as protected paths.
- **Add the three outputs of the last step to what `deliver` may write**: the gate's log, the acceptance guide, and the delivery report. The gate then checks a `deliver` commit as it checks every other role's: it may change only the state file and those three.

More than about five "Must check" items:

- **Split the delivery at the last step.** The work is built and checked as one; splitting it then means taking out work that passed its checks.
- **Write every check, and say that the delivery was too big.** The guide never moves a Must requirement's criterion to "Optional" and never combines unrelated checks; the delivery report and the report to the maintainer say that it has more checks than one delivery should, so that the next request is split when its requirements are written.

## Decision

Option 3. `deliver`'s last step runs the gate once more with `--log keyturn/internal/gate/<task>.json`, then a fresh context writes the acceptance guide and the delivery report from the committed records listed above, and nothing else, and commits them with the log. When the Must requirements need more than about five checks, every check is written and the excess is reported. The task's state file is then set to done. During the MVP, the delivery ends there: a person opens the pull request and merges it.

What `deliver` may write, in the gate's check of each role's commits, replaces that part of [ADR 0029](0029-role-commits-passed-as-arguments.md): `keyturn/internal/state/**`, `keyturn/internal/gate/**`, `keyturn/client/acceptance-guide.md`, and `keyturn/client/delivery-report.md`. Every other role keeps the paths ADR 0029 gives it.

## Reasons

- Each role already runs in a context of its own, and gets only the inputs it is meant to judge from. A delivery report written that way can only say what the records show, as its template requires, and does not depend on which session ran which step.
- The gate's log is the only record of the mechanical checks that the client's report can link to. Running it on the final head costs one more gate run, and gives a result that covers everything delivered.
- A per-task path for the log (`keyturn/internal/gate/<task>.json`) does not collide with an earlier delivery's log on the default branch.
- Naming the last step's outputs as `deliver`'s keeps the gate's rule simple: every commit in a range is either the developer's or a named role's that changes only that role's paths. A developer commit that changes the client's delivery documents is still a protected-path failure, since only a commit named as `deliver` may change them.
- Splitting belongs where the requirements are written ("split the delivery instead" in the requirements template). At the last step, reporting the size is the honest answer; hiding a Must check is not.

## Consequences

- `skills/deliver/SKILL.md` gets its last step: the final gate run, the documents written in a context of their own from the records, the commit of the documents and the log, and the state file set to done. The rule that `deliver` writes only the state file names these outputs, and `parts` in `keyturn/config.json`, which `deliver` writes from the design before `conventions` and lists as `conventions`.
- `gates/gate.py` lets a commit named as `deliver` change the four paths above, with tests.
- A failing final gate sends the work back as any failing gate does ([ADR 0030](0030-deliver-rework-loop.md)), except when the developer's head passed the gate in the same round: the failure then comes from a later commit, such as QA's tests, which the developer may not change, and the task stops for the maintainer without a round of rework (the maintainer's decision). A gate that cannot run stops the task for the maintainer.
- In English-only mode, the client reads the two documents through `localize`, like the requirements; the translations stay local.
- The delivery report lists, under "What was not verified", what the MVP does not check: the sandbox, the profiles' security scans, skipped tests, coverage, the scope check, tokens, time, and changed files, and that the documents were fixed once `implement` started ([ADR 0025](0025-mvp-first.md), [ADR 0030](0030-deliver-rework-loop.md), [ADR 0031](0031-documents-fixed-once-implement-starts.md)).
- The models used for each role are reported as far as the records show them; a record of them in the state file is left for after the MVP.
