# 0071. `AGENTS.md` and each `SKILL.md` have a size limit that a test checks; what only some sessions need lives in files of its own

- Status: accepted
- Date: 2026-11-28

## Context

`AGENTS.md` is loaded into every session (through the `CLAUDE.md` link), and it had grown to 55,192 bytes. "Trying changes locally" alone was 29,526 bytes, and "Review comments" and "CodeRabbit rate limits" 8,959 bytes more, though a session needs them only when it tries a change locally, or opens a pull request and handles its reviews (#207).

The skills have the same problem at a larger scale. A role's `SKILL.md` is loaded whole into every run of that role, also in the projects of everyone who installs the plugin. Together they were 412,883 bytes, `deliver` alone 102,777 and `design` 60,779. The Agent Skills standard recommends a short `SKILL.md` (about 5,000 tokens, under 500 lines) with what is needed less often in files the skill loads only when it needs them (progressive disclosure, in `references/`).

Both files grew the same way: each fix added a condition, and nothing ever pushed back. Accepted ADRs name the sections of `AGENTS.md` ("CodeRabbit rate limits" in `AGENTS.md`), and are never edited ([ADR rules](README.md)).

## Options considered

1. **Move the rarely needed sections out, set a size limit on each file, and check it with a test.** The cost of every session falls at once, and a test makes the growth visible in the pull request that causes it. A limit can push a writer to cut something that matters, so the rules say how to make room first.
2. **Move the sections out, with no limit.** The same saving today, but nothing stops the files from growing back.
3. **A limit as a guideline in the design, with no test.** Nothing fails, so in practice it is checked only when someone notices.

## Decision

Option 1.

- "Trying changes locally" moves to `docs/trying-locally.md`, and "Review comments" and "CodeRabbit rate limits" to `docs/pull-request-reviews.md`, unchanged except for their relative links, an opening paragraph in each file, the path of the gate in the trials that run it in a scratch repository, and "this file" in the second condition for `no-review` ([ADR 0027](0027-when-an-agent-may-add-no-review.md)), which now names `AGENTS.md` and the files it points to so that the condition still covers them. `AGENTS.md` keeps each heading with a one-line pointer that says when to read the file, so that the references in accepted ADRs still lead to the content (as [ADR 0021](0021-design-split-into-section-files.md) did for the design). "Before opening a pull request" stays in `AGENTS.md`.
- Limits, in bytes of the file as committed: 20,000 for `AGENTS.md`, and 30,000 for each `skills/<name>/SKILL.md`. Until #208 shrinks them, a skill over 30,000 bytes has an interim limit of its size on 2026-11-28 plus 5,000, rounded up to the next 1,000: `deliver` 108,000, `design` 66,000, `qa` 50,000, `security-review` 48,000, `review` 40,000, `resume` 38,000, and `spec` 36,000. An interim limit is lowered as its skill shrinks, and removed once the skill is at 30,000 or less.
- `scripts/test_doc_sizes.py` fails when a file is over its limit.
- When changing `AGENTS.md` or a `SKILL.md`: first try rewording what is there so that it covers the case, before adding a condition; put what only some sessions need in a file of its own under `docs/`, with a pointer in `AGENTS.md`; and put steps a role rarely takes in the skill's `references/`, named from `SKILL.md` with when to read each one.
- The final limits change only by a new ADR. An interim limit may be raised with the reason in the pull request, since it only holds the line until #208.

## Reasons

- Bytes are what the test can count the same way on every machine, and they track tokens closely enough for English text. 30,000 bytes is about 7,500 tokens: above the standard's recommendation, since a role's procedure carries rules the run must not skip, but low enough to make `deliver` and `design` move their rare branches out.
- 20,000 bytes leaves `AGENTS.md` about 1 KB of room after the move: enough for small additions, not for a new section.
- The interim limits keep the MVP work going (its pull requests still add to the skills) while stopping a skill from growing by more than about 5,000 bytes before it is shrunk.
- Keeping the headings in `AGENTS.md` costs a few hundred bytes and keeps every reference in an accepted ADR and in the checklist correct.

## Consequences

- Every session loads about 18.8 KB of `AGENTS.md` instead of 55.2 KB. Trying a change, or handling a review, costs one more file read.
- A pull request that grows `AGENTS.md` or a skill past its limit fails `python3 -m unittest discover -s scripts` and must make room first.
- #208 shrinks the skills, starting with `deliver`, and lowers the interim limits as it goes. Adding `references/` to a skill changes what someone who installed the plugin can use, so it follows the version rule for `.claude-plugin/`.
- The accepted ADRs that name "Review comments" or "CodeRabbit rate limits" in `AGENTS.md` ([0019](0019-pre-pull-request-review.md), [0022](0022-second-review-stage-for-skills-gates-adapters.md), [0026](0026-review-points-until-the-mvp.md), [0027](0027-when-an-agent-may-add-no-review.md)) now reach the content through the pointer in `AGENTS.md`.
