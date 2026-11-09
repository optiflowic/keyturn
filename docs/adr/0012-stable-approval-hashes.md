# 0012. Approved documents are checked out with LF, and the approved translation is kept next to the current one

- Status: proposed
- Date: 2026-11-09

## Context

[ADR 0008](0008-approval-records-in-a-separate-file.md) records an approval of `keyturn/client/requirements.md` by the SHA-256 of the file's bytes, which is also the `sha256` on the first line of a fresh `localize` translation. The review of #46 left two problems for the skill that records approvals (#47).

1. **Line endings change the hash.** Git can write the same committed version with different line endings in different checkouts (`core.autocrlf`, or `text` and `eol` attributes). `localize` hashes the text exactly as stored, line endings included, so a checkout with CRLF gives another hash, and an approval that did not change looks stale. The tests in `skills/localize/scripts/test_localize.py` show this: the same text with LF and with CRLF gives two different source hashes, and a clone with `core.autocrlf=true` writes CRLF and changes the hash.
2. **Links in the kept copy of the approved translation.** The PM keeps the translation the client approved, unchanged and outside Git, so it can be shown again. Its relative link to the translated `approvals.md` (the current status) only works if the copy sits in the same folder as the current translation.

Whatever is chosen, the source hash in an approval must still match the `sha256` on the first line of a fresh translation, and the check must stay one comparison a person can run.

## Options considered

For the line endings:

1. **Require LF for client-facing documents with `.gitattributes`**: each project has `keyturn/client/*.md text eol=lf`, so every checkout writes LF whatever `core.autocrlf` says. The hash stays the SHA-256 of the file's bytes, so ADR 0008, `localize`, and the `shasum` check stay as they are. It depends on a line in each project, which the skills add and check.
2. **Normalize line endings before hashing**: `localize` would turn CRLF into LF before hashing. Works without any project setting, but the hash is no longer the hash of the file's bytes, so `shasum` stops being a check, ADR 0008 has to be superseded, and `localize`, a general tool, gets a rule that only keyturn needs.
3. **Hash the committed blob** (`git show HEAD:<path>`): the same in every checkout, but it hashes what is committed, not what the client was sent, and `localize` hashes the file it reads, so the two hashes can differ.

For the kept copy:

1. **Next to the current translation**, as `.keyturn/i18n/<lang>/keyturn/client/requirements.v<n>.approved.md`: every relative link in it, including the one to `approvals.md`, opens the same file as in the current translation. The file name changes, but its bytes and hash do not.
2. **In a separate folder** (for example, `.keyturn/approved/`): keeps approved copies apart, but every relative link breaks, and the copy would have to be changed to fix them, which changes its hash.

## Decision

- Every project that uses keyturn has `keyturn/client/*.md text eol=lf` in its `.gitattributes` (line endings, option 1). The PM adds the line before it sends the first version for approval, and checks it each time.
- When the PM adds the line to a project that already tracks client documents, it also runs `git add --renormalize keyturn/client/` and commits the result with the line. The attribute does not change blobs that are already committed with CRLF; renormalizing does, so no later normalization can change the bytes of an approved document.
- Before recording a hash, the PM checks that the file sent is the committed version and has LF line endings: its SHA-256 equals the SHA-256 of `git show HEAD:keyturn/client/requirements.md`, and it contains no carriage return (CR). If not, it renormalizes and commits first, or stops; it never records the hash of a file that differs from the commit or contains CR.
- The approved translation is kept next to the current translation, as `.keyturn/i18n/<lang>/keyturn/client/requirements.v<n>.approved.md`, unchanged (kept copy, option 1).

## Reasons

- The hash stays the hash of the file's bytes, so ADR 0008 holds, `localize` stays general, and `shasum -a 256` is still the whole check.
- `eol=lf` overrides `core.autocrlf`, so every checkout on every platform writes the bytes that were committed. The test with `core.autocrlf=true` shows the hash stays the same with the attribute and changes without it.
- Comparing the file with the committed blob catches what the attribute cannot: an editor that saved CRLF, or an edit that was not committed.
- Keeping the copy in the same folder keeps its links working without changing a byte of it.

## Consequences

- `templates/client/approvals.md` tells the PM to check the `.gitattributes` line and the committed version before recording a hash, and where to keep the approved translation.
- `docs/DESIGN.md` "Approving translated content" states the line-ending rule.
- This repository has the same rule for the worked examples' client documents, so the hash in `evals/requests/task-manager/example/keyturn/client/approvals.md` checks out the same everywhere.
- The `spec` skill (#53) adds the `.gitattributes` line, runs both checks, and keeps the approved translation. A helper script for the checks, if one is written, lives with that skill and has tests.
- `localize status` does not know about `*.approved.md` files: they are not translations it manages, and they are never retranslated.
