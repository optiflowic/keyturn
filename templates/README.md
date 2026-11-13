# Templates

Templates for the documents that roles hand to each other and to the client.

- `client/`: client-facing documents (requirements, design summary, acceptance guide, delivery report). Written in the client's language by default.
- `internal/`: agent-to-agent documents (design, decisions, conventions, handoff, test report, review). Always written in English.

Each template has short filling instructions in HTML comments. Delete them, and the placeholders in `<angle brackets>`, when you fill in the template.

See "Documents" in [`docs/DESIGN.md`](../docs/DESIGN.md).

## Client-facing templates

| Template | Filled in by | Purpose |
|---|---|---|
| [`client/requirements.md`](client/requirements.md) | PM | What will be built and how it will be judged, with numbered requirements (`R-n`) and acceptance criteria (`AC-n`). The client approves it before work starts. |
| [`client/design-summary.md`](client/design-summary.md) | Architect | The main design decisions in plain language, with the reason, the alternatives, and what each means for the client. The decisions that need the client's agreement come first and link to their ADRs. The development tools approved by the stack profile are listed last, for information only. |
| [`client/acceptance-guide.md`](client/acceptance-guide.md) | PM | What the client checks by hand at delivery, in priority order, with steps and expected results. Each check names the `AC-n` it covers and is "Must check" (around five at most) or "Optional". |
| [`client/delivery-report.md`](client/delivery-report.md) | PM | What was delivered, what was verified and by whom (gate, QA, security, review), what was not verified, the remaining risks, triggered guardrails, and the models and tools used. |
| [`client/decision-card.md`](client/decision-card.md) | Any role | One question to the client: the context, the options, a recommendation, and what happens if the client does not answer. Short enough to answer in a few minutes. |
| [`client/approvals.md`](client/approvals.md) | PM | Which version of the requirements the client approved, in which language, and the SHA-256 of the source and of the translation they read, recorded when the version was sent. A "Current status" line says when an approval has gone stale. |

## Internal templates

| Template | Filled in by | Purpose |
|---|---|---|
| [`internal/design.md`](internal/design.md) | Architect | The structure, data model, libraries (each marked with its kind: runtime, profile tool, or other tool), and the areas (files or folders) the work may change, with the requirements (`R-n`) each part serves. |
| [`internal/threat-model.md`](internal/threat-model.md) | Architect | Assets, entry points, and threats (`T-n`, including misuse), each with its mitigation and how it is verified. The security role checks every mitigation is implemented. |
| [`internal/adr.md`](internal/adr.md) | Architect (or the role making the decision) | One decision per file: context, options considered, decision, reasons, consequences, and status. Follows the same structure as keyturn's own `docs/adr/template.md`. |
| [`internal/conventions.md`](internal/conventions.md) | Standards | The tool rules (formatter, linters, limits, boundaries between parts, forbidden patterns) with the config file of each, and a checklist (`C-n`) of only what no tool can check, for the reviewer. Changed only through an ADR. |
| [`internal/handoff.md`](internal/handoff.md) | Developer | What was done, which requirements it covers, what is left, how to run it, and what the next role must know. Only "How to run" is given to QA and security, so they never see the developer's reasoning. |
| [`internal/test-report.md`](internal/test-report.md) | QA | The result of every acceptance criterion (`AC-n`), failures, untested areas, and test counts. States when the tests treat the current behavior as correct because there was no specification. |
| [`internal/review.md`](internal/review.md) | Reviewer, Security | Findings with a location and a severity, for design fit, readability, and conventions. The security role also fills in the threat model check and the scan triage (false positives only with a recorded reason). |
