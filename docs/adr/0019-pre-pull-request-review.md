# 0019. A fresh subagent reviews the diff once before a pull request is opened

- Status: accepted
- Date: 2026-11-14

## Context

Every keyturn pull request is reviewed by CodeRabbit ([ADR 0004](0004-independent-ai-reviewer.md)). Its review allowance is limited: it reviews a pull request automatically once, re-reviews only when asked, and rate limits often delay both ("CodeRabbit rate limits" in `AGENTS.md`). Each round of fixes costs a re-review and waiting time.

On the 14 most recent pull requests it reviewed (#64 to #95), CodeRabbit made 42 verified points (counted by hand from its review comments on those pull requests, on 2026-11-14). About 31 of them could have been found by reading the repository, without deep analysis:

- contradictions between documents, or between a document and what a script does (8);
- claims and definitions broader than they should be (4);
- steps that break when a task stops and resumes, or when an input is missing (about 7);
- unhandled script errors and unchecked input (6), and a missing page fetch (1);
- tests that depend on the operating system or the developer's setup (2);
- missed repository rules: the plugin version bump, a link to a file only an unmerged pull request adds, a skill that relies on one not yet written (3).

The rest needed deeper analysis: the threats in the worked example (5), a fact about Go's `go.sum` (1), and points that were too small to be worth fixing. Several pull requests needed extra rounds because a fix left another line in the same file out of date.

The author of a change shares its blind spots, so checking its own work against `AGENTS.md` did not catch these, even where `AGENTS.md` states the rule.

## Options considered

1. **Leave it to CodeRabbit**: no extra step, but most rounds are spent on points that reading the repository finds, and each round waits for the review allowance.
2. **The author checks its own diff against a checklist**: cheap, but the author already missed rules that `AGENTS.md` states.
3. **A fresh subagent reviews the diff once, on a lower-tier model**: it did not write the change, so it does not share the author's reasoning. It gets only what the diff needs, so the review stays short.
4. **The same, on a higher-tier model, or more than once**: more thorough, but it costs more and repeats what CodeRabbit does next.

## Decision

Option 3. Before a pull request is opened, a fresh subagent that did not write the change reviews the diff against `main` once, on a lower-tier model (Sonnet in Claude Code). It reads only:

- the sections of `docs/DESIGN.md` and the ADRs that the change relates to, and the files the diff links to;
- the sections of [`docs/pre-pr-checklist.md`](../pre-pr-checklist.md) whose paths match the changed files;
- the `path_instructions` in `.coderabbit.yaml` whose paths match the changed files.

It reports findings and does not edit files. The author fixes the findings that are right and writes in the pull request what was found and fixed. The review is not repeated after the fixes. On a tool without subagents, the review runs in a separate process on a lower-tier model. Where a rule is already stated in `AGENTS.md`, `docs/DESIGN.md`, or an ADR, the checklist links to it instead of copying it.

## Reasons

- The points this review targets are found by comparing what is written: a document with another document, a claim with a counterexample, a script with its error cases. A lower-tier model is enough for that. "Model Tiers" in `docs/DESIGN.md` gives the review of a lower-tier model's output to a higher-tier model; this review is not that one. It is a cheap check before the review, and the review that needs judgment stays with CodeRabbit and the maintainer. Deep analysis, such as the threats in a worked example, is left to CodeRabbit.
- A subagent that did not write the change does not share the author's reasoning, like the separate contexts of design principle 5.
- Reading only what the diff needs keeps the review short and cheap. Reading all of `docs/DESIGN.md` and every ADR would cost more and spread the reviewer's attention.
- Where a rule is already stated elsewhere, the checklist links to it instead of copying it, so a change to the rule is made in one place.
- One review is enough to remove most of the points that reading finds. Repeating it would cost more than it saves, and CodeRabbit reviews the result anyway.

## Consequences

- `AGENTS.md` "Before opening a pull request" describes the review. "Where things live" in `AGENTS.md` and "Repository Layout" in `docs/DESIGN.md` list the checklist.
- When CodeRabbit keeps finding points of a kind the checklist does not cover, and reading the repository could have found them, an item for that kind is added to the checklist.
- This does not replace CodeRabbit ([ADR 0004](0004-independent-ai-reviewer.md)) or the maintainer: CodeRabbit is still the independent reviewer from another vendor, and the maintainer still merges.
- The review is a step in developing keyturn, not part of keyturn's pipeline for client projects; the `review` skill (#59) is that.
