<!--
Template: approval record (client-facing). Kept by the PM in keyturn/client/approvals.md. See ADR 0008 in keyturn's docs/adr/.

- Add a row when you send a version for approval, newest last. Fill in "Source SHA-256" and "Translation SHA-256" at that moment, from the files you send,
  never later: requirements.md or its translation may change before the client answers.
  - "Source SHA-256": the SHA-256 of requirements.md as sent. Compute it with `shasum -a 256 keyturn/client/requirements.md` or `sha256sum keyturn/client/requirements.md`.
    When you send a translation, first check that it is fresh (localize status); its first line then shows the same value as sha256.
  - "Translation SHA-256": the SHA-256 of the translation file the client reads, computed the same way. Write "none" when the client reads requirements.md itself.
    Keep that translation file unchanged, outside Git (for example, a copy under .keyturn/), until the version is replaced, so the approved text can be shown again;
    its SHA-256 proves it is the text that was approved. Translations are never committed.
- "Language" is the language the client reads, with "(translation)" or "(original)".
- When the client answers, fill in "Answer" (approved, or not approved with what they want changed) and "Date answered". Never change anything else in a row, and never delete a row.
- An approval is current only if its "Source SHA-256" equals the SHA-256 of the current requirements.md. Check this whenever requirements.md changes.
  When it no longer matches, update "Current status", and tell the client that the new version needs their approval.
- Write for a client who does not read code. Write the headings and the text in the client's language, unless the project uses English-only mode.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Approvals

This file records which version of the requirements you approved, and exactly which text you read.

## Current status

<!--
One or two lines, updated by the PM whenever an answer arrives or requirements.md changes. For example:
"Version 2 is approved and current." or "Version 1 was approved, but the requirements changed on 2026-11-20. Version 2 is waiting for your approval."
-->

> [!IMPORTANT]
> <the version that is approved and current, or the version waiting for your approval and what changed>

## How to tell whether an approval is still current

<!-- Keep this section short. The client should not need to understand hashes to read it. -->

Each row identifies the exact text you were sent by a fingerprint. If the requirements change after your approval, the fingerprint of the current file no longer matches the row: we update "Current status" above and ask you to approve the new version.

## Approvals

| Document | Version | Language | Source SHA-256 | Translation SHA-256 | Date sent | Answer | Date answered |
|---|---|---|---|---|---|---|---|
| requirements.md | <n> | <language> <(translation) \| (original)> | <SHA-256> | <SHA-256 \| none> | <YYYY-MM-DD> | <waiting \| approved \| not approved: what to change> | <YYYY-MM-DD> |
