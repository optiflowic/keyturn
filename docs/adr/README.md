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
