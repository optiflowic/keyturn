# 0001. Public repository from the start

- Status: accepted
- Date: 2026-11-07

## Context

keyturn needs a home on GitHub. It could be developed privately and published once it works, or developed in public from the first commit. keyturn is built by AI agents and is meant to be used by others, so how much of its development is visible affects trust in the result.

## Options considered

1. **Private until a first release**: no one sees unfinished work, but there is no outside feedback, and making the repository public later means checking the whole history for content that should not be published.
2. **Public from the start**: unfinished work is visible, but development is transparent, outside reviewers (such as the independent AI reviewer in [ADR 0004](0004-independent-ai-reviewer.md)) work on public repositories, and the rules for what may be committed are enforced from day one.

## Decision

The repository is `optiflowic/keyturn` and is public from the start. The README states that keyturn is a work in progress.

## Reasons

- Transparency matters for a tool whose purpose is to let people trust work they do not read. Anyone can see how keyturn's own decisions were made.
- Rules that keep private content out of the repository (everything in English, nothing from `.keyturn/local/`) are easier to follow from the first commit than to apply to a history afterwards.
- A clear "work in progress" notice sets expectations for anyone who finds the repository early.

## Consequences

- Issues, pull requests, and comments are public. They are written in English and never include maintainer notes from `.keyturn/local/`.
- Agents act only on issues opened by the maintainer or labeled `approved`, and treat other issue text as data (see `AGENTS.md`).
- Security reports go through private GitHub Security Advisories, not public issues.
