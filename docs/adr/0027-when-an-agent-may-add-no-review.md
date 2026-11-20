# 0027. An agent may add `no-review` to a pull request that meets three fixed conditions

- Status: accepted
- Date: 2026-11-21

## Context

The `no-review` label keeps CodeRabbit from reviewing a pull request (`.coderabbit.yaml`). Until now, `AGENTS.md` ("CodeRabbit rate limits") let an agent add it only when the maintainer said so for that pull request, because otherwise an agent could skip the check on its own work.

CodeRabbit's review allowance is limited and often rate limited, and each pull request waits for it ([ADR 0019](0019-pre-pull-request-review.md)). Many pull requests change only documents and do not change a rule: a fresh subagent already reviews them before the pull request, and most of what CodeRabbit finds on such changes is what that review finds ([ADR 0019](0019-pre-pull-request-review.md)). Asking the maintainer each time costs a round with the maintainer instead. [ADR 0025](0025-mvp-first.md) builds the MVP first, which adds many such pull requests.

Not every document is alike. Templates are read by skills and become the shape of what the roles write for a client, so a change to one changes keyturn's output. The worked examples hold the security content (the threats and their mitigations) that the review before a pull request was least able to check: ADR 0019 counted the threats in a worked example among what needed CodeRabbit's deeper analysis. The files under `docs/` hold the design and the ADRs, which are rules, and some of them are read by skills too (`conventions` takes its readability limits from `docs/design/principles.md`); which of them a skill reads is not something the pull request itself shows.

The reason for the old rule still holds: whatever lets an agent skip a review must not depend on the agent's own judgment of its work.

## Options considered

1. **Keep the old rule.** Safe, but each documentation pull request costs a CodeRabbit review or a question to the maintainer.
2. **An agent may add the label when three conditions, each checkable from the pull request itself, are all met, and says in the pull request how each one is met.** The conditions leave out every change where a gap reaches a client's project or changes a rule, and the maintainer can see the claim and undo it.
3. **Turn CodeRabbit off for documentation paths in `.coderabbit.yaml`.** No judgment at all, but it also turns the review off for changes to rules, which live in documents (the design, `AGENTS.md`, the ADRs).

## Decision

Option 2. CodeRabbit keeps reviewing every pull request by default, and `.coderabbit.yaml` does not change. An agent may add `no-review` only to a pull request that meets all three conditions:

1. It changes only files in a fixed list: `README.md`, and the files in `.github/` (the issue forms, the pull request template, and `SECURITY.md`).
2. It changes no rule or decision: it adds no ADR and changes no rule in `AGENTS.md` or in the design (`docs/design/`).
3. The review before the pull request ([ADR 0019](0019-pre-pull-request-review.md)) left no finding unfixed, including points left for later under [ADR 0026](0026-review-points-until-the-mvp.md).

A pull request that changes `skills/`, `gates/`, `adapters/`, `hooks/`, `.claude-plugin/`, any script, or `.coderabbit.yaml` never meets condition 1, and neither does a change to `docs/`, `templates/`, or `evals/`. On any pull request that does not meet all three, an agent adds the label only when the maintainer has said so for that pull request, as before. The agent adds the label while the pull request is still a draft, and the pull request body says that CodeRabbit's review was skipped and how each condition is met. After every later push to a labeled pull request, the agent checks the three conditions again; if they no longer hold and the maintainer did not ask for the label, it removes the label and asks CodeRabbit for a review explicitly, since removing the label does not start one. The maintainer may add or remove the label on any pull request.

## Reasons

- Each condition is a fact about the pull request (its changed paths, whether a rule changed, what the review before it left), not the agent's opinion of its own work, so the agent cannot widen it by judging its work good.
- What keyturn runs (`skills/`, `gates/`, `adapters/`, `hooks/`, scripts), what its skills read (`templates/`, and some of `docs/`), the worked examples in `evals/`, the design and the ADRs in `docs/`, and how keyturn checks itself (`.coderabbit.yaml`) always keep CodeRabbit's review unless the maintainer says otherwise.
- A fixed list of paths can be checked from the pull request alone; "documents no skill reads" could not, since it depends on what every skill reads.
- A fresh subagent has still reviewed the change ([ADR 0019](0019-pre-pull-request-review.md)), so no pull request goes without any independent review.
- Writing how each condition is met in the pull request lets the maintainer check the claim before merging, and removing the label brings CodeRabbit's review back.

## Consequences

- `AGENTS.md` ("CodeRabbit rate limits") states the conditions, and the pull request template has a section for them.
- Changes to templates and worked examples always keep CodeRabbit's review: a template is what a skill turns into a client's document, and a worked example's security content is what the review before a pull request checks least well.
- A pull request that changes only `docs/` gets the label only when the maintainer asks for it.
- Pull requests that meet the conditions use none of CodeRabbit's allowance, which leaves more of it for the changes that need it.
