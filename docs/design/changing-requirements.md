# Changing Requirements

Requirements change during development, as in agile development. keyturn treats requirements as a living, versioned document rather than a fixed contract.

- **Stable IDs.** Every requirement and acceptance criterion has an ID (e.g., `R-3`, `AC-5`) that never changes or gets reused. Removed items are marked as removed, not deleted.
- **Traceability.** Tests, design decisions, and deliveries reference the IDs they cover, so a change to one item shows what else is affected.
- **Change requests are issues.** Each change goes through the PM, who updates the requirements and writes an impact summary for the client: what changes, what is affected, and whether it conflicts with existing requirements.
- **Conflicts are surfaced, not resolved silently.** If a new request contradicts an approved requirement, the client decides.
- **History is kept.** requirements.md has a short changelog, and git keeps the full history.
- **Small increments.** Work is delivered in small pieces, which keeps each acceptance check short (see [Client attention budget](documents.md#client-attention-budget)) and makes changes cheaper.
