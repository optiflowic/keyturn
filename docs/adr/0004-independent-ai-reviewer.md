# 0004. Independent AI reviewer from a different vendor

- Status: accepted
- Date: 2026-11-07

## Context

keyturn is built by AI agents, mainly from one model family. If the same model family writes and reviews every change, its blind spots are shared by both sides, and mistakes can pass review consistently. keyturn's design relies on independent checks (see "Design Principles" 5 and 6 in `docs/DESIGN.md`), and that should apply to keyturn's own development too.

## Options considered

1. **Review only by keyturn's own agents and the maintainer**: no extra service, but the agent review shares the builder's blind spots.
2. **An AI reviewer from a different vendor, in addition to the maintainer**: a second, independent perspective on every pull request at little cost. Needs a service that works with public GitHub repositories.
3. **Human reviewers only**: independent, but not available at the pace AI agents produce changes.

## Decision

Every keyturn pull request is also reviewed by an independent AI reviewer from a different vendor. CodeRabbit is used, configured in `.coderabbit.yaml`.

## Reasons

- A reviewer built on a different model family is less likely to share the builder's mistakes.
- CodeRabbit is free for public repositories ([plans](https://docs.coderabbit.ai/management/plans)) and can be told to review against `docs/DESIGN.md`, the ADRs, and `AGENTS.md`.
- The maintainer still decides what is merged.

## Consequences

- `.coderabbit.yaml` holds the review rules and must stay in line with `docs/DESIGN.md` and the ADRs.
- CodeRabbit's review is advice: it can request changes, but it does not block merging. The maintainer merges.
- If CodeRabbit is replaced, a new ADR supersedes this one.
