# Decision: Is it acceptable that someone can block a person's sign-in again and again?

- Status: answered
- Related: R-8

## Summary

Someone who knows a person's email address can block that person from signing in, again and again, by typing wrong passwords on purpose. We recommend accepting this small risk. If you do not answer, the rest of the work goes on, but we cannot deliver until you answer.

## Context

R-8 blocks signing in to an account for 15 minutes after 5 wrong passwords, to stop password guessing. A side effect is that anyone who knows a person's email address can trigger the block on purpose, and repeat it when it ends.

People who are already signed in are not affected, and the block lets no one in and shows no tasks. The person only cannot sign in on a new device, or after signing out, until the block ends. We rate this risk as low: it is an annoyance, not a way in.

## Options

1. **Accept the risk (recommended)**: nothing changes. The risk is listed in every delivery report, so you can change your mind later.
2. **Also limit wrong passwords by network address**: the block would apply only to the network the wrong passwords come from, so the owner could still sign in from elsewhere. This changes R-8, needs your approval of the new requirements, and adds about a day of work. People who share one network, such as a home or an office, could still block each other.

## Our recommendation

Accept the risk: only you and a few friends use the app, and the people affected stay signed in on their own devices (R-2, R-8).

## If you do not answer

We keep building everything else, but we cannot deliver until you answer: we never choose for you, not even our recommendation.

## Your answer

- Answer: accept the risk. "Only friends use it; we'll tell you if it ever happens."
- Date: 2026-11-08
