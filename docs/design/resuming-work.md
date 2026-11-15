# Resuming Work

A task can stop at any point: a usage limit, a closed terminal, a crash, a question waiting for the client, or the rework limit. It must always be possible to resume it later without losing work or repeating finished steps.

- **State lives outside the session.** Each task has a state file, `keyturn/internal/state/<task>.md`, recording the current step, completed steps, open questions, and why it stopped ([ADR 0011](../adr/0011-task-state-file.md)). GitHub (issue labels, PR status) reflects the same state when integration is used.
- **Checkpoint at every step boundary.** When a step finishes, its outputs are written to documents and committed to the task branch, and the state file is updated. A stop never loses more than the step in progress.
- **Steps are safe to rerun.** If a stop happens in the middle of a step, resuming reruns that step from its inputs. Steps must not depend on anything that exists only in the previous session's context.
- **One command resumes.** A `resume` skill reads the state file and continues from the right step. With no argument, it lists the tasks that can be resumed.
- **Resume anywhere.** Because state is in the repository, a task can be resumed in a new session, on another machine, or with the other supported AI tool.
- When work stops because of a usage limit, the state file records when the limit resets, so the client knows when it can continue. (Automatic resumption after a reset belongs to the future autonomous mode.)
