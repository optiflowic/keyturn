# 0011. The task state file is a Markdown file with fixed fields

- Status: accepted
- Date: 2026-11-08

## Context

"Resuming Work" in `docs/DESIGN.md` requires a state file per task in `keyturn/internal/`. It records the current step, the completed steps, open questions, why the task stopped, and, for a usage limit, when the limit resets. `deliver` writes it at every step boundary, and `resume` reads it to continue in a new session, on another machine, or with the other supported AI tool.

The question is what the file looks like and where it lives. What constrains the answer:

- Agents read and write it from a skill's instructions, and may use a small helper script to check it. Both must be able to find each field without guessing.
- People read it too: the maintainer while developing keyturn, and the client when they want to know why a task stopped and when it can go on.
- It is committed to the task branch at each checkpoint, so its changes should be easy to read in a diff.
- It must work the same with Claude Code and Codex, so it cannot depend on one tool's features.

## Options considered

1. **A Markdown file with fixed fields**: `- Field: value` lines at the top, a table of steps, and short sections for open questions and a history of stops. The same shape as the other templates (for example, the `Status` line of a threat), readable by a person and by a script that matches the field names. A script must parse lines instead of loading a data format, so the template has to fix the field names and values.
2. **A JSON or YAML file**: easy and exact for scripts, but harder for a person to read, and YAML needs a parser that is not in Python's standard library. The other documents are all Markdown.
3. **Markdown with YAML front matter**: the fields in front matter, the history in the body. Exact fields, but two formats in one file, and front matter still needs a YAML parser.

## Decision

Option 1. Each task has one Markdown file at `keyturn/internal/state/<task>.md`, started from `templates/internal/state.md`. `<task>` is a short name in lowercase with hyphens, such as `delivery-1`, and never changes.

- The fields at the top, the steps table, and their allowed values are fixed by the template. A skill writes only those values.
- Times are in UTC, in the form `YYYY-MM-DDTHH:MMZ`.
- The file is updated and committed at every step boundary, and when the task stops, on the task's branch, `task/<task>`.
- `resume` with no argument finds the tasks it can continue on every task branch, not only in the current checkout: for each local or remote branch named `task/<task>`, it reads `keyturn/internal/state/<task>.md` from that branch (for example, with `git show task/<task>:keyturn/internal/state/<task>.md`), and lists the tasks whose status is not `done`.

## Reasons

- It is readable as it is, in a diff and on GitHub, and keeps the shape of the other keyturn documents.
- Fixed field names and values make it as easy to check as a data file, with Python's standard library only (ADR 0006 keeps helper scripts that way).
- One file per task, at a path built from the task's name, on a branch named after the task, lets `resume` find every task from the branch list alone, without a shared index that every task would have to update.

## Consequences

- `templates/internal/state.md` defines the fields, and the worked example has a filled-in state file.
- `deliver` (#60) writes the file and `resume` (#61) reads it. If a helper script checks it, the script and its tests live with the skill that owns it.
- A new field means a template change, and the worked example is updated with it.
- When GitHub integration arrives (phase 7), issue labels and PR status mirror this file; the file stays the source of truth.
