# Threat model: task manager

Based on requirements version 2 and the design document: [design.md](design.md).

## Summary

The valuable things are each user's tasks and their passwords. Attacks come from other signed-in users (reaching someone else's tasks), from people who are not signed in (guessing passwords), and from harmful input in task titles.
The most serious threat is one user reaching another user's tasks (T-1).

## Assets

| Asset | Why it matters |
|---|---|
| Tasks | Private to each user (R-7); reading or changing them breaks the main promise of the app |
| Passwords | People often reuse passwords; a leak harms them outside this app too |
| Sessions | A stolen session lets someone act as that user |

## Entry points

| Entry point | Who can reach it | Input it accepts |
|---|---|---|
| `POST /api/signup`, `POST /api/signin` | anyone | username, password |
| `/api/tasks` and `/api/tasks/{id}` | signed-in users | task ID in the path; title, due date, done |
| `POST /api/signout` | signed-in users | none |
| Web pages | anyone | none (static files) |

## Threats

Entry points that can reveal whether an account exists were each considered, and are public by requirement: usernames are public on purpose (R-1 and the "Misuse" section of the requirements), and the app keeps no email address, so no private identifier can be tested.

- Sign-up (`POST /api/signup`) says that a username is taken.
- Sign-in (`POST /api/signin`) and its errors.
- The block after 5 wrong passwords (R-8) shows that a username is an account.

### T-1: A user reaches another user's task by changing the ID

- Entry point: `/api/tasks/{id}`
- Asset: tasks
- Misuse: yes, from R-7
- Severity: high
- Status: verified: [security review F-1 and the threat model check](security-review.md)
- Remaining risk: none

**Threat**: A signed-in user changes the task ID in a link or request to read, change, or delete a task that belongs to someone else.

**Mitigation**: Every task query includes the session's user ID (`WHERE user_id = ?`), in the task service, and another user's task is reported as not found (R-7).

**How it is verified**: AC-4; QA API tests that try every task route with another user's task ID; security review of every query in `api/internal/task/`.

### T-2: Someone who is not signed in uses the task API

- Entry point: `/api/tasks` and `/api/tasks/{id}`
- Asset: tasks
- Misuse: yes, from R-2
- Severity: high
- Status: verified: [security review](security-review.md)
- Remaining risk: none

**Threat**: A request without a valid session reads or changes tasks.

**Mitigation**: The session middleware rejects every `/api/` request without a valid, unexpired session, except sign-up and sign-in (R-2).

**How it is verified**: AC-1 (the task list shows the sign-in page after signing out); QA API tests without a cookie and with an expired session.

### T-3: Password guessing

- Entry point: `POST /api/signin`
- Asset: passwords
- Misuse: yes, from R-8
- Severity: high
- Status: verified: [security review F-2 and the threat model check](security-review.md)
- Remaining risk: none

**Threat**: Someone tries many passwords for one account until one works.

**Mitigation**: Passwords of at least 12 characters (R-1); after 5 wrong passwords in a row, the account is blocked for 15 minutes (R-8).

**How it is verified**: AC-2 and AC-7; security review of the counter (it must also count attempts made at the same moment).

### T-4: Code in a task title runs in the browser

- Entry point: `/api/tasks`
- Asset: sessions
- Misuse: yes, from R-3
- Severity: medium
- Status: verified: [security review](security-review.md)
- Remaining risk: none

**Threat**: A title containing HTML or script runs in the page when it is shown.

**Mitigation**: Titles are rendered as React text, never as HTML (R-3); the session cookie is `HttpOnly`, so injected code could not read it and take the session elsewhere (it could still send requests from the open page, so rendering titles as text is the main mitigation) ([ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)). Only the owner sees their titles (R-7).

**How it is verified**: AC-3; the gate's frontend lint rule that forbids `dangerouslySetInnerHTML`.

### T-5: Stolen password hashes

- Entry point: a copy of the database file
- Asset: passwords
- Misuse: no
- Severity: medium
- Status: verified: [security review](security-review.md)
- Remaining risk: none

**Threat**: Someone who copies the database file guesses the passwords offline, at high speed.

**Mitigation**: Passwords are stored only as Argon2id hashes with a random salt; session tokens are stored only as SHA-256 hashes ([ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)).

**How it is verified**: Security review of the account service and the schema.

### T-6: Locking another person out on purpose

- Entry point: `POST /api/signin`
- Asset: the owner's access to their tasks
- Misuse: yes, from R-8
- Severity: low
- Status: verified: [security review threat model check](security-review.md)
- Remaining risk: accepted on 2026-11-08: [decision card 2](../client/decision-card-2.md)

**Threat**: Someone who knows another person's username types 5 wrong passwords, again and again, so the owner cannot sign in.

**Mitigation**: The block stops only new sign-ins, for 15 minutes; sessions already signed in keep working, so the owner stays signed in on their own devices (7-day sessions, ADR 0003). The block is shown with the time it ends (R-8).

**What is left**: Blocking again and again is not prevented, so the owner cannot sign in on a new device or after signing out while someone keeps doing it. An owner with no active session is locked out at once. Sessions end 7 days after sign-in, not 7 days after the blocking starts (ADR 0003), so an existing session can end soon after, and the owner then has no access until the blocking stops. Severity stays low: it lets no one in, exposes and loses no data, access comes back when the blocking stops, and the attacker must know a username, which is not secret because usernames are public (R-1), so it needs no guessing, and repeat the block every 15 minutes. Preventing it would change R-8, and blocking by network address instead would weaken the account-wide limit against T-3, so it would need a looser account-wide limit as well. The client accepted this risk on decision card 2, which offered that change. It is listed under "Remaining risks" in the delivery report.

**How it is verified**: QA API test that a signed-in session keeps working while the account is blocked (`TestSessionWorksWhileBlocked`).

## Out of scope

- Attacks on the server, its operating system, or its network: the client runs the server (Requirements: Out of scope).
- Encrypting the connection (HTTPS): set up by the client in front of the app. The cookie is marked `Secure`, so it is not sent without HTTPS.
