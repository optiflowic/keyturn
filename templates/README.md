# Templates

Templates for the documents that roles hand to each other and to the client.

- `client/`: client-facing documents (requirements, design summary, acceptance guide, delivery report). Written in the client's language by default.
- `internal/`: agent-to-agent documents (design, decisions, handoff, test report, review). Always written in English.

Each template has short filling instructions in HTML comments. Delete them, and the placeholders in `<angle brackets>`, when you fill in the template.

See "Documents" in [`docs/DESIGN.md`](../docs/DESIGN.md).

## Client-facing templates

| Template | Filled in by | Purpose |
|---|---|---|
| [`client/requirements.md`](client/requirements.md) | PM | What will be built and how it will be judged, with numbered requirements (`R-n`) and acceptance criteria (`AC-n`). The client approves it before work starts. |
| [`client/design-summary.md`](client/design-summary.md) | Architect | The main design decisions in plain language, with the reason, the alternatives, and what each means for the client. The decisions that need the client's agreement come first and link to their ADRs. |
