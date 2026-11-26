# 0067. The design decides how the look is built, with one design-token file the code uses

- Status: accepted
- Date: 2026-11-26

## Context

The requirements now have a required "Look" section: a baseline (`standard` or `worked out`), a UI library (`none`, a name, or `chosen by the architect`), and the look's criteria as ordinary requirements and acceptance criteria ([ADR 0066](0066-requirements-ask-about-the-look-once.md)). Nothing yet says how the screens are built to meet them. In the rehearsal (#63), the web part had no styling at all; criteria alone do not stop each page from getting its own spacing, sizes, and colors, written as literal values wherever the developer needed one, which is how buttons with the same role end up with different sizes.

What constrains the answer:

- The design states the result and the ADRs keep the reasoning; the developer builds only what the design covers, and the reviewer checks the change against the design.
- A UI library, or any package a styling method needs, is a direct dependency, chosen and checked as any other ("Guardrails" 3, [ADR 0015](0015-dependency-kinds.md), [ADR 0018](0018-direct-dependencies-in-the-design.md), [ADR 0054](0054-newest-stable-versions-checked-against-the-runtime.md)), and a runtime dependency needs the client's agreement.
- When the client left the look to keyturn, keyturn takes the best practice at that time and records it (ADR 0066).
- Later work builds on what this decides: QA checks the look on the screens (#196), the client gets the evidence in a test report (#200), and an approved look, for example from Figma, brings its own tokens (#197).
- Linting styles (for example, Stylelint) is out of scope for now: no gate check reads the styles beyond formatting.

## Options considered

1. **Leave the styling to the developer.** No change to the design; every page decides its own values, and nothing ties them to one set that the reviewer, QA, or a later approved look can refer to.
2. **A "Look" section in the design, with the styling method and the values written in the design only.** The developer copies the values into the code wherever needed: they are the same in the design, but the code repeats them, and a later change to one value touches every page.
3. **A "Look" section in the design that names the styling method, one design-token file, and its tokens (spacing steps, type, colors, component shapes), with the rule that the code uses the tokens and never literal values of those kinds.** The values live in one place in the code, named as the design names them.
4. **The same as 3, with the tokens in the W3C Design Tokens format (JSON) and a build step that turns them into CSS.** The format that design tools export, but every project with screens then needs a token build tool, a dependency the client agrees to and that the gate does not know.

## Decision

Option 3.

- `templates/internal/design.md` has a required "Look" section, after "Libraries and external services". It takes the requirements' "Look" section as approved and says how it is built:
  - **Look baseline** and **UI library**: as the requirements say; a library is listed in "Libraries and external services" with its kind and check, as any dependency.
  - **Styling method**: how the pages are styled, with a link to its ADR. With a stack profile whose `README.md` names styling methods, one it approves; with a profile that names none, or no profile, one from the stack's documentation; a method that needs a package (for example, Tailwind CSS or a CSS-in-JS library) brings a dependency, chosen and checked as any other, and a runtime one needs the client's agreement.
  - **Token file**: the one file that holds every token, inside "Areas the work may change" (for `react-spa`, `src/styles/tokens.css` in the part, as CSS custom properties). With a UI library, it is where the library's theme takes its values from, so the library's look and the pages' own styles use the same tokens; a library whose theme cannot take its values from the token file without repeating them does not fit the stack.
  - **Checked widths**: the phone and desktop widths at which the look's criteria are met, so that the developer builds for them and QA checks at them (#196), and the breakpoints, if the layout changes at a width: CSS custom properties cannot be used in media queries, so the code may repeat a breakpoint as a literal there only.
  - **Tokens**: a table of every token (name, value, and what it is used for), in four groups: spacing steps, type (families, sizes, line heights, weights), colors (text, background, borders, the focused control, and what the baseline adds), and component shapes (control height, radius, borders, the focus outline).
  - **How the look's criteria are met**: one row per acceptance criterion of the look, naming the tokens and the rule that meet it (for example, AC-10: each label above its field, with `--space-2` between them).
  - The rule: the code uses the tokens for every spacing, type size, color, radius, control height, border width, and shadow; literal values of those kinds appear only in the token file (`0`, `auto`, `inherit`, and percentages are not such values). The developer writes the token file with exactly the design's tokens and values; a token the code needs that the design does not have is a question for the design, not a value the developer picks (once `implement` has started, a design answer may add it, as [ADR 0068](0068-design-answers-may-add-a-token.md) says).
- `skills/design/SKILL.md` fills the section from the requirements' "Look" section. The styling method gets an ADR, with the realistic options. When the requirements say the client left the look to keyturn, or name a decision card answered that way, the architect takes the best practice at that time for the chosen stack, checked in the stack's and the profile's current documentation (never from memory), and records it, with the date and the alternatives, in that ADR. A styling method that adds no dependency is "For information" in the design summary; one that adds a runtime dependency is "Must agree", as any dependency. A deliverable without screens (`Look baseline: none (no screens)`) has `None (no screens).` in the section; requirements approved before their "Look" section existed have `None: the requirements have no "Look" section.`, with the open question that `design` already writes.
- `profiles/react-spa/README.md` names the styling methods the profile approves, which need no package: CSS Modules (which Vite builds) with the token file as CSS custom properties, and, when the requirements name a UI library or leave its choice to the architect, the library's own styling with its theme taking its values from the token file. It also says what the gate does not check: that the code uses the tokens.
- The token file is not a protected path in the MVP: it is the developer's, inside the design's areas. The reviewer checks it against the design's "Tokens", and the code against the rule, as `design fit` findings.

## Reasons

- One token file gives every page the same spacing, sizes, and colors by construction, which is what the tidy minimum's criteria ask for (buttons with the same role the same size, space between labels and fields), and a change to one value is a change to one line.
- The design names the tokens and how each criterion is met, so the reviewer can check the code against something written, and QA (#196) and the client's test report (#200) have the widths and criteria to check against.
- CSS custom properties need no build tool and work with CSS Modules and with most UI libraries' themes, so the tidy minimum adds no dependency the client must agree to. Option 4's format is what design tools export, but its build step is a dependency every project would pay for before any approved look exists; #197 can convert an exported look into the token file, or supersede this decision if it needs that format.
- Option 2 keeps the values in the design but lets the code repeat them, so nothing in the code says that two buttons share a height.

## Consequences

- `templates/internal/design.md` gets the "Look" section, `skills/design/SKILL.md` fills and checks it, `profiles/react-spa/README.md` names the approved styling methods, and the worked example's design has the section filled in, with an ADR of the project for its styling method.
- The developer builds the token file and uses it; the reviewer has one more thing to check against the design. No gate check finds a literal value outside the token file until styles are linted (later work).
- QA's check of the look on the screens (#196) checks at the design's checked widths, and the client's test report (#200) carries its evidence; until then, the worked example's test report marks the look's criteria `not tested` and its acceptance guide has the client check them by hand.
- An approved look (#197) puts its tokens into the same file, through the same table in the design.
