# 0073. The design weighs how easily the client's people can maintain each choice after delivery, with a weight set from the request

- Status: accepted
- Date: 2026-11-28

## Context

In contract development, the client usually maintains the deliverable after delivery, with their own people or another vendor. The design chooses tools and approaches for fit with the stack and the requirements, and checks each dependency for existence, maintenance status, known vulnerabilities, license, and supply-chain risks ("Guardrails" 3, [ADR 0015](0015-dependency-kinds.md), [ADR 0054](0054-newest-stable-versions-checked-against-the-runtime.md)). Nothing asks whether the client can find people who know the tool, or material to learn it from.

A rehearsal showed the cost. Its deliverable, a small web application of four pages, had routing written by hand to keep the dependencies few, where most people who work with that stack would reach for its standard router first. Whoever maintains hand-written routing must first work out how it works, and a later delivery's review found a defect in its own URL handling that left the screen blank. The design's rule "avoid a dependency only when the alternative fits as well" let keeping the dependencies few pass as a reason on its own.

What constrains the answer:

- keyturn fixes only its promises, and chooses everything else for each request and at that time (#214). This criterion is a way of choosing, not a list of tools: it names no tool, and a stack profile's default is one of the options it compares, as [ADR 0069](0069-qa-checks-the-screens-end-to-end-in-a-browser.md) and [ADR 0072](0072-profiles-fix-styling-principles-not-the-tool.md) say for the E2E tool and the styling method.
- How much maintainability matters depends on the request: a tool that nobody will maintain after a short use needs little of it; a system another vendor will maintain for years needs much.
- The client's attention is limited ("Client attention budget" in `docs/design/documents.md`): a new question should be folded into a decision the client already reads.
- Every dependency still goes through the supply-chain checks, whatever the reason it was chosen ([ADR 0055](0055-installs-skip-install-scripts.md), [ADR 0056](0056-gate-fails-new-packages-with-install-scripts.md)).
- A signal such as how widely a tool is used changes over time; a value from memory may be years old ([ADR 0054](0054-newest-stable-versions-checked-against-the-runtime.md)).

## Options considered

1. **Fit only, as today.** Simple, but it keeps choosing what is easiest for the architect today, not for the people who maintain the deliverable, and it lets "fewer dependencies" justify rebuilding a standard feature.
2. **Maintainability always with the same weight as fit.** Easy to apply, but wrong for a short-lived tool, and for a client whose team already knows a tool that a general comparison ranks lower.
3. **Maintainability weighed against fit as the request calls for, with the same weight when the request says nothing about who maintains the deliverable; the PM asks the client about it on a card of its own with the first requirements.** The weight fits the request, but the client gets one more question, asked before anything they could weigh it against.
4. **As option 3, but the design states the weight and its reason, takes them from the requirements when they say, and folds the question into the design summary the client already answers.** The weight fits the request, and the client corrects an assumption when agreeing to the design, without a card of its own.

## Decision

Option 4.

**What it applies to.** Every choice of a tool or an approach the deliverable is built or tested with: the stack, the repository structure, the data store, each library or group of libraries used together, the styling method, and the test tools the design chooses. Writing a standard feature by hand is one of the options compared, against the widely used library or the stack's own feature that does it (for example, the pages' routing, against the stack's standard router). Keeping the dependencies few is not, on its own, a reason to avoid the standard choice: a dependency that fits and is easier to maintain is proposed, with the client's agreement for a runtime one, and checked like every other ("Guardrails" 3).

**The signals.** Maintainability after delivery is judged from five signals, each from current sources checked at the time, with the source and the date, never from memory:

- **Use**: how widely it is used, from current signals (for example, the repository's stars, the package's downloads, and how recent its releases are).
- **Modern**: whether the stack's current documentation still recommends it. An option that the current documentation no longer recommends, or calls legacy, counts against it, even when it is widely used.
- **Documentation**: how much documentation and learning material there is, its own and others'.
- **People**: how easy it is to find people who know it. A tool the client's team, or the vendor who will maintain the deliverable, already knows counts for it more than any general signal.
- **Stability**: how stable it is over time: how often its releases break what was built with it, and whether it has a supported upgrade path.

Code written by hand for the project has no use, documentation, or people outside it: whoever maintains it learns it from the code alone, which counts against it on those signals.

**The weight.** The design weighs maintainability against fit as the request calls for: who maintains the deliverable after delivery (the client's own team, another vendor, or nobody, for a short-lived tool), for how long, and which tools that team already knows. It takes them from the approved requirements, or from the client's answer. When the request says nothing about who maintains the deliverable, the two have the same weight. A less known option that fits clearly better can still be chosen, with the reason.

**The client's preference.** A tool or a stack the approved requirements name as one the client's team already uses is the client's choice, taken and checked as a dependency, as ADR 0072 says for the styling method. When the requirements do not say who maintains the deliverable, `spec` does not ask: the design summary says what the design assumed (who maintains it, and the weight that gave) and that the client may say otherwise when they answer, which folds the question into the agreement the client already gives. An answer that changes the weight changes the design as any answer that disagrees with it: the weight is set again, each ADR it changes is redone (one already accepted is superseded), and in English-only mode the answer is confirmed as any answer that changes what is built. When the client does not answer it, also when nothing in the design summary needs their agreement, the assumption stands. The assumption needs no consent of its own: the same weight is the rule for a request that says nothing, not a decision made for the client ([ADR 0009](0009-no-answer-is-not-consent.md)).

**The ADR.** Each ADR of such a choice says the weight it gave and why (from which requirement, from the client's answer, or that the request says nothing), and how each realistic option compares on the five signals, with the sources checked and their date. A signal that cannot be checked (for example, without network access) is written as `not checked: <why>`, as a dependency's check is.

**The design summary.** When the design chooses an option that is less known than another realistic option on this criterion (including code written by hand instead of a widely used library), the design summary's entry for that decision says so in "What it means for you", and why: the client's people maintain it after delivery, so the client should know before agreeing to the design. This holds also for a decision listed for information only.

**What stays fixed.** The criterion does not name or rank tools, and it changes no stack profile's choices. The names of tools appear only in the profiles and in a project's own documents, never in keyturn's skills, templates, or ADRs (ADR 0072).

## Reasons

- The people who maintain the deliverable are usually not the ones who built it. A choice they can find help for, and people for, costs the client less over the deliverable's life than one they must learn from the code.
- A weight set from the request keeps the criterion right for both ends: a short-lived tool is not held to the standard of a long-lived system, and a client's own team's tools count for what they are.
- The same weight when the request says nothing keeps the default neutral: neither fit nor maintainability wins by silence.
- Folding the assumption into the design summary asks the client nothing new before they can weigh it; they read it next to the decisions it affects, and correct it there.
- Checking the signals at the time, with the date, keeps the comparison honest as tools rise and fall; a signal from memory is the same failure as a version from memory (ADR 0054).
- Telling the client about a less known choice lets them object before they own it.

## Consequences

- `skills/design/SKILL.md` weighs maintainability where tools and approaches are chosen, and says what the ADR and the design summary say about it; its rule on avoiding a dependency no longer lets fewer dependencies be a reason on its own.
- `templates/internal/adr.md` has a section for the weight and the comparison, and `templates/client/design-summary.md` says where the assumption about who maintains the deliverable and a less known choice go. The worked example in `evals/requests/task-manager/example/` shows both.
- "Architect" in `docs/design/roles.md` names the criterion.
- `spec` does not change; the requirements state who maintains the deliverable only when the client says so in the request or in an answer.
- Each design takes a little longer: the signals are checked per option. A guide for the people who maintain the deliverable is separate work (#212), and choosing a library when a task starts, with this criterion, comes with #214.
