<!--
Template: answers to the developer's questions (internal). Written by the architect (the `design` skill) after `implement` has started, when the developer asks what the approved documents leave open (ADR 0058 in keyturn's `docs/adr/`).

- Always written in English.
- Lives at `keyturn/internal/design-answers.md`. Entries are only added, numbered A-1, A-2, ... in order: never change, renumber, or remove one, and never write one that contradicts an earlier one.
- An answer fills in only what the requirements, the design, the ADRs, the threat model, and the conventions leave open. It never changes a requirement or an acceptance criterion, an area the work may change, QA's folders, an external interface, the data model, a dependency or its version, a threat or its mitigation, or a decision an ADR or the design records; it never allows a suppression or an install script, and never decides what the client must agree to. A question that needs any of these is not answered here.
- An answer from the maintainer is written as they gave it, in English, under "Answered by: the maintainer".
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Design answers

Answers to questions the developer asked after the work started. They fill in what the design leaves open, and change nothing it decides. Read them with the [design](design.md).

## A-<n>

- Question: <the question, as the developer asked it, in one or two lines>
- Answer: <the answer, specific enough to build from>
- Why it changes nothing: <which document leaves this open, and why any answer within it fits: one line>
- Answered by: <the architect | the maintainer>
- Reads with the design at: `<the full hash of the documents' commit>`
- Round: <n>
- Date: <YYYY-MM-DD>
