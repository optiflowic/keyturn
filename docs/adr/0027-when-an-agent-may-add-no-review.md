# 0027. An agent may add `no-review` to a pull request that meets three fixed conditions

- Status: accepted
- Date: 2026-11-21

## Context

The `no-review` label keeps CodeRabbit from reviewing a pull request (`.coderabbit.yaml`). Until now, `AGENTS.md` ("CodeRabbit rate limits") let an agent add it only when the maintainer said so for that pull request, because otherwise an agent could skip the check on its own work.

CodeRabbit's review allowance is limited and often rate limited, and each pull request waits for it ([ADR 0019](0019-pre-pull-request-review.md)). Many pull requests change only documents, templates, or examples, and do not change a rule: a fresh subagent already reviews them before the pull request, and most of what CodeRabbit finds on such changes is what that review finds ([ADR 0019](0019-pre-pull-request-review.md)). Asking the maintainer each time costs a round with the maintainer instead. [ADR 0025](0025-mvp-first.md) builds the MVP first, which adds many such pull requests.

The reason for the old rule still holds: whatever lets an agent skip a review must not depend on the agent's own judgment of its work.

## Options considered

1. **Keep the old rule.** Safe, but each documentation pull request costs a CodeRabbit review or a question to the maintainer.
2. **An agent may add the label when three conditions, each checkable from the pull request itself, are all met, and says in the pull request how each one is met.** The conditions leave out every change where a gap reaches a client's project or changes a rule, and the maintainer can see the claim and undo it.
3. **Turn CodeRabbit off for documentation paths in `.coderabbit.yaml`.** No judgment at all, but it also turns the review off for changes to rules, which live in documents (the design, `AGENTS.md`, the ADRs).

## Decision

Option 2. CodeRabbit keeps reviewing every pull request by default, and `.coderabbit.yaml` does not change. An agent may add `no-review` only to a pull request that meets all three conditions:

1. It changes only documents, templates, worked examples, and issue forms.
2. It changes no rule or decision: it adds no ADR and changes no rule in `AGENTS.md` or in the design (`docs/design/`).
3. The review before the pull request ([ADR 0019](0019-pre-pull-request-review.md)) left no finding unfixed, including points left for later under [ADR 0026](0026-review-points-until-the-mvp.md).

A pull request that changes `skills/`, `gates/`, `adapters/`, `hooks/`, any script, or `.coderabbit.yaml` never gets it from an agent. The agent adds the label while the pull request is still a draft, and the pull request body says that CodeRabbit's review was skipped and how each condition is met. The maintainer may add or remove the label on any pull request.

## Reasons

- Each condition is a fact about the pull request (its changed paths, whether a rule changed, what the review before it left), not the agent's opinion of its own work, so the agent cannot widen it by judging its work good.
- The paths where a gap reaches a client's project, or changes how keyturn checks itself, always keep CodeRabbit's review, as do the documents that hold rules.
- A fresh subagent has still reviewed the change ([ADR 0019](0019-pre-pull-request-review.md)), so no pull request goes without any independent review.
- Writing how each condition is met in the pull request lets the maintainer check the claim before merging, and removing the label brings CodeRabbit's review back.

## Consequences

- `AGENTS.md` ("CodeRabbit rate limits") states the conditions, and the pull request template has a section for them.
- Templates are files skills read, so a template change still bumps the plugin version when the version rule says so; the label changes nothing about that.
- Pull requests that meet the conditions use none of CodeRabbit's allowance, which leaves more of it for the changes that need it.
