# 0008. Approval records live in a separate file

- Status: accepted
- Date: 2026-11-08

## Context

The client approves the requirements in the language they read, often through a local translation made by `localize` (see "Approving translated content" in `docs/DESIGN.md`). The approval must record which version they read, by the SHA-256 of the source, so that a later change to the source makes the approval visibly stale.

`localize` already records the SHA-256 of the whole source file in the first line of each translation. The question is where the approval record goes. If it goes inside `requirements.md`, writing it changes the file, so the file's hash no longer matches the hash that was approved, and every approval would be stale the moment it is recorded. Changing the file's `Status` line to "approved" has the same effect.

## Options considered

1. **A separate approval file** (`keyturn/client/approvals.md`), one row per approval: the document, its version, the language read, the source SHA-256, the date, and who approved. `requirements.md` does not change when it is approved. An approval is current when its hash equals the SHA-256 of the current file. No change to `localize`.
2. **The record inside `requirements.md`, left out of the hash**: the hash would cover the file without the approval section and the `Status` line. Keeps everything in one file, but `localize` hashes whole files, so it would need a keyturn-specific exclusion rule, and the hash shown in a translation would no longer match the hash in the approval.
3. **The record inside `requirements.md`, by Git commit**: record the commit of the approved version and compare it with `git diff`. The commit that records the approval still changes the file, so an exclusion rule is still needed, and matching the commit to the translation the client read is a manual step.

## Decision

Approvals are recorded in `keyturn/client/approvals.md` (option 1). The hash is the SHA-256 of the approved file's bytes, which is the `sha256` value on the first line of a fresh translation of it.

## Reasons

- The approved file and the hash stay identical, so checking an approval is one comparison: hash the current file and compare it with the row.
- The hash in the record is the one `localize` already shows in the translation the client read, so the approved translation is identified without new tooling. `localize` stays a general tool with no keyturn-specific rules.
- The file is plain Markdown, so the client portal and the GitHub integration (phases 7 and 8) can read and append to it later.

## Consequences

- `requirements.md` must not change after it is sent for approval, not even its `Status` line or "What you need to do". Any edit starts a new version that needs a new approval. Its `Status` line only goes up to "waiting for approval"; whether a version is approved is read from `approvals.md`.
- The changelog row for a version is written before the version is sent for approval.
- Checking whether an approval is stale means hashing the file (`shasum -a 256` or `sha256sum`). The skills in phase 3 do this for the client.
- Other documents the client approves or agrees to (for example, `design-summary.md`) could use the same file later; that is a separate decision.
