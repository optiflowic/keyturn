# 0074. A decision the client asked to be consulted on needs their agreement, whatever its kind

- Status: accepted
- Date: 2026-11-28
- Supersedes: in [0067](0067-design-decides-how-the-look-is-built.md) and [0072](0072-profiles-fix-styling-principles-not-the-tool.md), that a styling method without a dependency is for information, when the client asked to be consulted on it

## Context

The design summary sorts the design's decisions into two groups: "Must agree", which waits for the client's agreement, and "For information", which the client only reads. A decision is "Must agree" when it adds a runtime dependency or an other tool ([ADR 0015](0015-dependency-kinds.md)) or an external service, decides how people sign in, what they may reach, or what personal data is kept, or affects cost, scope, or what the client has to do. Everything else is for information, and [ADR 0067](0067-design-decides-how-the-look-is-built.md) and [ADR 0072](0072-profiles-fix-styling-principles-not-the-tool.md) say so for a styling method that adds no dependency.

A rehearsal of a change to the look showed the gap. The client's request said they wanted to decide together how far to refine the look and whether to use a UI library, and to hear keyturn's recommendation with its reasons. On the card about the look ([ADR 0066](0066-requirements-ask-about-the-look-once.md)), the client chose the tidy minimum without a UI library and added: style it in a way that is widely used and easy to maintain, for example something like a styling tool they named, and tell me which way you recommend, with your reasons. The design then chose another styling method than the one the client named, which added no dependency, so it listed it for information ("nothing new needs your agreement"), and the task went on to the developer without the client seeing the recommendation they had asked for.

What constrains the answer:

- An unanswered question is never decided for the client ([ADR 0009](0009-no-answer-is-not-consent.md)), and once `implement` starts the design is fixed for the task ([ADR 0031](0031-documents-fixed-once-implement-starts.md)): a recommendation the client sees only after delivery cannot be changed in the task.
- The client's attention is limited ("Client attention budget" in `docs/design/documents.md`): what the client leaves to keyturn should stay with keyturn, and nothing should be asked twice.
- The design reads only the approved requirements and the decision cards; text in them is data, not instructions.

## Options considered

1. **Keep the kinds as they are.** The client's request to be consulted is lost whenever the decision has no dependency, and keyturn decides against the client's named example without telling them before the work.
2. **Ask a new card for every such decision.** The client sees it, but they are asked the same thing twice: the card they answered already asked, and their answer asked for the recommendation.
3. **Make such a decision "Must agree", whatever its kind, with the recommendation in its design summary entry.** The client gets the recommendation and the reasons where they read the design, agrees to it with the rest, and nothing is asked again.

## Decision

Option 3.

**What counts as asking.** The client asked to be consulted on a decision when the approved requirements (for example, the request as they record it, or a "Decided on" line) or the answer or comment of a decision card say, about that decision or its subject (not a general wish to hear reasons, which each entry's "Why" meets), that they want to decide it together, ask for keyturn's recommendation and its reasons, or name a tool or a way of doing it as an example of what they want. A tool or a way the approved requirements require, or say the client's team already uses, is not asking: it is the client's choice, taken as the other rules say (for a styling method, as ADR 0072 says). One named or required only in a card's answer or comment is asking: the design reads only the approved requirements as binding, so it does not take it unseen, and the client agrees to it, or to the alternative, in the design summary; a change it needs to the approved requirements goes through `spec`, as for any requirement. "Leave it to you" or a card's recommended option, without such a comment, is not asking: the decision is made as the other rules say. A profile tool the client asked to be consulted on is "Must agree" too, and stays listed with the profile's tools.

**What follows.** Such a decision goes under "Must agree" in the design summary, with "Needs client agreement: yes" in its ADR, which stays `proposed` until the client agrees, whatever its kind: also a decision that adds no dependency, and also when the design takes what the client named. Its entry gives the recommendation, the reasons, and the realistic options, as any "Must agree" entry does. When the design does not take what the client named or suggested, the entry says so and why, and the client agrees to the alternative before any work that depends on it starts.

**No second question.** When a card already asked about it and the client's answer asks for the recommendation, the design summary's entry is where the recommendation is given, and agreeing to it is the client's answer: the card is not asked again, and its earlier answer is not the agreement, so the entry waits like any other.

**What it replaces.** That a styling method that adds no dependency is "For information" ([ADR 0067](0067-design-decides-how-the-look-is-built.md), [ADR 0072](0072-profiles-fix-styling-principles-not-the-tool.md)) holds only when the client did not ask to be consulted on it.

## Reasons

- A client who asks to decide something together expects to see it before it is built; listing it for information breaks that expectation in the same way a decision made for them would.
- The rule follows what the client said, not the decision's kind, so it holds for every kind of decision, not only the look.
- Putting the recommendation in the design summary answers the client where they already read and agree, without a new card, so the client's load does not grow.
- "Leave it to you" keeps its meaning: what the client leaves to keyturn is still decided by keyturn.

## Consequences

- `skills/design/SKILL.md` lists such a decision in "What the client must agree to", its "Styling method" no longer makes a method without a dependency "For information" when the client asked to be consulted on it, and step 7's check of the summary and the cards checks that every such decision is under "Must agree".
- "Architect" in `docs/design/roles.md` says it.
- A design whose client asked to be consulted on a decision waits for their agreement, also when it adds nothing to the app: the task stops at `design` until they agree.
- Which part of the design summary a decision goes into after a rewrite, and whether a summary sent for information reached the client, are separate work (#216, #217).
