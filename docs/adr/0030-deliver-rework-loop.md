# 0030. `deliver` sends work back on a failing gate, a failing test, and high or medium findings, up to a set number of rounds

- Status: accepted; a medium finding of `review` that the client accepted on a decision card no longer sends the work back, superseded by [0042](0042-pm-merges-on-machine-checked-conditions.md); a rating finding of the security review no longer sends the work back, and a question QA asks for the design does, superseded by [0060](0060-design-answers-for-qa-and-threat-ratings.md)
- Date: 2026-11-21

## Context

`deliver` (#60) runs the roles in order: `spec`, `design`, `conventions`, `implement`, `qa`, `security-review`, `review`, and its own last step ([Roles](../design/roles.md)). After the developer's step, four things can find a problem: the gate ([ADR 0028](0028-gate-interface.md)), QA's tests, the security role, and the reviewer. "Who checks what" says that the developer fixes what any of them report, and [Guardrails](../design/guardrails.md) 5 says that every task has a rework limit, at which it stops and asks.

Questions to settle: what sends the work back to the developer, which steps run before it goes back, what the developer gets, and where the limit is set.

Each round costs a run of `implement`, the gate, `qa`, `security-review`, and `review`, within a subscription plan's usage windows. A round spent on a low finding (an unclear name) costs as much as one spent on a failing test.

## Options considered

1. **Every open finding sends the work back**, low ones included. Closest to "the developer fixes what any of them report", but a low finding then costs a full round, and the rework limit is reached on readability alone.
2. **Only what blocks delivery sends it back**: a failing gate, a failing test, and high findings. Medium findings (code that works, but in the wrong part, or against a convention in a way that makes it harder to change) would then be delivered unless something else sends the work back.
3. **A failing gate, a failing test, and high or medium findings send it back; low findings go with a round that happens anyway.** Low findings alone are listed in the delivery report.

## Decision

Option 3.

- After each `implement` step, `deliver` runs the gate on the developer's work. A failing gate (exit 1) sends the work back at once: `qa`, `security-review`, and `review` do not run on a change that fails its checks. A gate that cannot run (exit 2) stops the task, and a person is asked.
- When the gate passes, `qa`, `security-review`, and `review` all run, in that order, before anything goes back, so that one round gives the developer everything they found.
- The work goes back when any of these holds: the gate failed; a criterion in QA's report is `fail`; QA could not build or start the deliverable from the developer's "How to run", so its criteria are `not tested` for that reason; `security-review` or `review` has an open finding of high or medium severity.
- When it goes back, the developer gets every finding still open from the last reports, low ones included, and the gate's failing checks. When only low findings are open, the work does not go back; they are listed in the delivery report as open.
- Each time the work goes back, the round count goes up by one. The limit is 3 rounds by default, set by the optional `rework_limit` in `keyturn/config.json`. When the work would go back once more than the limit allows, the task stops for the rework limit, and the maintainer decides what happens next.
- In a new round, the steps after `implement` run again from their inputs, as reruns of their own skills (each of them reads its earlier report). None is skipped because it found nothing in the round before: a fix can break what an earlier round passed.

## Reasons

- A failing test or a high finding blocks delivery, so it must go back. A medium finding is still a defect in the change (the design or a convention is not followed), and leaving it for after delivery makes the next change harder, which is what the reviewer is there to prevent.
- A low finding alone does not justify a full round. Sending it with a round that happens anyway costs nothing extra, and listing the rest keeps them visible to the client.
- Running the three checks together after a passing gate halves the rounds compared with going back after each one, and keeps each role's report about the same head.
- Skipping the checks on a failing gate saves a round's worth of usage on a change that has to change anyway.
- A configurable limit lets a project with a larger change allow more rounds without changing the skill. Stopping at it, instead of going on, is what [Guardrails](../design/guardrails.md) 5 asks.

## Consequences

- `skills/deliver/SKILL.md` follows this order and these conditions, and counts rounds in the task state file's "Rework" field (`<n> of <limit>`).
- `project-config` knows the optional `rework_limit` (a whole number from 0 to 10); without it, the limit is 3.
- The delivery report (#60) lists the low findings left open, and every round's result.
- When the developer thinks a finding is wrong, they say so in the handoff notes, and the task stops for the maintainer to decide: the role that raised it does not read the handoff notes, so it cannot weigh the objection itself.
