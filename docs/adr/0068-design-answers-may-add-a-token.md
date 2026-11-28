# 0068. A design answer may add a token to the design's "Look", on the scale the tokens already have

- Status: accepted; that an answer never adds checked widths superseded by [0069](0069-qa-checks-the-screens-end-to-end-in-a-browser.md) (it may when the design has none); the form of a reference to an existing token superseded by [0072](0072-profiles-fix-styling-principles-not-the-tool.md)
- Date: 2026-11-26
- Supersedes: in [0058](0058-design-answers-during-implement.md), that an answer never changes a decision the design records, for one case: an answer may add a token to the design's "Look"

## Context

The design's "Look" section lists every token the code takes its spacing, type, colors, and component shapes from, and the developer writes the token file with exactly those tokens and values ([ADR 0067](0067-design-decides-how-the-look-is-built.md)). Building the pages often shows a need the architect did not foresee: for example, a gap inside a task's row that no listed token is meant for. Once `implement` has started, the design is fixed ([ADR 0031](0031-documents-fixed-once-implement-starts.md)), and a design answer may not change a decision the design records ([ADR 0058](0058-design-answers-during-implement.md)). The "Tokens" table is a closed list, so adding a token reads as such a change, and every token the architect missed would stop the task for the maintainer. Writing the value as a literal instead breaks ADR 0067's rule, and the reviewer reports it.

What constrains the answer:

- The look the client agreed to, and its acceptance criteria, must not change inside the task.
- A new token must not bring a value the design never chose: the point of the tokens is that every page uses the same few values.
- The reviewer checks that an answer can be built within the areas the work may change and the conventions, and reports one that cannot at the answer, which stops the task for the maintainer ([ADR 0061](0061-answer-findings-stop-for-the-maintainer.md), #182).

## Options considered

1. **Keep the rule: every missing token stops the task for the maintainer.** Safe, but a token the architect missed is common and harmless, and each one costs the maintainer a decision.
2. **Let the developer add tokens to the token file.** No stop, but the developer then picks values, which is what ADR 0067 rules out, and nothing records why a token exists.
3. **Let a design answer add a token, under three conditions, and have the reviewer check it against "Look".** The architect, not the developer, adds it, in the design answers, where every reader finds it.

## Decision

Option 3. An answer in `keyturn/internal/design-answers.md` may add a token to the design's "Look" when all of these hold:

- **It only adds.** It names a new token, its group, and what it is used for. It never changes the value of a token the design or an earlier answer lists, never removes one, and never changes a row of "How the look's criteria are met", the styling method, the token file, or the checked widths and breakpoints.
- **Its value is on the scale the tokens already have.** The value is one a token of the same group already has, a reference to an existing token (`var(--<token>)`), or, for spacing steps and type sizes, a value on the scale the existing steps follow (for example, the next step of a 4 px scale), and the answer says which. Never a new color, a new font family, or any other value of its own.
- **The reviewer checks it.** `review` reads the answers that add tokens with the "Tokens" table: the token file must hold the design's tokens and those answers' tokens, and nothing else. An answer that breaks either condition above, or that contradicts the design's "Look" (for example, a token for a use that an existing token already covers, with another value), is a high `design fit` finding located at the answer, titled `A-<n> cannot stand as an answer`, as for an answer that cannot be built ([ADR 0061](0061-answer-findings-stop-for-the-maintainer.md), #182).

Such an answer goes through the same checks as every other answer (ADR 0058): it is built inside "Areas the work may change" (the token file is there), within the conventions. The form of `templates/internal/design-answers.md` gets an `Adds token:` line for it.

## Reasons

- The architect keeps choosing every value, and only from values the design already chose, so the pages still use the same few values, and the client's look and criteria do not change.
- The common case, a token the architect missed, no longer stops the task, while an answer that brings a value of its own is still found, by the reviewer, and stops the task for the maintainer.
- The answer records why the token exists, where QA and the reviewer read it.

## Consequences

- `skills/design/SKILL.md` ("Answering questions once implement has started") answers a missing token this way, `skills/implement/SKILL.md` writes the answer's token into the token file, and `skills/review/SKILL.md` checks the token file against the design's "Tokens" and these answers.
- A need that no value on the existing scale meets (a new color, for example) still cannot be answered inside the task: it goes to the maintainer, as before.
- The next change to the design writes the added tokens into "Tokens".
