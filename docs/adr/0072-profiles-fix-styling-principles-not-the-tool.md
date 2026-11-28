# 0072. A stack profile fixes how the pages use the tokens, not the styling tool, and the design chooses the styling method with the client

- Status: accepted; that a styling method without a dependency is for information superseded by [0074](0074-decisions-the-client-asked-to-be-consulted-on-need-agreement.md) when the client asked to be consulted on it
- Date: 2026-11-28
- Supersedes: in [0067](0067-design-decides-how-the-look-is-built.md), the styling methods a profile approves, the token file's form, and a UI library that does not fit the stack: a profile states the principles and a default method, and the design chooses any method that keeps them; one token file: one file by default, which the design may split when the project's scale calls for it, each token defined once; and a breakpoint repeated as a literal in media queries only: it may be repeated wherever the token file's form cannot be used; in [0068](0068-design-answers-may-add-a-token.md), the form of a reference to an existing token: it follows the token file's form

## Context

ADR 0067 has the design name a styling method, one token file, and its tokens, with the rule that the code uses the tokens and never literal values of their kinds. It also has the `react-spa` profile approve a closed list of styling methods, fixes the token file's form for that profile, and rules out a UI library whose theme cannot take the values in that form. A method outside the list needed the client's agreement and was something the profile "does not fit", even when it keeps the rule.

That breaks the rule ADR 0069 states: keyturn fixes the way of working, not the tools; a stack profile names the tools for its stack as the best practice at the time it is written, and a project's design may choose another with the client. Styling tools change quickly, and the client, or the people who will maintain the deliverable after delivery, may already use one. ADR 0068 has the same problem on a smaller scale: it writes a reference to an existing token in one form only.

What constrains the answer:

- What ADR 0067 keeps is right: one definition of each of the design's tokens, and no literal values of their kinds outside them. Those are what make the pages consistent, and what the reviewer and QA check against. How many files hold the tokens, and whether their values are the project's own or a scale the method ships, depend on the project's scale and the method, not on that rule.
- A styling method that needs a package brings a dependency, checked as every other one ("Guardrails" 3, [ADR 0015](0015-dependency-kinds.md), [ADR 0054](0054-newest-stable-versions-checked-against-the-runtime.md), [ADR 0055](0055-installs-skip-install-scripts.md), [ADR 0056](0056-gate-fails-new-packages-with-install-scripts.md)); one that is part of the deliverable or builds it is a runtime dependency, which needs the client's agreement.
- Maintainability after delivery as a criterion of the design's choices is its own decision (#211); this one must leave room for it.

## Options considered

1. **Keep the closed list, and add methods to it as clients ask.** Every new method waits for a change to keyturn, and the list goes out of date with the tools.
2. **Drop styling from the profile, and leave the method and the rule to each design.** No list to keep up, but each design restates the rule, and nothing tells the architect what the stack's usual method is today.
3. **The profile states the principles and names one default method as the best practice at the time it is written; the design chooses the method with the client among the realistic options, recorded in an ADR, and the token file's form follows the method.** The rule stays fixed in one place; the tool is a choice.

## Decision

Option 3.

**The principles.** For every part with screens, whatever the method:

- The token file holds every token the design's "Look" lists, each defined once. It is one file by default; when the project's scale calls for it (for example, one file per theme, or per part of a large application), the design splits the tokens over several files and names them all, and "the token file" means all of them. Every spacing, type size, color, radius, control height, border width, and shadow the pages use comes from it, as a reference to a token in the form the method gives.
- No literal value of those kinds appears outside the token file: not in style sheets, not in class names that carry a value, not in style objects in the code, and not in inline style attributes. `0`, `auto`, `inherit`, and percentages are not such values, nor is a breakpoint the design names, where the token file's form cannot be used (for example, in a media query).
- Where the tokens' values come from is the design's choice, recorded in the styling method's ADR: the design's own values, which replace the method's built-in scale or theme so that only the design's tokens are available to the code; or a built-in scale that the method or a UI library ships, adopted as it is when it meets the look's criteria, with the steps the pages use listed as the design's tokens. Either way, a value the project's code writes that the design's tokens do not list is a literal value for this rule, also when it comes from the method's scale (for example, a class name for another step). A UI library's default theme stays as the library ships it wherever the project does not change it.
- A UI library's theme takes the values the design's tokens decide from the token file, by referencing the tokens without repeating them, so the library and the pages' own styles use the same values where the design decides them. The token file does not have to replace the rest of the library's theme.

**The profile.** A stack profile with screens states these principles for its stack in its `README.md`, and names a default method, with the token file's place and form, as the best practice at the time it is written, with the date and where it was checked, as it names its E2E tool (ADR 0069). It may also say what the stack's other realistic methods need. From this ADR on, the names of styling tools appear only in the profiles, never in keyturn's skills, templates, or new ADRs, which state the principles.

**The design.** The architect chooses the styling method among the realistic options for the stack, the profile's default among them, and records it in an ADR of the project with the options and the reasons. The token file's form follows the method, and so does where the values come from, as long as each token is defined once. When the client left the look to keyturn, the architect takes the best practice at that time, checked in current documentation (never from memory), as ADR 0067 says. A method that needs a package brings a dependency, checked as every other one, and a runtime one needs the client's agreement under "Must agree"; one that needs none is "For information". A UI library fits the stack when some method lets its theme take the values the design's tokens decide from the one token file; when none does for the library the client named, the design asks on a decision card, as ADR 0067 says.

**The checks.** The reviewer checks the code against the principles, in whatever form the method writes styles, and the token file against the design's tokens; QA measures the pages in a browser, which does not depend on the method. An answer that adds a token (ADR 0068) may reference an existing token in the token file's form.

## Reasons

- The principles are what make the pages consistent and checkable; the tool is how one project meets them. Fixing only the principles keeps the rule true when the tools change, as ADR 0069 does for the E2E tool.
- Naming a default keeps the common case quick: the architect starts from the profile's default, and a project that needs another method chooses it with the client, without a change to keyturn.
- Counting every value the design's tokens do not list as a literal value, also one from the method's scale, closes the gap a method with its own scale would open: without it, the pages could use values the design never named while every one of them comes from "the method".
- Leaving the number of token files and the source of the values to the design keeps the rule the same for a small project and a large one: a few tokens fit one file, while themes or many parts call for several; and a widely used built-in scale, adopted as it is, may be easier for the client's people to maintain than the project's own values (#211). What keeps the pages consistent is one definition per token and no value the design does not list, not the number of files.
- Limiting that to the values the project's code writes keeps a UI library usable: its default theme has many values the design never needs to name, and replacing all of them would make the token file restate the library. The library's look is what the client agreed to when it was chosen; the token file decides only where the design does.
- Keeping tool names in the profiles only means that a new tool changes one profile, not the skills, the templates, and the ADRs.

## Consequences

- `profiles/react-spa/README.md` states the principles and its default method, with the date it was checked, and what its other realistic methods need. `docs/design/stack-profiles.md` says that a profile fixes the styling principles, not the tool.
- `skills/design/SKILL.md` and `templates/internal/design.md` let the design choose any method that keeps the principles, with the dependency check for one that needs a package. `skills/review/SKILL.md` checks the principles in any form, and `templates/internal/design-answers.md` writes an added token without a form of its own.
- The gate still does not check the styles, as ADR 0067 says: a literal value outside the token file is found by the reviewer, not the gate.
- #211 adds maintainability after delivery as a criterion of the design's choices; the styling method is one of them, compared in its ADR with the other criteria.
