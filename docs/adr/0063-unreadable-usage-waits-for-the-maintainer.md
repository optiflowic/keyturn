# 0063. A usage check that cannot read the usage stops the task waiting for the maintainer

- Status: accepted
- Date: 2026-11-24

## Context

`deliver` runs the adapter's usage check before every step ("Subscription usage limits" in [`docs/design/guardrails.md`](../design/guardrails.md#subscription-usage-limits)). In Claude Code, `usage.py check` prints a `stop:` line for each window over its limit, with when it resets, and also for each value it cannot read: nothing recorded, a window missing, a recording older than 15 minutes, a window past its reset with no newer value, a setup error, or an unexpected error (`adapters/claude/README.md`).

Until now, `deliver` recorded a stop for a value it could not read as `Stopped because: error` and `Can continue: now`. `resume` goes on at once on `now`, with no one deciding, and `deliver` runs the check again before the step. No step starts without a passing check, so the guardrail held. But several causes do not go away by themselves: the status line is not set up, the session is headless, the plan has no 5-hour window and `KEYTURN_PLAN_WINDOWS` is not set ([ADR 0024](0024-windows-a-plan-has-are-a-setting.md)), or a setting is wrong. Then every resume hit the same stop and committed another one on the task branch, as a usage check the tool refused to run did before #162. The agent cannot tell these causes from a value that has not arrived yet.

## Options considered

1. **Keep `error` and `now`.** A cause that goes away by itself needs no one, but a lasting one adds a stop on every resume, and nothing tells the maintainer that a person has to change something.
2. **Wait for the maintainer on any `stop:` line that is not a window over its limit**, also when other lines are windows over their limits, with the lines in `Can continue: when the maintainer decides: ...`. A person sees why, fixes the cause or decides that it was passing, and resumes; `deliver` then runs the check again. A cause that would have gone away by itself now needs a person too.
3. **Tell lasting causes from passing ones by the text of the line**, and wait for the maintainer only on the lasting ones. Saves a person a step, but ties `deliver` to the wording of one adapter's script, and a stale recording can be either.

## Decision

Option 2. In `deliver` step 2.1, a check whose `stop:` lines are all windows over their limits stops as before (`usage limit`, `after <time>`). Any other `stop:` line stops the task with `Stopped because: waiting for the maintainer` and `Can continue: when the maintainer decides: <the stop lines, in one line>`, and "Summary" says that the usage could not be read, why, and what a person may need to change. `resume` already stops on such a task and goes on only once the maintainer has decided.

## Reasons

- The same reason as #162: a stop that comes back on every resume until a person acts should say so, and wait for that person.
- It needs no change to `usage.py`, to `task_state.py` (which already accepts this pair), or to `resume`, and no knowledge of one adapter's wording.
- A mix waits for the maintainer because the unreadable value might be the one that matters; the reset time of the other windows is still in the stop lines.

## Consequences

- A value that would have arrived by itself (for example, a recording that went stale while a session was idle) now needs the maintainer to resume the task; the cost is one decision.
- `deliver` no longer writes `Stopped because: error` for the usage check. The value stays in the state file's template.
