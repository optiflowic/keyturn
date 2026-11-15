# Language

There are two different contexts: this repository itself, and the projects that use keyturn.

## This repository

- Everything in the keyturn repository (code, skills, templates, docs, README) is written in English.
- The maintainer reads it in their own language through local translations (see `localize` below). Translations are never committed.

## Projects that use keyturn

- Conversation with the client happens in the client's language.
- **Client-facing documents** are written in the client's language by default.
- **Internal documents** (agent-to-agent) are written in English.
- A project can choose **English-only mode** instead, for example a public OSS project whose published content should all be in English. In this mode, client-facing documents, issues, PRs, and comments are all in English, and the client reads them through local translations.

The language settings are stored per project in keyturn's project configuration, `keyturn/config.json`: the client's language and whether the project uses English-only mode. Every role checks the file with a script before reading it, and stops if it is missing or invalid. Other settings are added by the role that first needs them. See [ADR 0014](../adr/0014-project-configuration-in-json.md).

## Local translations (`localize`)

Used for this repository and for projects in English-only mode.

### Reading: English → client's language

- Translations are generated into a local, git-ignored folder (e.g., `.keyturn/i18n/<lang>/`), mirroring the original paths.
- Each translation records the hash of its source, so it is regenerated when the source changes and stale translations are never shown.
- This works for documents in the repository and for GitHub content (issues, PRs, comments) fetched on demand.
- The client portal shows the client's language by default, with the English original one click away.

### Writing: client's language → English

- When the client writes in their language (a request, an answer to a question, a comment), agents translate it into English before posting.
- For anything that changes what will be built (requirements, answers to questions), the client confirms the translated meaning before it is posted.
- The client confirms by reading the English translated back into their language, from the English alone, so that a mistranslation shows up in their own language. Requirements are confirmed through their approval (see below), so a request is not confirmed twice. Short replies, thanks, and general comments are posted without a confirmation, so the client is not asked more than needed. The client's original stays local, under `.keyturn/i18n/inbound/`, and only the English is committed or posted. See [ADR 0013](../adr/0013-confirming-translations-into-english.md).

### Approving translated content

Mistranslation in requirements is a real risk, because the client approves what they read in their own language, not the English source.

- Requirements and acceptance criteria are numbered (e.g., `R-3`, `AC-5`), and the numbers are identical in the original and the translation, so every item can be matched 1:1.
- The approval records which translation (by source hash) the client read, in a separate approval file (`approvals.md`), so that recording it does not change the approved document. See [ADR 0008](../adr/0008-approval-records-in-a-separate-file.md).
- An approval whose source hash does not match the current document is stale, and the new version needs a new approval.
- So that an unchanged approval stays current in every checkout, client-facing documents are always checked out with LF (`keyturn/client/*.md text eol=lf` in `.gitattributes`), and a hash is recorded only for the committed version. The approved translation is kept, unchanged, next to the current translation, so its links still work. See [ADR 0012](../adr/0012-stable-approval-hashes.md).

### Keeping the cost down

- Translate on demand, when the client opens something, not everything in advance.
- Translate only what the client reads (client-facing documents, PR and issue summaries), not code or internal documents unless asked.
- Use the source hash to skip unchanged files, and retranslate only the changed sections of a changed file.
- Use a small, inexpensive model for translation. Translation is a simple task compared with design or implementation.
- Keep a short glossary per project so terms stay consistent without long context.
- Record translation tokens as a separate role in the cost data.

### Standalone use

Translation is also a standalone skill (`localize`). It works on any repository, including ones that do not use the rest of keyturn, and it only reads the repository, so it is safe to use from the start.
