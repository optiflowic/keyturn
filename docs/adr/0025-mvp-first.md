# 0025. Build a minimum viable keyturn first, and move the rest to enhancements

- Status: accepted
- Date: 2026-11-21

## Context

[Phases](../design/phases.md) builds keyturn one phase at a time, and each phase is done only when all of it is done: phase 3 adds every phase 1 skill and the Claude Code adapter, with its sandbox, and is done when a run finishes inside the sandbox; phase 4 adds the gate and two profiles, and also the evaluation baseline and a one-command eval suite; phase 5 adds the security scans; phase 6 is the first run on a real application.

By the end of phase 2 and most of phase 3, every role skill except `deliver` exists, but keyturn has not yet taken one request from start to end. Following the phases in order, the first real run comes after the sandbox, the translation subagent, the baseline, the eval suite, and the security scans. Each of those is useful, but none is needed to learn whether the pipeline works, and the run is where most of the problems will be found ([Phases](../design/phases.md): keyturn is developed by using it). Development also runs within a subscription plan's usage windows, so the order decides how soon that run happens.

## Options considered

1. **Keep the phases in order.** Each phase is finished before the next, but the first run on a real application comes last, after work that the run may show to be wrong.
2. **Build a minimum viable keyturn first (an MVP), then the rest as enhancements.** The MVP takes a request from requirements through design, implementation, tests, security review, code review, and a delivery report, on a real application, and the client decides from the requirements, the acceptance guide, and the delivery report. It takes parts of phases 3, 4, and 6. What it leaves out is listed, and the delivery report states it as a known gap.
3. **Run the pipeline by hand now, without `deliver` or a gate.** Cheapest, but it tests neither the hand-offs between roles nor the checks that keep the developer honest, which are what keyturn is for.

## Decision

Option 2. The MVP is:

- `deliver`, and what it needs from `review` and `security-review` on a rerun;
- the Claude Code adapter's subagent definitions, and minimal permission settings that block direct pushes to the default branch and destructive commands;
- a minimal gate for the `go` and `react-spa` profiles: build, tests, lint, no drop in the number of tests, protected paths, and new suppression comments in the diff;
- one run from request to delivery on a real application, including finishing a stopped run with `resume`.

Everything else in phases 3 to 6 becomes an enhancement after the MVP: the translation subagent, the sandbox and protecting the usage records, full security scans (SAST, secrets, and more), checks for skipped tests and coverage, the evaluation baseline and one-command eval suite. So do the other later items: more stacks, other tools' adapters, the client portal, automatic merging, runs paced to a deadline, and multi-repository projects. The phases keep their numbers and order for what is left.

## Reasons

- The run on a real application finds the problems in the hand-offs, the gate, and the client-facing documents, and finding them early changes less work than finding them after the enhancements are built on top.
- Every part of the MVP is on the path from a request to a delivery report that a client can decide from. The parts left out make that path safer or broader, but the path works without them, and the delivery report says what is missing.
- The sandbox can wait because the MVP is run by the maintainer, on a repository of their own, with no production credentials, and with the permission rules that block the most damaging actions. The sandbox protects the machine and the network from an agent that does more than it should; until it exists, a person who knows that is watching the runs. A client project needs it, so it is the first enhancement for the adapter.
- The security scans can wait for the same reason the profiles' known gaps exist ([Stack Profiles](../design/stack-profiles.md)): the delivery report states what was not checked instead of implying it was.
- Keeping the phase numbers keeps the references to them in the ADRs and the design correct.

## Consequences

- [Phases](../design/phases.md) has an "MVP" section before the numbered phases, and the phases say which of their parts are in the MVP and which are enhancements. Phase 3 is no longer done "inside the sandbox".
- [Guardrails](../design/guardrails.md) 4 and [Stack Profiles](../design/stack-profiles.md) say what the MVP runs without, and that the delivery report lists it under "What was not verified".
- Work is tracked in an "MVP" milestone; issues moved to enhancements get the `enhancement` label. The sandbox is tracked in its own issue, and adding it removes that known gap.
- The MVP run uses a repository the maintainer creates, not this one, and nothing about the application is committed to `evals/requests/`.
