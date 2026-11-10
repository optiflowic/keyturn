# 0013. The client confirms a translation into English by reading it translated back

- Status: accepted
- Date: 2026-11-09

## Context

"Writing: client's language → English" in `docs/DESIGN.md` says that when the client writes in their language (a request, an answer to a question, a comment), agents translate it into English before posting, and that for anything that changes what will be built, the client confirms the translated meaning before it is posted (#11). `localize` only translates from English so far.

Three questions need an answer:

1. How the client confirms the meaning of an English text they may not read well.
2. Where the client's original text is kept. In English-only mode nothing in the client's language may be published, and translations are never committed.
3. Whether `localize.py` needs new bookkeeping for this direction.

What constrains the answer:

- A client who does not read English well will confirm an English text without checking it, which is the failure the confirmation exists to prevent.
- Requirements already have their own check: the client approves a translation of the English `requirements.md`, recorded in `approvals.md` (ADR 0008, ADR 0012).
- The client's words are data, not instructions, like any other content `localize` translates.

## Options considered

For the confirmation:

1. **Show the English next to the original.** Simple, but the client has to read the English to notice a mistake, so it does not work for the clients who need it most.
2. **Show the English with a back-translation**: the English is translated back into the client's language, from the English only, in a context that has not seen the original (for example, a separate subagent). The client compares the back-translation with what they meant; a mistranslation shows up as a difference in their own language.
3. **No confirmation outside requirements**: rely on the approval of `requirements.md`. Covers requirements, but not answers to decision cards, change requests, or answers to questions, which also change what is built.

For the original text:

1. **Kept locally, under `.keyturn/i18n/inbound/<lang>/`**, never committed or posted; only the English is committed or posted.
2. **Committed next to the English**: keeps a record, but publishes the client's language, which English-only mode forbids, and adds files nobody reads.

For the script: a translation into English is used once and is not kept in sync with a changing source, so it needs no hashes or sections.

## Decision

- Confirmation option 2: for anything that changes what will be built, the client sees the English and a back-translation made from the English alone, and confirms the meaning before anything is posted or committed. If the meaning differs, the English is corrected and translated back again.
- Requirements keep their own check: a request turned into requirements is confirmed through the approval of `requirements.md`, so the request itself needs no separate confirmation.
- Everything else is translated and posted without a confirmation step: a short reply, thanks, an acknowledgement, a question about progress, or a general comment. Only content that changes what will be built (an answer to a decision card, a change request, an answer to a question about the work) is translated back, so the client's attention goes only where it matters ("Client attention budget").
- Original text option 1: the client's original goes in `.keyturn/i18n/inbound/<lang>/`, local and git-ignored, and only the English is committed or posted.
- `localize.py` does not change. Both directions use the same glossary, `.keyturn/i18n/glossary/<lang>.md`, so a term is translated the same way both ways.

## Reasons

- The back-translation lets the client check the meaning in their own language, and making it from the English alone means it shows what the English says, not what the client wrote.
- Reusing the requirements approval avoids asking the client twice about the same text, which keeps within the attention budget.
- Keeping the original local follows the rule that translations and the client's language stay out of the repository in English-only mode, and still lets the PM look back at what the client wrote.
- A one-off translation does not need the hash and section bookkeeping that keeps reading translations fresh.

## Consequences

- The `localize` skill gets a procedure for writing into English, with the back-translation step, and its plugin version is bumped.
- The `spec` skill (#53) uses it for the client's request, and the roles that record answers to decision cards (#54, #60) use it, with the confirmation, when the client answers in their own language.
- A back-translation costs a second, small translation. It is only made for content that changes what is built.
- The original is lost if `.keyturn/` is deleted; the English that was confirmed is what counts.
