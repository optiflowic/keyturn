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

| Name | Version | Kind | Purpose | Serves | New | Check |
|---|---|---|---|---|---|---|
| `modernc.org/sqlite` | pinned in `api/go.mod` | runtime | SQLite driver without C code | R-1, R-3 to R-6 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), BSD-3-Clause |
| `golang.org/x/crypto` | pinned in `api/go.mod` | runtime | Argon2id password hashing (`argon2` package only) | R-1, R-2 | yes | exists, maintained by the Go team, BSD-3-Clause; one OSV entry for this version (GO-0000-0001, checked 2026-11-08), in the `openpgp` package, which the app does not import; `govulncheck` must keep reporting it as not called |
| `react`, `react-dom` | pinned in `web/package.json` | runtime | web client | R-1 to R-9 | yes | exist, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `vite` | pinned in `web/package.json` | runtime | builds the web client that is delivered | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `eslint` | pinned in `web/package.json` | profile tool (`react-spa`) | lints the web client | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `vitest` | pinned in `web/package.json` | profile tool (`react-spa`) | unit tests for the web client | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `@playwright/test` | pinned in `web/package.json` | profile tool (`react-spa`) | browser tests of the whole app | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), Apache-2.0 |
| `@eslint/js`, `typescript-eslint` | pinned in `web/package.json` | profile tool (`react-spa`) | ESLint's recommended rules and its rules for TypeScript | R-1 to R-9 | yes | exist, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `typescript` | pinned in `web/package.json` | profile tool (`react-spa`) | type checks the web client's code; a peer dependency of `typescript-eslint` | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), Apache-2.0 |
| `prettier` | pinned in `web/package.json` | profile tool (`react-spa`) | formats the web client's code | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT |
| `golangci-lint` | pinned in `api/go.mod` (`tool` directive) | profile tool (`go`) | lints the API's code | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), GPL-3.0, used only as a tool, never linked into the app |

Not listed, as they are not dependencies ([ADR 0015 in keyturn](../../../../../../docs/adr/0015-dependency-kinds.md)): the Go and Node.js toolchains, covered by approving the stack, and the gate's scanners (`gosec`, `govulncheck`, Semgrep, gitleaks), which the gate installs outside the project.

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
| `web/package.json`, `web/package-lock.json` | the npm dependencies listed above only: those approved in ADR 0004 and the `react-spa` profile's development tools | R-1 to R-9 |
| `web/vite.config.ts` | the development server's proxy to the API only (added in delivery 1, see the delivery report) | R-1 to R-9 |

## QA's tests

| Path | What is tested there |
|---|---|
| `api/qa/**` | the API, through its HTTP interface only |
| `web/e2e/**` | the pages in a browser, against the built web client and the API |

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
