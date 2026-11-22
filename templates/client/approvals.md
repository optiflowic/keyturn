<!--
Template: approval record (client-facing). Kept by the PM in keyturn/client/approvals.md. See ADR 0008 in keyturn's docs/adr/.

- Commit requirements.md before you send it, so the version sent stays in Git history even after a new version starts.
- Check two things before you record a hash (ADR 0012 in keyturn's docs/adr/), and stop if either fails:
  - the project's .gitattributes has `keyturn/client/*.md text eol=lf`, so every checkout writes the same bytes. If the line is missing, add it,
    run `git add --renormalize keyturn/client/` so documents already committed with CRLF are stored with LF, and commit both;
  - the file you send is the committed version with LF line endings: its SHA-256 equals the SHA-256 of `git show HEAD:keyturn/client/requirements.md`,
    and it contains no carriage return (CR).
- Add a row when you send a version for approval, newest last. Fill in "Source SHA-256" and "Translation SHA-256" at that moment, from the files you send,
  never later: requirements.md or its translation may change before the client answers.
  - "Source SHA-256": the SHA-256 of requirements.md as sent. Compute it with `shasum -a 256 keyturn/client/requirements.md` or `sha256sum keyturn/client/requirements.md`.
    When you send a translation, first check that it is fresh (localize status); its first line then shows the same value as sha256.
  - "Translation SHA-256": the SHA-256 of the translation file the client reads, computed the same way. Write "none" when the client reads requirements.md itself.
    Keep that translation file unchanged, outside Git, next to the current translation, as .keyturn/i18n/<lang>/keyturn/client/requirements.v<n>.approved.md,
    until the version is replaced, so the approved text can be shown again and its links (including the one to this file) still open the current translations;
    its SHA-256 proves it is the text that was approved. Translations are never committed.
    When you show the approved requirements to the client again, show that kept copy, after checking that its SHA-256 matches the row.
    A new translation of the same source (for example, after a full retranslation) is not the approved text, even though the source hash matches:
    show it only as a new translation, and get a new approval if it is to replace the approved one.
- "Language" is the language the client reads, with "(translation)" or "(original)".
- When the client answers, fill in "Answer" (approved, or not approved with what they want changed) and "Date answered". Never change anything else in a row, and never delete a row.
- An approval is current only if its "Source SHA-256" equals the SHA-256 of the current requirements.md. Check this whenever requirements.md changes.
  When it no longer matches, update "Current status", and tell the client that the new version needs their approval.
- When the client reads translations, update the translation of this file (localize) every time you change it, and before telling the client,
  so that the link from the translated requirements opens the current status.
- Write for a client who does not read code. Write the headings and the text in the client's language, unless the project uses English-only mode.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Approvals

This file records which version of the requirements you approved, whether you accepted each delivery, and exactly which text you read.

## Current status

<!--
One or two lines, updated by the PM whenever an answer arrives or requirements.md changes. For example:
"Version 2 is approved and current.", "Version 1 was approved, but the requirements changed on 2026-11-20. Version 2 is waiting for your approval.",
or "You did not approve version 1. We are changing R-3 as you asked, and will send you version 2 for approval."
-->

> [!IMPORTANT]
> <the version that is approved and current; the version waiting for your approval and what changed; or, after "not approved", what we are changing and what comes next>

## How to tell whether an approval is still current

<!-- Keep this section short. The client should not need to understand hashes to read it. -->

Each row identifies the exact text you were sent by a fingerprint. If the requirements change after your approval, the fingerprint of the current file no longer matches the row: we update "Current status" above and ask you to approve the new version.

## Approvals

| Document | Version | Language | Source SHA-256 | Translation SHA-256 | Date sent | Answer | Date answered |
|---|---|---|---|---|---|---|---|
| requirements.md | <n> | <language> <(translation) \| (original)> | <SHA-256> | <SHA-256 \| none> | <YYYY-MM-DD> | <waiting \| approved \| not approved: what to change> | <YYYY-MM-DD> |

## Acceptance

<!--
One row each time a delivery's acceptance guide and delivery report are sent for the client's acceptance, newest last (ADR 0046 in keyturn's docs/adr/).
The PM fills in everything but the answer from `approval.py accept-send <task>` (with --lang <language> when the client reads translations), at that moment, never later,
and commits this file alone. Keep these cells exactly as the template has them, whatever the document language, since CI reads them:
- the first cell is always `acceptance-guide.md, delivery-report.md`, and "Task" is the task's name;
- "Documents commit" is the full hash `accept-send` prints;
- "Answer" is one of `waiting`, `accepted`, or `not accepted: <what to change, in the client's words>`, in English.
When the client answers, fill in "Answer" and "Date answered" in a commit of this file alone. Never change anything else in a row, and never delete a row.
An acceptance is current only while the two documents and their commit are the ones in the row (`approval.py accept-status <task>`). No answer is not acceptance.
-->

| Documents | Task | Documents commit | Language | Acceptance guide SHA-256 | Delivery report SHA-256 | Acceptance guide translation SHA-256 | Delivery report translation SHA-256 | Date sent | Answer | Date answered |
|---|---|---|---|---|---|---|---|---|---|---|
| acceptance-guide.md, delivery-report.md | <task> | <full commit hash> | <language> <(translation) \| (original)> | <SHA-256> | <SHA-256> | <SHA-256 \| none> | <SHA-256 \| none> | <YYYY-MM-DD> | <waiting \| accepted \| not accepted: what to change> | <YYYY-MM-DD> |
