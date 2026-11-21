# Architecture Decision Records

This folder holds the decisions made for keyturn itself. Projects that use keyturn keep their own ADRs in their own repositories.

## Rules

- One decision per file: `NNNN-short-title.md`, numbered in order. Start from [`template.md`](template.md).
- Each ADR has a status: `proposed`, `accepted`, or `superseded`.
- Check the existing ADRs before making a decision. If an accepted ADR already covers the question, follow it.
- Do not edit an accepted ADR, except to mark it superseded. To change a decision, add a new ADR that explains what changed and links to the one it replaces.
- When a new ADR replaces only part of an accepted ADR, the old ADR stays `accepted`, and its status line names the part that was replaced and the new ADR's number.

See "Architecture decision records" in [`docs/design/documents.md`](../design/documents.md#architecture-decision-records).

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-public-repository-from-the-start.md) | Public repository from the start | accepted |
| [0002](0002-mit-license.md) | MIT license | accepted |
| [0003](0003-first-stack-profiles.md) | First stack profiles: `go` and `react-spa` | accepted |
| [0004](0004-independent-ai-reviewer.md) | Independent AI reviewer from a different vendor | accepted |
| [0005](0005-repository-root-as-plugin-root.md) | Repository root as the plugin root | accepted; what `adapters/claude/` holds superseded by [0020](0020-tool-specific-files-in-adapters.md) |
| [0006](0006-localize-helper-script.md) | A Python helper script for `localize` bookkeeping | accepted |
| [0007](0007-github-content-as-local-source-files.md) | GitHub content is translated as local source files | accepted |
| [0008](0008-approval-records-in-a-separate-file.md) | Approval records live in a separate file | accepted |
| [0009](0009-no-answer-is-not-consent.md) | An unanswered decision card is never decided on the client's behalf | accepted; `deliver` going on with a task's other work while a card waits replaced by [0031](0031-documents-fixed-once-implement-starts.md) during the MVP |
| [0010](0010-accepting-the-risk-of-a-low-threat.md) | The client may accept the risk of a low threat, on a decision card | accepted |
| [0011](0011-task-state-file.md) | The task state file is a Markdown file with fixed fields | accepted |
| [0012](0012-stable-approval-hashes.md) | Approved documents are checked out with LF, and the approved translation is kept next to the current one | accepted |
| [0013](0013-confirming-translations-into-english.md) | The client confirms a translation into English by reading it translated back | accepted |
| [0014](0014-project-configuration-in-json.md) | The project configuration is a JSON file, checked by a script before use | accepted |
| [0015](0015-dependency-kinds.md) | Which tools and libraries need the client's approval depends on their kind | accepted |
| [0016](0016-account-existence-is-data.md) | Learning whether an account exists counts as reading data | accepted |
| [0017](0017-qa-tests-in-their-own-folder.md) | QA's tests live in their own folder, outside the areas the developer may change | accepted |
| [0018](0018-direct-dependencies-in-the-design.md) | The design lists direct dependencies; the lock file covers the rest | accepted |
| [0019](0019-pre-pull-request-review.md) | A fresh subagent reviews the diff once before a pull request is opened | accepted; "the review that needs judgment stays with CodeRabbit and the maintainer" superseded by [0022](0022-second-review-stage-for-skills-gates-adapters.md) for `skills/`, `gates/`, and `adapters/`; fixing every right finding superseded by [0026](0026-review-points-until-the-mvp.md) until the MVP |
| [0020](0020-tool-specific-files-in-adapters.md) | Everything one tool uses lives in its adapter folder; files the tool needs at the plugin root stay thin | accepted |
| [0021](0021-design-split-into-section-files.md) | The design is split into one file per section; `docs/DESIGN.md` stays as an index that keeps every heading | accepted |
| [0022](0022-second-review-stage-for-skills-gates-adapters.md) | A second review stage, on a higher-tier model, before pull requests that change skills, gates, or adapters | accepted; fixing every right finding superseded by [0026](0026-review-points-until-the-mvp.md) until the MVP |
| [0023](0023-releasing-usage-stops.md) | A person releases a usage stop until the window resets | accepted |
| [0024](0024-windows-a-plan-has-are-a-setting.md) | The windows a plan has are a setting the person makes, never inferred from a missing value | accepted |
| [0025](0025-mvp-first.md) | Build a minimum viable keyturn first, and move the rest to enhancements | accepted |
| [0026](0026-review-points-until-the-mvp.md) | Until the MVP, only Critical and Major review points and points that block the flow are fixed | accepted |
| [0027](0027-when-an-agent-may-add-no-review.md) | An agent may add `no-review` to a pull request that meets three fixed conditions | accepted |
| [0028](0028-gate-interface.md) | The gate is a Python CLI behind `gates/gate.sh`, run on a Git range, with JSON stack profiles | accepted |
| [0029](0029-role-commits-passed-as-arguments.md) | `deliver` names each role's commits to the gate and the reviews as arguments; the task state file only records them | accepted; the range's start, and `resume` listing its state commit only past it, superseded by [0032](0032-gate-base-is-where-the-task-branch-left.md); what `deliver` may write superseded by [0033](0033-delivery-documents-from-the-records.md) |
| [0030](0030-deliver-rework-loop.md) | `deliver` sends work back on a failing gate, a failing test, and high or medium findings, up to a set number of rounds | accepted |
| [0031](0031-documents-fixed-once-implement-starts.md) | During the MVP, a task runs alone, and its requirements, design, and conventions are fixed once `implement` starts | accepted |
| [0032](0032-gate-base-is-where-the-task-branch-left.md) | The gate's base is where the task branch left the default branch, and the document roles' commits are named too | accepted |
| [0033](0033-delivery-documents-from-the-records.md) | `deliver`'s last step writes the acceptance guide and the delivery report from the committed records, in a context of its own | accepted |
| [0034](0034-new-task-waits-for-unmerged-task-branches.md) | A new task waits while a task branch is not merged into the default branch, unless the person says to start anyway | accepted |
| [0035](0035-subagent-tools-and-models.md) | Each role's subagent preloads its skill, and gets only the file tools and the shell, on a model set by its tier | accepted |
| [0036](0036-minimal-permission-rules.md) | During the MVP, the recommended permission rules deny every push and the commands that discard work, in the person's local settings | accepted |
