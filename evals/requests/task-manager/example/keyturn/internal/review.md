# Review: delivery 1

- Reviewed by: reviewer
- Reviewed change: `a51f0c2`..`9b02d4f`
- Compared against: [design.md](design.md), [conventions.md](conventions.md), [ADR 0001](adr/0001-one-repository-for-api-and-web-client.md), [ADR 0002](adr/0002-sqlite-database.md), [ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)

## Summary

Two findings, both fixed: one medium (a handler checked a password rule itself, against the design), one low (a name).
Nothing blocks delivery.

## Findings

### F-1: The sign-up handler checks the password length itself

- Location: `api/internal/http/signup.go:27`
- Severity: medium
- Category: design fit
- Based on: design.md "HTTP server" (handlers only parse input and call the services) and "Accounts and sessions"; [conventions.md](conventions.md) C-4
- Status: fixed

The handler rejected passwords shorter than 12 characters, and the account service did not check the length at all. The minimum (R-1) belongs to the account service, so that every way of creating an account applies it. Expected: the account service enforces the minimum, and the handler only passes the input on.

### F-2: Unclear name for the failed sign-in counter

- Location: `api/internal/account/signin.go:18`
- Severity: low
- Category: readability
- Based on: [conventions.md](conventions.md) C-1
- Status: fixed

`cnt` holds the number of wrong passwords in a row. Expected: a name that says so, such as `failedSignins`, matching the column name.
