# 0007. GitHub content is translated as local source files

- Status: accepted
- Date: 2026-11-08

## Context

`localize` must also translate GitHub content (issues, pull requests, and their comments) fetched on demand, into `.keyturn/i18n/<lang>/` at a predictable path (see "Local translations" in `docs/DESIGN.md`). Unchanged content must not be translated again, and a new comment must be translated without translating the old ones again. Nothing may be posted to GitHub or committed.

ADR 0006 already gives `localize` a cache for repository files: a translation records the hash of its source and of each section (split at Markdown headings), and only changed sections are translated again. The question is how GitHub content fits into that.

## Options considered

1. **A separate cache for GitHub content**, keyed by comment ID and edit time: precise, but a second format and a second set of commands to keep correct, for the same job.
2. **Save the content as a local Markdown file, then translate that file like any other**: the script fetches the issue or pull request with `gh`, writes it as one Markdown file with one `##` section per comment, and the existing `status`, `prepare`, and `apply` steps do the rest. A new comment is a new section; an edited comment is a changed section.

## Decision

Option 2. `localize.py fetch <number>` writes the issue or pull request to `.keyturn/github/<owner>/<repo>/issues/<number>.md` (or `pulls/<number>.md`). Its translation mirrors that path, like any other file: `.keyturn/i18n/<lang>/.keyturn/github/<owner>/<repo>/issues/<number>.md`.

## Reasons

- One cache and one set of commands for every source. The rules that keep the cache correct (hashes, damaged markers, line endings) apply to GitHub content without new code.
- The translation path cannot clash with a repository file, because files under `.keyturn/` are never translated from the repository itself. A shorter path such as `.keyturn/i18n/<lang>/github/...` could clash with a `github/` folder in the repository.
- The fetched file is plain Markdown, so the reader can also open the English original next to the translation.

## Consequences

- The fetched file must be stable: fetching unchanged content must write the same bytes. The script sorts comments by time and ID, leaves out values that change on their own (such as edit times), and ends every section the same way, so a new comment does not change the one before it.
- The script cleans each body before saving it: hidden HTML comments are dropped (readers do not see them, and bots keep long hidden data there), headings move down below the `##` comment headings, a code fence left open is closed so it cannot swallow the next comment, and a line that looks like a `localize` marker is indented so it cannot pose as one.
- A change to the issue's title or state only changes the short first section.
- `localize` needs the GitHub CLI (`gh`), signed in, for GitHub content. Repository files still need only Python and Git.
- The script only reads from GitHub (`gh api` without a method or fields, and `gh repo view`). Writing to GitHub (the writing direction) is a separate decision.
