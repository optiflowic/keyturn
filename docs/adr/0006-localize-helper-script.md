# 0006. A Python helper script for `localize` bookkeeping

- Status: accepted
- Date: 2026-11-08

## Context

The `localize` skill translates repository files into the reader's language, into `.keyturn/i18n/<lang>/` (see "Local translations" in `docs/DESIGN.md`). Besides the translation itself, it has to:

- record the hash of each source file, so stale translations are never shown,
- skip files that did not change, and retranslate only the sections that did,
- keep `.keyturn/` out of Git in any repository, without committing anything.

The AI tool does the translation. The question is who does the bookkeeping, and in what language. It must work with any AI tool, on any repository (including ones that do not use keyturn), and follow the readability rules.

## Options considered

1. **The agent does the bookkeeping by following the skill text**: no code, but hashing, section splitting, and merging are exactly the steps a model gets subtly wrong (a missed section, a wrong hash). Results would vary between runs and models.
2. **A POSIX shell script**: available everywhere Git is, but splitting Markdown into sections outside code fences and merging them by hash is hard to write readably in shell, and `sha256sum` and `shasum` differ between Linux and macOS.
3. **A Python script using only the standard library**: Python 3 is installed on macOS (with the developer tools) and most Linux systems, and has hashing, text handling, and argument parsing built in. No packages to install.

## Decision

The bookkeeping is done by `skills/localize/scripts/localize.py`, a Python 3.9+ script that uses only the standard library (option 3). The agent only translates the text it is given.

## Reasons

- Deterministic steps are done by code, so the cache behaves the same with every tool and model. The model does only what needs a model.
- Python keeps the section splitting and merging short and readable, and is easy to test.
- Python 3.9 is the version the macOS developer tools ship, so the script runs without installing anything on most machines.

## Consequences

- `localize` needs Python 3.9 or later and Git on the reader's machine. The skill says so.
- The translation format is fixed by the script: the first line records the source path and SHA-256, and each section starts with a `localize-section` marker with the hash of its source section.
- The agent never copies hashes. The work file it translates marks sections with short numbers, and the hashes stay in a separate file that only the script reads. (In the first trial, a small model dropped one character of a 64-character hash; the script refused the result, but numbered markers avoid the problem.)
- The script has its own tests (`skills/localize/scripts/test_localize.py`, run from the repository root with `python3 -m unittest discover -s skills/localize/scripts`). Phase 4 can add them to the gate and CI.
- Windows without Python is not supported yet.
