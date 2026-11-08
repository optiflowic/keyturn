<!--
Template: approval record (client-facing). Kept by the PM in keyturn/client/approvals.md. See ADR 0008 in keyturn's docs/adr/.

- One row per approval, newest last. Never edit or delete a row; a new approval is a new row.
- "Source SHA-256" is the SHA-256 of requirements.md exactly as the client approved it.
  When the client read a translation, it is the sha256 value on the first line of that translation.
  Before asking for approval, check that the translation is fresh (localize status), so it matches the current file.
  When the client read the file itself, compute it with `shasum -a 256 keyturn/client/requirements.md` or `sha256sum keyturn/client/requirements.md`.
- "Language" is the language the client read, with "(translation)" when they read a translation and "(original)" when they read the file itself.
- An approval is current only if its "Source SHA-256" equals the SHA-256 of the current requirements.md. If they differ, the approval is stale:
  the requirements changed after the client approved them, and the new version needs a new approval.
- Write for a client who does not read code. Write the headings and the text in the client's language, unless the project uses English-only mode.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Approvals

This file records which version of the requirements you approved, and in which language you read it.

## How to tell whether an approval is still current

<!-- Keep this section short. The client should not need to understand hashes to read it. -->

Each row identifies the exact text you approved by a fingerprint ("Source SHA-256"). If the requirements change after your approval, the fingerprint of the current file no longer matches the row, and we ask you to approve the new version. We tell you when that happens; you do not need to check it yourself.

## Approvals

| Document | Version | Language | Source SHA-256 | Date | Approved by |
|---|---|---|---|---|---|
| requirements.md | <n> | <language> <(translation) \| (original)> | <SHA-256> | <YYYY-MM-DD> | <name> |
