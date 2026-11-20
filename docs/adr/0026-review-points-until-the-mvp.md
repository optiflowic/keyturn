# 0026. Until the MVP, only Critical and Major review points and points that block the flow are fixed

- Status: accepted
- Date: 2026-11-21
- Supersedes: [0019](0019-pre-pull-request-review.md) and [0022](0022-second-review-stage-for-skills-gates-adapters.md), only their rule that the author fixes the findings that are right, and only until the MVP is done ([ADR 0025](0025-mvp-first.md)). The same rule for CodeRabbit's points in `AGENTS.md` ("Review comments") is replaced for the same period.

## Context

Each keyturn pull request is reviewed up to three times: the review before a pull request ([ADR 0019](0019-pre-pull-request-review.md)), the second stage for `skills/`, `gates/`, and `adapters/` ([ADR 0022](0022-second-review-stage-for-skills-gates-adapters.md)), and CodeRabbit. Every finding that is right is fixed. On the recent pull requests that change skills, each review found ten or more points, most of them Minor: wording, rare cases that fail toward a finding, a trial that does not exist yet. Fixing them takes most of a pull request's time and usage, and a fix to a skill often brings new points in the next review.

[ADR 0025](0025-mvp-first.md) builds a minimum viable keyturn first, so that a real run finds the problems early. Until that run, many Minor points are about parts that the run may change anyway.

## Options considered

1. **Keep fixing every finding that is right.** The skills stay polished, but the MVP run comes much later, and some fixes are made to procedures the run will change.
2. **Until the MVP, fix only Critical and Major points and points that block the flow; record the rest and fix them after the MVP.** The points are not lost, and the run comes sooner. Some Minor gaps stay in the skills during the MVP.
3. **Stop the reviews until the MVP.** Cheapest, but the reviews also find the Major points, which are the ones that matter most.

## Decision

Option 2. Until the MVP is done (every issue in the "MVP" milestone is closed), the findings of every review (the review before a pull request, the second stage, and CodeRabbit) are handled this way:

- **Fixed in the pull request**: Critical and Major points, and points that block the flow: a point that, if left, stops the MVP run or the work of a later MVP issue (for example, a step that cannot be done as written, or a check that fails on a correct run).
- **Left for later**: every other point. The pull request lists each one under "How It Was Verified", in one line with why it was left, and a comment on the issue that collects deferred review points lists them too. A CodeRabbit thread gets a reply that says the point was left for later and where it is recorded.
- **Unchanged**: points that need the maintainer's decision are still reported to the maintainer, whatever their severity. The reviews still run as ADR 0019 and ADR 0022 say, once each.

The severity is the one the reviewer gave. When a point has none (the reviews before a pull request may not give one), the author gives it, and says so in the pull request.

After the MVP, the rule that every finding that is right is fixed applies again, and the collected points are worked through in that issue.

## Reasons

- Critical and Major points, and points that block the flow, are the ones that make the MVP run fail or give a wrong result; the rest make the skills better, but the run works without them.
- Recording each deferred point in the pull request and in one issue keeps it from being lost, and lets the work after the MVP see them all at once.
- Ending the rule with the MVP keeps it from becoming the way keyturn is always built.

## Consequences

- `AGENTS.md` ("Review comments" and "Before opening a pull request") states the rule and its end.
- Minor gaps stay in the skills during the MVP. The MVP run may find some of them; the fix then follows this rule too, by its severity in that run.
- The author decides a severity when a review gives none, which leaves room to call a point Minor to skip it. The pull request records each such decision, and the maintainer, who reads it before merging, can ask for a fix.
