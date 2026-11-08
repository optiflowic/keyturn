# Review: delivery 1

- Reviewed by: reviewer
- Reviewed change: `a51f0c2`..`9b02d4f`
- Compared against: [design.md](design.md), `conventions.md`, [ADR 0001](adr/0001-one-repository-for-api-and-web-client.md), [ADR 0002](adr/0002-sqlite-database.md), [ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)

## Summary

Two findings, both fixed: one medium (a handler queried the database directly, against the design), one low (a name).
Nothing blocks delivery.

## Findings

### F-1: The task list handler queries the database directly

- Location: `api/internal/http/tasks.go:41`
- Severity: medium
- Category: design fit
- Based on: design.md "HTTP server" (handlers never query the database directly)
- Status: fixed

The list handler built its own SQL instead of calling the task service. It did filter by user ID, but the design keeps every task query in one place so that R-7 can be checked there. Expected: the handler calls the task service.

### F-2: Unclear name for the failed sign-in counter

- Location: `api/internal/account/signin.go:18`
- Severity: low
- Category: readability
- Based on: `conventions.md` (names say what a value is)
- Status: fixed

`cnt` holds the number of wrong passwords in a row. Expected: a name that says so, such as `failedSignins`, matching the column name.
