<!--
Template: answers to the developer's questions (internal). Written by the architect (the `design` skill) after `implement` has started, when the developer asks what the approved documents leave open (ADR 0058 in keyturn's `docs/adr/`).

- Always written in English.
- Lives at `keyturn/internal/design-answers.md`. Entries are only added, numbered A-1, A-2, ... in order: never change, renumber, or remove one, and never write one that contradicts an earlier one.
- An answer fills in only what the requirements, the design, the ADRs, the threat model, and the conventions leave open. It never changes a requirement or an acceptance criterion, an area the work may change, QA's folders, an external interface, the data model, a dependency or its version, a threat or its mitigation, or a decision an ADR or the design records; it never allows a suppression or an install script, and never decides what the client must agree to. A question that needs any of these is not answered here.
- Every word here is the architect's own. The developer's question is never copied in, not even in part or in quotes: write what the design left open as a gap of the design, in your own words, and the answer the same way. An answer from the maintainer is written in your own words too, keeping what they decided (their words stay in the task state's "History"), under "Answered by: the maintainer". QA and the reviewers read this file, and only the architect's words reach them.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Design answers

Points the design left open, found after the work started, and the architect's answers. They fill in what the design leaves open, and change nothing it decides. Read them with the [design](design.md).

## A-<n>

- What the design left open: <the gap, as a gap of the design, in your own words, in one or two lines: never the developer's question>
- Answer: <the answer, specific enough to build from>
- Why it changes nothing: <which document leaves this open, and why any answer within it fits: one line>
- Answered by: <the architect | the maintainer>
- Reads with the design at: `<the full hash of the documents' commit>`
- Round: <n>
- Date: <YYYY-MM-DD>
