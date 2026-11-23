<!--
Template: answers to the developer's and QA's questions, and to the threat ratings the security review questions (internal). Written by the architect (the `design` skill) after `implement` has started: when the developer or QA asks what the approved documents leave open, or when the maintainer decides that the architect answers a rating (ADR 0058 and ADR 0060 in keyturn's `docs/adr/`).

- Always written in English.
- Lives at `keyturn/internal/design-answers.md`. Entries are only added, numbered A-1, A-2, ... in order: never change, renumber, or remove one, and never write one that contradicts an earlier one.
- An answer to a question fills in only what the requirements, the design, the ADRs, the threat model, and the conventions leave open. It never changes a requirement or an acceptance criterion, an area the work may change, QA's folders, an external interface, the data model, a dependency or its version, a threat or its mitigation, or a decision an ADR or the design records; it never allows a suppression or an install script, and never decides what the client must agree to. It can be built by changing only paths inside "Areas the work may change", within every rule of the conventions and of the configs their "Tool rules" name (a lint rule among them). A question that needs any of these, or whose every answer breaks such a rule, is not answered here.
- A rating answer (the second form) is written only by the maintainer's decision. It raises a threat's rating, or keeps it and gives the reason it stands; it never lowers one, and never changes the threat's text, its mitigation, or what is left. It closes nothing: the security review alone decides whether its finding is fixed.
- Every word here is the architect's own. The developer's or QA's question, and the security review's finding, are never copied in, not even in part or in quotes: write what the design left open as a gap of the design, in your own words, and the answer the same way. An answer from the maintainer is written in your own words too, keeping what they decided (their words stay in the task state's "History"), under "Answered by: the maintainer". QA and the reviewers read this file, and only the architect's words reach them.
- Use one of the two forms below for each entry, and delete the other.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Design answers

Points the design left open, found after the work started, and the architect's answers, and threat ratings the architect raised or explained. They fill in what the design leaves open, and change nothing it decides except a threat's rating, which only goes up. Read them with the [design](design.md) and the [threat model](threat-model.md).

## A-<n>

- What the design left open: <the gap, as a gap of the design, in your own words, in one or two lines: never the question as it was asked>
- Asked by: <implement | qa>
- Answer: <the answer, specific enough to build from, and, for QA, to test through>
- Why it changes nothing: <which document leaves this open, why any answer within it fits, and that it builds within the areas and the conventions: one line>
- Answered by: <the architect | the maintainer>
- Reads with the design at: `<the full hash of the documents' commit>`
- Round: <n>
- Date: <YYYY-MM-DD>

## A-<n>

- Rating of: T-<n>, rated <low | medium> in the threat model (security review finding F-<n>, at `<the full hash of the report's commit>`)
- Answer: <raised to <medium | high> | kept at <low | medium>>
- Why: <what the threat lets someone do, in your own words, and why that calls for this rating; for a kept rating, the reason it stands: one or two lines>
- Answered by: <the architect | the maintainer>, by the maintainer's decision
- Reads with the design at: `<the full hash of the documents' commit>`
- Round: <n>
- Date: <YYYY-MM-DD>
