# Decision: Is it acceptable that someone can block a person's sign-in again and again?

- Status: answered
- Related: R-8

## Summary

Someone who knows a person's username can block that person from signing in, again and again, by typing wrong passwords on purpose. We recommend accepting this small risk. If you do not answer, the rest of the work goes on, but we cannot deliver until you answer.

## Context

R-8 blocks signing in to an account for 15 minutes after 5 wrong passwords, to stop password guessing. A side effect is that anyone who knows a person's username can trigger the block on purpose, and repeat it when it ends.

The block lets no one in and shows no tasks. While it lasts, the person cannot sign in. Someone who is not signed in anywhere is locked out at once. Someone who is signed in keeps working until their sign-in runs out, which is 7 days after they signed in (decision card 1), so it can be soon after the blocking starts. Access comes back once the blocking stops. We rate this risk as low: it is an annoyance, not a way in, no data is lost or shown, and the person blocking must repeat the block every 15 minutes. Usernames are public, so anyone can find one to block.

## Options

1. **Accept the risk (recommended)**: nothing changes. The risk is listed in every delivery report, so you can change your mind later.
2. **Block by network address instead**: after 5 wrong passwords, only the network they come from is blocked, so the owner can still sign in from elsewhere. Someone guessing a password could then try from many networks, so a looser limit for the whole account is also needed (for example, 50 wrong passwords in a day). That makes guessing a little easier than now, and blocking the owner harder but still possible. This changes R-8, needs your approval of the new requirements, and adds about a day of work. People who share one network, such as a home or an office, could still block each other.

## Our recommendation

Accept the risk: only you and a few friends use the app, and the people affected stay signed in on their own devices (R-2, R-8).

## If you do not answer

We keep building everything else, but we cannot deliver until you answer: we never choose for you, not even our recommendation.

## Your answer

- Answer: accept the risk. "Only friends use it; we'll tell you if it ever happens."
- Date: 2026-11-08
