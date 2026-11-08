# Design: task manager

Based on requirements version 1.

## Summary

A Go API (`api/`) serves a JSON interface and the built React client (`web/`) from one program. Data is in one SQLite file. Every task query is filtered by the signed-in user's ID in the data access layer, so no handler can read another user's task by accident.

## Stack

- Stack profile: `go` for `api/`, `react-spa` for `web/`
- Repository structure: one repository, see [ADR 0001](adr/0001-one-repository-for-api-and-web-client.md)

## Structure

### HTTP server

- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8, R-9
- Location: `api/cmd/server/`, `api/internal/http/`

Routes requests, serves the built web client, and applies the session middleware to every `/api/` route except `POST /api/signup` and `POST /api/signin`. Handlers only parse input and call the account and task services; they never query the database directly.

### Accounts and sessions

- Serves: R-1, R-2, R-8
- Location: `api/internal/account/`

Sign-up (email uniqueness, password length of at least 12), Argon2id hashing, sign-in with the failed-attempt counter and the 15-minute block, and server-side sessions (7 days, see [ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)).

### Tasks

- Serves: R-3, R-4, R-5, R-6, R-7, R-9
- Location: `api/internal/task/`

Create, list (optionally without done tasks), update, and delete. Every function takes the user ID from the session as its first argument, and every SQL statement includes `WHERE user_id = ?`. A task that exists but belongs to someone else is reported as not found, the same as a missing task.

### Storage

- Serves: R-1, R-3, R-4, R-5, R-6
- Location: `api/internal/store/`

Opens the SQLite file, runs the schema migrations at start-up, and provides the queries used by the services. See [ADR 0002](adr/0002-sqlite-database.md).

### Web client

- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-8, R-9
- Location: `web/src/`

Sign-up, sign-in, and task list pages. Task titles are rendered as React text, never as HTML. The client never decides access; it shows what the API returns.

## Data model

### users

- Owner and access: each row is the user's own; only the account service reads it.

| Field | Type | Notes |
|---|---|---|
| id | integer | primary key |
| email | text | unique, stored in lower case |
| password_hash | text | Argon2id, with its parameters and salt |
| failed_signins | integer | reset to 0 after a successful sign-in |
| blocked_until | timestamp | null unless blocked (R-8) |

### sessions

- Owner and access: belongs to one user; only the session middleware reads it.

| Field | Type | Notes |
|---|---|---|
| token_hash | text | SHA-256 of the random session token; the token itself is only in the cookie |
| user_id | integer | references users.id |
| expires_at | timestamp | 7 days after sign-in |

### tasks

- Owner and access: owned by `user_id`. Only that user may read, change, or delete it (R-7).

| Field | Type | Notes |
|---|---|---|
| id | integer | primary key |
| user_id | integer | references users.id; part of every query |
| title | text | 1 to 200 characters, stored as typed |
| due_date | date | optional |
| done | boolean | |

## Libraries and external services

| Name | Version | Purpose | Serves | New | Check |
|---|---|---|---|---|---|
| `modernc.org/sqlite` | v1.34.1 | SQLite driver without C code | R-1, R-3 to R-6 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), BSD-3-Clause |
| `golang.org/x/crypto` | v0.58.0 | Argon2id password hashing (`argon2` package only) | R-1, R-2 | yes | exists, maintained by the Go team, BSD-3-Clause; one OSV entry for this version (GO-0000-0001, checked 2026-11-08), in the `openpgp` package, which the app does not import; `govulncheck` must keep reporting it as not called |
| `react`, `react-dom` | 18.3.1 | web client | R-1 to R-9 | yes | exist, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `vite` | 8.3.5 | builds the web client (development only) | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT. Earlier versions, such as 5.4.11, have OSV entries |

No external services.

## Areas the work may change

| Path | What changes | Serves |
|---|---|---|
| `api/cmd/server/**` | the program's entry point | R-1 to R-9 |
| `api/internal/http/**` | routes, handlers, session middleware | R-1 to R-9 |
| `api/internal/account/**` | accounts, passwords, sessions, sign-in limits | R-1, R-2, R-8 |
| `api/internal/task/**` | task operations | R-3 to R-7, R-9 |
| `api/internal/store/**` | schema, migrations, queries | R-1, R-3 to R-6 |
| `api/go.mod`, `api/go.sum` | the two approved Go dependencies only | R-1 to R-6 |
| `web/src/**`, `web/index.html` | pages and components | R-1 to R-6, R-8, R-9 |
| `web/package.json`, `web/package-lock.json` | the npm dependencies approved in ADR 0004 only | R-1 to R-9 |
| `web/vite.config.ts` | the development server's proxy to the API only (added in delivery 1, see the delivery report) | R-1 to R-9 |

## Requirements coverage

| Requirement | Parts |
|---|---|
| R-1 | Accounts and sessions, Storage, HTTP server, Web client |
| R-2 | Accounts and sessions, HTTP server, Web client |
| R-3 | Tasks, Storage, Web client |
| R-4 | Tasks, Storage, Web client |
| R-5 | Tasks, Storage, Web client |
| R-6 | Tasks, Storage, Web client |
| R-7 | Tasks, HTTP server |
| R-8 | Accounts and sessions, Web client |
| R-9 | Tasks, Web client |

## Decisions

- [ADR 0001](adr/0001-one-repository-for-api-and-web-client.md): one repository with `api/` and `web/`
- [ADR 0002](adr/0002-sqlite-database.md): SQLite through `modernc.org/sqlite`
- [ADR 0003](adr/0003-password-sign-in-with-server-sessions.md): server-side sessions and Argon2id
- [ADR 0004](adr/0004-react-and-vite-for-the-web-client.md): React and Vite for the web client

## Open questions

None.
