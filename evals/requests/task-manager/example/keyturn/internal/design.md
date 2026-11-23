# Design: task manager

Based on requirements version 2.

## Summary

A Go API (`api/`) serves a JSON interface and the built React client (`web/`) from one program. Data is in one SQLite file. Every task query is filtered by the signed-in user's ID in the data access layer, so no handler can read another user's task by accident.

## Stack

- Stack profile: `go` for `api/`, `react-spa` for `web/`
- Runtime: Go 1.27.4 for `api/`, Node.js 26.13.1 for `web/`, confirmed from the official sources on 2026-11-23
- Repository structure: one repository, see [ADR 0001](adr/0001-one-repository-for-api-and-web-client.md)

## Structure

### HTTP server

- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8, R-9
- Location: `api/cmd/server/`, `api/internal/http/`

Routes requests, serves the built web client, and applies the session middleware to every `/api/` route except `POST /api/signup` and `POST /api/signin`. Handlers only parse input and call the account and task services; they never query the database directly.

### Accounts and sessions

- Serves: R-1, R-2, R-8
- Location: `api/internal/account/`

Sign-up (username uniqueness, no `@` in a username, password length of at least 12), Argon2id hashing, sign-in with the failed-attempt counter and the 15-minute block, and server-side sessions (7 days, see [ADR 0003](adr/0003-password-sign-in-with-server-sessions.md)).

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
| username | text | unique, compared in lower case, never contains `@` |
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
| `modernc.org/sqlite` | pinned in `api/go.mod` | runtime | SQLite driver without C code | R-1, R-3 to R-6 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), BSD-3-Clause; works with Go 1.27.4 (checked 2026-11-23) |
| `golang.org/x/crypto` | pinned in `api/go.mod` | runtime | Argon2id password hashing (`argon2` package only) | R-1, R-2 | yes | exists, maintained by the Go team, BSD-3-Clause; one OSV entry for this version (GO-0000-0001, checked 2026-11-08), in the `openpgp` package, which the app does not import; `govulncheck` must keep reporting it as not called; works with Go 1.27.4 (checked 2026-11-23) |
| `react`, `react-dom` | pinned in `web/package.json` | runtime | web client | R-1 to R-9 | yes | exist, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `vite` | pinned in `web/package.json` | runtime | builds the web client that is delivered | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `eslint` | pinned in `web/package.json` | profile tool (`react-spa`) | lints the web client | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `vitest` | pinned in `web/package.json` | profile tool (`react-spa`) | the web client's unit tests and QA's tests of the pages | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `jsdom`, `@testing-library/react`, `@testing-library/dom` | pinned in `web/package.json` | profile tool (`react-spa`) | QA's tests show the pages in a simulated browser and use them as a person would | R-1 to R-9 | yes | exist, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `@eslint/js`, `typescript-eslint` | pinned in `web/package.json` | profile tool (`react-spa`) | ESLint's recommended rules and its rules for TypeScript | R-1 to R-9 | yes | exist, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `typescript` | pinned in `web/package.json` | profile tool (`react-spa`) | type checks the web client's code; a peer dependency of `typescript-eslint` | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), Apache-2.0; 6.0, the newest release `typescript-eslint` supports (its peer dependency asks for below 6.1, checked 2026-11-23), not the newest stable 7.0, as the [`react-spa` profile](../../../../../../profiles/react-spa/README.md) says; works with Node.js 26.13.1 |
| `prettier` | pinned in `web/package.json` | profile tool (`react-spa`) | formats the web client's code | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), MIT; works with Node.js 26.13.1 and with the other dependencies (`engines` and peer dependencies, checked 2026-11-23) |
| `golangci-lint` | pinned in `api/go.mod` (`tool` directive) | profile tool (`go`) | lints the API's code | R-1 to R-9 | yes | exists, maintained, no OSV entries for this version (checked 2026-11-08), GPL-3.0, used only as a tool, never linked into the app; works with Go 1.27.4 (checked 2026-11-23) |

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
| `web/package.json`, `web/package-lock.json` | the runtime npm dependencies listed above only (approved in ADR 0004); the `react-spa` profile's development tools are installed by `conventions`, and their versions never change here | R-1 to R-9 |
| `web/vite.config.ts` | the development server's proxy to the API only (added in delivery 1, see the delivery report) | R-1 to R-9 |

## QA's tests

| Path | What is tested there |
|---|---|
| `api/qa/**` | the API, through its HTTP interface only |
| `web/qa/**` | the pages, rendered in `jsdom` through the components the web client exports, with the API's answers stubbed |

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
