# 0024. The windows a plan has are a setting the person makes, never inferred from a missing value

- Status: proposed
- Date: 2026-11-15

## Context

Some plans have no 5-hour usage window (verified Ultra accounts; usage-based Enterprise has no per-seat limits). Claude Code then sends only the 7-day window, and `check` ("Subscription usage limits" in [`docs/design/guardrails.md`](../design/guardrails.md#subscription-usage-limits)) stops every step for good, because a missing window counts as unknown (#106). The status line input does not say which plan it is, and a window is also missing before the session's first API response and just after a reset, so its absence alone cannot tell "this plan has none" from "not sent yet". Missing data must keep failing safe.

## Options considered

1. **An environment variable, `KEYTURN_PLAN_WINDOWS`, names the windows the plan has (default: both).** Something a person says, so failing safe on missing data stays the rule. A person can set it wrongly, so a value that is sent still counts.
2. **Treat a window that has not been sent for a while as one the plan does not have.** No setup, but a stopped status line, a headless run, or a change in what Claude Code sends would turn the stop off without anyone saying so.
3. **A field in the project's `keyturn/config.json`.** The windows belong to the account, not to a project, and the usage file is already per user.

## Decision

Option 1. A missing value of a window that `KEYTURN_PLAN_WINDOWS` leaves out does not stop `check`; a recorded value of it still counts, and a window it names stops `check` until its value arrives. An empty value, or one that names anything other than `five_hour` and `seven_day`, is a setup error and stops `check`. `spend_limit` is not a subscription window and is not handled.

## Reasons

- A setting is something a person says; the absence of a value is not.
- Counting a value that is sent keeps a wrong setting from turning a real stop off.

## Consequences

- `usage.py check` and `release` read `KEYTURN_PLAN_WINDOWS`; the hook does not need it, since it stops only on known values. Tests cover it.
- The agent runs `check`, so an agent could set the variable in front of it, as it already could pass lower limits; this is a guardrail, not a sandbox.
