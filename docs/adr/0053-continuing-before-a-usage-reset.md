# 0053. The maintainer can let a task stopped for a usage limit go on before the recorded reset; `resume` records the decision and the usage check still decides

- Status: accepted
- Date: 2026-11-23

## Context

When `deliver` stops at a usage limit, the state file records `Stopped because: usage limit` and `Can continue: after <the window's reset>`, and `resume` does not continue before that time ("Not before the reset" in `skills/resume/SKILL.md`; "Resuming Work").

The time is when the window resets, not the only moment the task may go on. The maintainer may decide to go on sooner: they raise the limits for the session (`KEYTURN_SOFT_LIMIT`), or release the stop with `usage.py release` ([ADR 0023](0023-releasing-usage-stops.md)). In the end-to-end rehearsal (#156), the maintainer did the first, `usage.py check` passed, and `resume` still stopped, because the state file's time had not come. The only way on was to edit the state file by hand, and its format had no place for the decision: for a usage limit, `Can continue` takes only `after <time>`, and a History line is one of `started`, `stopped`, `resumed`, `done`, and `closed`. The state file was set to `Can continue: after <the current time>`, which is not when the limit resets, and the commit was discarded.

What constrains the answer:

- A usage stop is lifted only by what a person does outside the agent's tools: the limits the session starts with, or `usage.py release` (ADR 0023). ADR 0023 rejected a confirmation that the agent asks for and records itself as the way to lift one, since the agent could then lift its own stop.
- The state file records only what is true and in the repository, and a History line is never changed (`templates/internal/state.md`).
- `deliver` runs the usage check before every step, with the limits the session has, and stops again when a window is still over its limit.

## Options considered

1. **Keep the rule; the maintainer waits for the reset, or edits the state file by hand.** Nothing to build, but a hand edit has to write a time that is not true, and nothing records why the task went on.
2. **`resume` goes on before the recorded time whenever the usage check passes.** No person needs to say anything, since the check already reads the limits the person set. But a task would also go on when the limits were raised for some other reason, and nothing would record that anyone decided it.
3. **`resume` goes on before the recorded time only when the person who asked says the maintainer decided so, and the usage check passes now; the decision goes on the resume's History line, and `Can continue` is never changed.** The decision is recorded where the task's stops and resumes are, the recorded reset stays true, and what lets the work use the plan is still the check, with the limits the person set.
4. **A new field or History kind for the decision** (for example, `released: usage limit, by the maintainer`). Makes the decision a value a script can read, but adds a state commit before the resume, which records nothing the resume's own line cannot, and no script needs to read it.

## Decision

Option 3. In `resume` step 4, `can continue: after <time>: not yet` stops as before, and says that the maintainer may decide to go on sooner. `resume` goes on before `<time>` only when the person who asked says, in the conversation, that the maintainer decided to go on now, and the adapter's usage check passes now, run as `deliver` runs it (no options, nothing set in front of it). It never edits the state file to make the time pass, and never changes the limits or releases a stop itself. Its resume line in History says ``(before the usage limit resets at <time>, by the maintainer's decision: <what they decided>)``, which the template names.

## Reasons

- The answer in the conversation does not lift a usage stop, so this is not ADR 0023's rejected option 3: the check, with the limits the person started the session with or a release they ran, decides whether any work runs, as it does before every step. The answer only lets `resume` stop waiting for a time that no longer matters, and running the check first keeps `resume` from recording a resume that `deliver` would stop again at once.
- The resume's History line is already the record of who decided a resume and why (as for a task that was `running`), and the stop's line before it keeps the window and its true reset.
- Requiring the decision, not only a passing check, keeps a task stopped until someone chose to go on, as the stop asked.

## Consequences

- `resume` runs the usage check of the adapter for the tool it runs in, for this case only; on a tool whose adapter has none, it cannot go on before the reset.
- The agent cannot tell that the person who asked is the maintainer, as with the confirmation for a `running` task; what it records is what that person said.
- `task_state.py` does not read the decision: a resume line's text after `resumed` is not checked, and the check never depends on the clock.
