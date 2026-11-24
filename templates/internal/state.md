<!--
Template: task state file (internal). Written by `deliver` at every step boundary and when the task stops; read by `resume`.

- Always written in English.
- Lives at `keyturn/internal/state/<task>.md`, on the task's branch `task/<task>`. <task> is a short name in lowercase with hyphens (for example, delivery-1), and never changes.
- Use only the field names and values listed here, so that scripts can read the file. Times are UTC: YYYY-MM-DDTHH:MMZ.
- Record only what is in the repository. Nothing here may depend on the context of the session that wrote it.
- Commit the file on a commit of its own after each step's commit, on the task branch, never in a role's commit: a role's commit may change only what that role writes (ADR 0029 in keyturn's `docs/adr/`).
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Task state: <task>

- Task: <task>
- Requirements version: <n>
- Branch: `task/<task>`
- Status: <running | stopped | done | closed>
- Current step: <step name from the table below | none>
- Stopped because: <none | usage limit | session ended | waiting for the client | waiting for the maintainer | rework limit | budget limit | error>
- Can continue: <now | after YYYY-MM-DDTHH:MMZ | when the client approves: requirements version <n> | when the client answers: decision card <n> | when the client agrees: design summary | when the client accepts: <task> | when the maintainer decides: <what> | not applicable>
- Rework: <n> of <limit>
- Updated: <YYYY-MM-DDTHH:MMZ>

## Summary

<!-- One or two lines a client can read: where the task is, and, if it stopped, why and when it can go on. -->

<summary>

## Steps

<!--
One row per step, in the order deliver runs them. Do not remove rows; a step that does not apply is "skipped", with the reason in "Notes".
- Status: not started, in progress, done, or skipped.
- Output: links to the documents the step wrote.
- Commit: the commit that checkpointed the step (its last commit). A step is done only when its outputs are committed. Every commit of a step, in every round, is listed under "Commits".
- When a finding sends work back to the developer, set implement and the steps after it back to "not started", and add one to "Rework".
-->

| Step | Status | Output | Commit | Notes |
|---|---|---|---|---|
| spec | <status> | <links> | <commit> | <notes> |
| design | <status> | <links> | <commit> | <notes> |
| conventions | <status> | <links> | <commit> | <notes> |
| implement | <status> | <links> | <commit> | <notes> |
| qa | <status> | <links> | <commit> | <notes> |
| security-review | <status> | <links> | <commit> | <notes> |
| review | <status> | <links> | <commit> | <notes> |
| deliver | <status> | <links> | <commit> | <notes> |
| merge | <status> | <links> | <commit> | <notes> |

## Commits

<!--
Every commit made on the task branch since it left the default branch, oldest first, one line each: the commit (its full hash, never a short one: ADR 0043 in keyturn's `docs/adr/`), the step that made it, and the round (1 for the first round, one more for each rework). Commits made before spec (the configuration) are listed as "spec". The architect's answers to the developer's questions during implement (keyturn/internal/design-answers.md) are listed as "answer", which is not a step (ADR 0058 in keyturn's `docs/adr/`). deliver's own state commits are listed as "deliver"; since a commit cannot name itself, each one is listed by the next state commit. resume lists the state commit it resumes from (the one that recorded the stop), and its own resume commit is listed by deliver's next state commit.
deliver adds a step's lines when the step ends. The list is a record only: the gate's range starts where the task branch left the default branch (git merge-base), deliver passes the other roles' commits to the gate and the reviews, and the gate checks that each one changes only what its role may write (ADR 0029 and ADR 0032 in keyturn's `docs/adr/`).
Leave the section with "None." only until the first state commit after "started" lists it.
-->

- `<commit>`: <step name from the table above, or answer>, round <n>

## Open questions

<!--
Everything waiting for the client, and the work that waits for it: decision cards, decisions in the design summary that wait for the client's agreement (one line for all of them), and requirements sent for approval (see approvals.md).
A decision card is never decided for the client, and work does not start before the requirements are approved. During the MVP, implement starts only when nothing here is left (ADR 0031 in keyturn's `docs/adr/`).
Leave the section with "None." when there is nothing waiting.
-->

- <decision card <n>: link>: <the question, in one line>. Waiting since <YYYY-MM-DDTHH:MMZ>. Blocks: <steps or requirements>
- <requirements version <n>: link to approvals.md>: waiting for approval since <YYYY-MM-DDTHH:MMZ>. Blocks: <design and every later step>
- <design summary: link>: waiting for agreement since <YYYY-MM-DDTHH:MMZ>. Blocks: <design and every later step>

## History

<!--
One line per stop and per resume, newest last. Never edit or remove a line.
For a usage limit, say which window and when it resets. A resume before that reset, by the maintainer's decision, says so on its line: "resumed: in the step, from which commit (before the usage limit resets at YYYY-MM-DDTHH:MMZ, by the maintainer's decision: what they decided)" (ADR 0053 in keyturn's `docs/adr/`). A redo of spec, design, or conventions before implement, and the maintainer's vouch for the redone documents, are said on the resume's line too: "(redo of <steps> before implement, by the maintainer's decision: what they decided)" and "(documents vouched for at `<full SHA>`, by the maintainer's decision)" (ADR 0057). So is the maintainer's answer to the developer's questions that the architect did not answer: "(answer to implement's questions, by the maintainer: their answer, in one line)" (ADR 0058). So is the maintainer's decision that QA fixes its own tests after the gate failed on them: "(QA fixes its tests, by the maintainer's decision: what QA fixes, in one line)"; the run of qa it starts does not count toward "Rework" (ADR 0064).
-->

- <YYYY-MM-DDTHH:MMZ>: <started | stopped: reason, in the step | resumed: in the step, from which commit | done | closed: why, in the step>
