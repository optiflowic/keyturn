# Architecture Decision Records

This folder holds the decisions made for keyturn itself. Projects that use keyturn keep their own ADRs in their own repositories.

## Rules

- One decision per file: `NNNN-short-title.md`, numbered in order. Start from [`template.md`](template.md).
- Each ADR has a status: `proposed`, `accepted`, or `superseded`.
- Check the existing ADRs before making a decision. If an accepted ADR already covers the question, follow it.
- Do not edit an accepted ADR, except to mark it superseded. To change a decision, add a new ADR that explains what changed and links to the one it replaces.

See "Architecture decision records" in [`docs/DESIGN.md`](../DESIGN.md).

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-public-repository-from-the-start.md) | Public repository from the start | accepted |
| [0002](0002-mit-license.md) | MIT license | accepted |
| [0003](0003-first-stack-profiles.md) | First stack profiles: `go` and `react-spa` | accepted |
| [0004](0004-independent-ai-reviewer.md) | Independent AI reviewer from a different vendor | accepted |
| [0005](0005-repository-root-as-plugin-root.md) | Repository root as the plugin root | accepted |
| [0006](0006-localize-helper-script.md) | A Python helper script for `localize` bookkeeping | accepted |
| [0007](0007-github-content-as-local-source-files.md) | GitHub content is translated as local source files | accepted |
| [0008](0008-approval-records-in-a-separate-file.md) | Approval records live in a separate file | accepted |
| [0009](0009-no-answer-is-not-consent.md) | An unanswered decision card is never decided on the client's behalf | accepted |
| [0010](0010-accepting-the-risk-of-a-low-threat.md) | The client may accept the risk of a low threat, on a decision card | accepted |
| [0011](0011-task-state-file.md) | The task state file is a Markdown file with fixed fields | accepted |
| [0012](0012-stable-approval-hashes.md) | Approved documents are checked out with LF, and the approved translation is kept next to the current one | accepted |
| [0013](0013-confirming-translations-into-english.md) | The client confirms a translation into English by reading it translated back | accepted |
| [0014](0014-project-configuration-in-json.md) | The project configuration is a JSON file, checked by a script before use | accepted |
| [0015](0015-dependency-kinds.md) | Which tools and libraries need the client's approval depends on their kind | accepted |
| [0016](0016-account-existence-is-data.md) | Learning whether an account exists counts as reading data | accepted |
| [0017](0017-qa-tests-in-their-own-folder.md) | QA's tests live in their own folder, outside the areas the developer may change | accepted |
| [0019](0019-pre-pull-request-review.md) | A fresh subagent reviews the diff once before a pull request is opened | accepted |
