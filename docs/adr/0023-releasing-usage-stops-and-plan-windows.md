# 0023. A person releases a usage stop until the window resets; the windows a plan has are a setting

- Status: proposed
- Date: 2026-11-15

## Context

The usage limits ("Subscription usage limits" in [`docs/design/guardrails.md`](../design/guardrails.md#subscription-usage-limits)) stop new steps at the soft limit and every tool call at the hard limit (#91). Two cases were left open (#106):

- A person may decide that a task should go on although a window is past a limit, for example because the window resets soon or the remaining work is small. Today nothing lets them, short of raising the limits for every later window too.
- Some plans have no 5-hour window (verified Ultra accounts, and usage-based Enterprise has no per-seat limits). Claude Code then sends only the 7-day window, and `check` stops every step for good, because a missing window counts as unknown. The status line input does not say which plan it is, and a window is also missing before the session's first API response and just after a reset, so its absence alone cannot tell "this plan has none" from "not sent yet".

The limits exist so that an agent does not use up the plan on its own, so whatever lifts them must be the person's act, not the agent's. Missing data must keep failing safe.

## Options considered

1. **A release command that a person runs, lasting until the window's reset; the hook denies an agent that tries it. The windows a plan has are an environment variable the person sets.** The release is narrow (one window, until its reset) and ends by itself; the next window stops again. The setting keeps the rule that a value is never assumed from its absence. The hook can only catch the plain ways to try a release (running the command, writing its file); an agent determined to get around it could, so it is a guardrail, not a sandbox.
2. **Raise the limits for the session with `KEYTURN_SOFT_LIMIT` / `KEYTURN_HARD_LIMIT`.** Already possible, but it lasts for every later window, so it is easy to forget, and it does not help a plan without a 5-hour window.
3. **Treat a window that has not been sent for a while as one the plan does not have.** No setup, but a stopped status line, a headless run, or a change in what Claude Code sends would turn the stop off without anyone saying so.
4. **A confirmation the agent asks for, answered in the conversation.** The person stays in the loop, but the agent records the answer itself, so the agent can release its own stop.

## Decision

Option 1. `usage.py release`, run by a person in a terminal of their own, lifts the stop of each window that is at or above the soft limit now, until that window's reset time: the soft stop, and the hard stop too when the window is at or above the hard limit. The release is kept next to the usage file and holds only for the window it was made for. The PreToolUse hook denies a tool call that runs the release command or touches the release file. `KEYTURN_PLAN_WINDOWS` names the windows the plan has (default: both); a window it leaves out never stops `check`, and a window it names still stops `check` until its value arrives. `spend_limit` is not a subscription window and is not handled.

## Reasons

- A release that ends at the window's reset cannot be forgotten into later windows, unlike raising the limits.
- A stop the agent is held to is lifted by something the person does outside the agent's tools, and the hook denies the plain ways the agent could do it through a tool. It does not stop every way (for example, a script the agent writes first, or a made-up recording written to the usage file); those remain as before this decision.
- A setting is something a person says; the absence of a value is not, so failing safe on missing data stays the rule.

## Consequences

- `usage.py` gains `release` and reads `KEYTURN_PLAN_WINDOWS`; the hook reads its input to find release attempts. Tests cover both.
- An agent's command that only mentions the release (for example, a `grep` for it) is denied too.
- The release file is per user, like the usage file, so a release covers every session of that account until the reset.
- The future autonomous mode (resuming on its own after a reset) is not changed by this; a release is never made automatically.
