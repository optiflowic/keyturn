# Security review: delivery 1

- Reviewed by: security
- Reviewed change: `a51f0c2`..`9b02d4f`
- Compared against: [threat-model.md](threat-model.md), [design.md](design.md), [ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)

## Summary

Three findings, all fixed: two high (another user's task could be told apart from a missing one; wrong-password attempts made at the same moment were not all counted) and one low (an ignored error at shutdown).
Every threat in the threat model has an implemented mitigation. Nothing blocks delivery.

## Findings

### F-1: Another user's task answered "forbidden" instead of "not found"

- Location: `api/internal/task/service.go:57`
- Severity: high
- Category: security
- Based on: T-1, R-7
- Status: fixed

Fetching another user's task returned 403, and a missing task returned 404. That told an attacker which task IDs exist, and the separate ownership check was one place where a later change could forget it. Expected: one query that includes the user ID, and 404 for both cases.

### F-2: Wrong passwords sent at the same moment were not all counted

- Location: `api/internal/account/signin.go:33`
- Severity: high
- Category: security
- Based on: T-3, R-8
- Status: fixed

The counter was read, increased in the program, and written back. Twenty wrong passwords sent at the same moment were counted as one, which allowed more than 5 guesses. Expected: the database increases the counter in one statement, and the block is decided from the value it returns.

### F-3: An error at shutdown was ignored

- Location: `api/cmd/server/main.go:52`
- Severity: low
- Category: security
- Based on: gosec G104 (see scan triage)
- Status: fixed

The error from closing the database at shutdown was ignored, so a failed final write would go unnoticed. Expected: the error is logged.

## Security

### Threat model check

| Threat | Mitigation implemented | Remaining risk | Evidence |
|---|---|---|---|
| T-1 | yes | none | every query in `api/internal/task/` includes `user_id`; `TestOtherUserTaskIsNotFound`; F-1 fixed |
| T-2 | yes | none | session middleware on every `/api/` route except sign-up and sign-in; `TestTasksNeedSession` |
| T-3 | yes | none | 12-character minimum; atomic counter and 15-minute block; `TestSignInBlockedAfterFiveFailures`; F-2 fixed |
| T-4 | yes | none | no `dangerouslySetInnerHTML` (lint rule passes); `HttpOnly` cookie; `TestCreateTaskKeepsTitleAsTyped` |
| T-5 | yes | none | Argon2id with a random salt in `api/internal/account/password.go`; session tokens stored as SHA-256 |
| T-6 | partly | accepted: [decision card 2](../client/decision-card-2.md) | a blocked account's existing sessions keep working; `TestSessionWorksWhileBlocked`. Repeated blocking is not prevented; the client accepted it, and it is low and only blocks new sign-ins for a while, so it qualifies |

### Scan triage

| Tool | Finding | Location | Triage | Reason |
|---|---|---|---|---|
| gosec | G104 (unhandled error) | `api/cmd/server/main.go:52` | real | listed as F-3 |
| govulncheck | GO-0000-0001 | `golang.org/x/crypto` (version pinned in `api/go.mod`), `openpgp` package | false positive | the advisory is in the `openpgp` package, which the app does not import; govulncheck reports it as not called, because only the `argon2` package is used. Check again if the app ever imports `openpgp` |
| gitleaks | generic-api-key | `api/internal/account/password_test.go:12` | false positive | a fixed test salt used only to make a test repeatable, not a secret; it is not used outside the test |
