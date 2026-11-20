# 0022. A second review stage, on a higher-tier model, before pull requests that change skills, gates, or adapters

- Status: accepted; its rule that the author fixes the findings that are right superseded by [0026](0026-review-points-until-the-mvp.md) until the MVP is done
- Date: 2026-11-15
- Supersedes: [0019](0019-pre-pull-request-review.md), only its sentence that "the review that needs judgment stays with CodeRabbit and the maintainer" (in its first reason), for pull requests that change `skills/`, `gates/`, or `adapters/`. Its sentence that deep analysis, such as the threats in a worked example, is left to CodeRabbit still stands.

## Context

[ADR 0019](0019-pre-pull-request-review.md) has one review before a pull request: a fresh subagent on a lower-tier model compares what is written, and "the review that needs judgment stays with CodeRabbit and the maintainer" (its Reasons).

On #101 (the `review` skill), a second stage was tried once at the maintainer's request, after the first stage's fixes: a fresh subagent on the session's model (Opus) took each rule of "Guardrails" in the design ([`docs/design/guardrails.md`](../design/guardrails.md)) and of the matching `.coderabbit.yaml` path instructions, one at a time, and looked for a way the skill's procedure breaks it. It found 10 points that the first stage had missed. CodeRabbit's later review overlapped with 2 of them, and none of the 6 that were fixed came back. Most of what it found came from running the procedure in a case the author had not walked through: a rerun, a missing input, a range that changes the documents it is judged by.

Skills, gates, and adapters are what a client's project runs, and what decides whether a check holds. A gap in them reaches every project that uses keyturn, while CodeRabbit's allowance is limited and each round of its points waits for it ("CodeRabbit rate limits" in `AGENTS.md`).

## Options considered

1. **Keep one stage, and leave judgment to CodeRabbit and the maintainer.** No extra cost, but on #101 that left 10 points for CodeRabbit's rounds or for no one: CodeRabbit found only 2 of them (counted by hand from the pull request's "How It Was Verified" and CodeRabbit's review, on 2026-11-15).
2. **A second stage on a higher-tier model, only for pull requests that change `skills/`, `gates/`, or `adapters/`.** Costs one more review on the changes where a gap reaches client projects, and where the trial paid off. Other changes keep the single cheap review.
3. **A second stage on every pull request.** More thorough, but documents, templates, examples, and `scripts/` are checked well by comparing what is written, which the first stage already does, so most of the cost would be spent where it finds little.
4. **Run the first stage on a higher-tier model instead.** One review, but it mixes comparing what is written with walking through cases, and the trial found the cases by doing them one rule and one case at a time, after the first stage's fixes.

## Decision

Option 2. A pull request that changes `skills/`, `gates/`, or `adapters/` gets a second review stage, after the fixes of the first stage ([ADR 0019](0019-pre-pull-request-review.md)) are committed:

- **Who**: a fresh subagent that wrote neither the change nor the first stage's review, on a higher-tier model than the first stage (Opus in Claude Code). On a tool without subagents, a separate process on a higher-tier model.
- **What it gets**: the diff against `main`, and every changed file in full as it is on the branch (a deleted file as it was on `main`), since walking through a procedure needs all of it, not only the changed lines; "Guardrails" and the other sections of the design and the ADRs that the change relates to, and the files the diff links to; and the `path_instructions` in `.coderabbit.yaml` whose paths match the changed files. Not the first stage's findings, so that it does not follow the same path.
- **What it does**: it takes each rule in those, one at a time, and looks for a way the changed procedure or script breaks it. It walks through the procedure step by step on the first run, with each input missing, and on a rerun; for a script, a hook, or a gate, it does the same with the script's inputs.
- **Once**: it runs once and is not repeated after its fixes. It reports findings and does not edit files.

The author fixes the findings that are right, and reports those that need a decision to the maintainer. The pull request says, under "How It Was Verified", what the second stage was given, what it found, what was fixed, and what was left and why.

## Reasons

- "Model Tiers" in the design ([`docs/design/model-tiers.md`](../design/model-tiers.md)) has higher-tier models review a lower-tier model's output for what needs judgment, and ADR 0019 says its review is not that one. The second stage is that review, for the changes that reach client projects, run before the pull request rather than left to CodeRabbit's rounds.
- On #101 the second stage found what the first stage cannot by comparing what is written: what happens when the procedure runs in a case the author did not walk through.
- Limiting it to `skills/`, `gates/`, and `adapters/` spends the higher-tier model where a gap reaches every project, and keeps other pull requests as cheap as before.
- Running it after the first stage's fixes, and once, keeps it from repeating what the first stage finds, and keeps its cost to one review.
- A reviewer that wrote neither the change nor the first review does not share the reasoning of either, like the separate contexts of design principle 5.

## Consequences

- `AGENTS.md` "Before opening a pull request" describes when the second stage runs, what it is given, and what the pull request records about it.
- `docs/pre-pr-checklist.md` has an item to walk through a skill's procedure on the first run, with each input missing, and on a rerun. It is a cheap prompt for the author and the first stage, which still compare what is written; it does not replace the second stage.
- CodeRabbit still reviews every pull request ([ADR 0004](0004-independent-ai-reviewer.md)), and the maintainer still decides and merges. The second stage does not replace either.
- A pull request that changes these paths costs one more review on a higher-tier model. If later pull requests show that it finds little, a new ADR can narrow or drop it.
