# 0021. The design is split into one file per section; `docs/DESIGN.md` stays as an index that keeps every heading

- Status: accepted
- Date: 2026-11-15

## Context

`docs/DESIGN.md` had grown to about 600 lines (46 KB), and `AGENTS.md` told agents to read all of it before doing anything. Most work touches only a few sections, so reading the whole file in every session costs usage for no benefit (#92).

Splitting the file moves its content, but many files point to it: accepted ADRs name its sections ("Guardrails" in `docs/DESIGN.md`) and the checklist links to its anchors (`DESIGN.md#guardrails`). Accepted ADRs are never edited ([ADR rules](README.md)), so their references must keep leading to the right content as they are.

## Options considered

1. **One file per top-level section in `docs/design/`, and `docs/DESIGN.md` as an index that keeps every current heading, each followed by a link to where its content now lives.** An agent reads the index and only the files it needs. Every old reference, by section name or by anchor, still resolves on the index page and is one link away from the content. The index repeats the headings, so a heading added to a section file must be added to the index too.
2. **One file per top-level section, and `docs/DESIGN.md` as a short list of the files.** A shorter index, but the headings below the top level disappear from `docs/DESIGN.md`, so an anchor or a section name such as "Subscription usage limits" in an accepted ADR no longer leads anywhere on that page.
3. **Keep one file and tell agents to read only some sections.** No links break, but an agent cannot read part of a file without first finding where the sections are, and the file keeps growing.

## Decision

Option 1. The design lives in `docs/design/`, one file per top-level section of the former `docs/DESIGN.md`, with its content unchanged. `docs/DESIGN.md` is the index: it keeps every heading of the former file, at the same level and in the same order, so that every former anchor is the same; under each top-level heading, one line says which file holds it and what it covers, and under each lower heading, a link points to that heading in its file.

## Reasons

- Agents read only what their work relates to, plus Phases, which is what makes the split worth doing.
- Keeping the headings at the same level and in the same order keeps every former anchor, including the numbered ones GitHub gives repeated headings (`#flow-1`), so links from accepted ADRs, issues, and pull requests keep working without editing them.
- Only the references between sections changed: "See Guardrails" or "see below" now link to the file that holds the section, because the reader of one file no longer has the others below it.

## Consequences

- `AGENTS.md` "Start here" tells agents to read the index, then the section files their work relates to, and always Phases. "Where things live" lists `docs/design/`.
- A change to the design edits the section file. A new, renamed, or removed heading also changes the index, so that the two stay in line.
- New references in skills, templates, and documents point to the section file (for example, `docs/design/guardrails.md`) rather than to `docs/DESIGN.md`.
