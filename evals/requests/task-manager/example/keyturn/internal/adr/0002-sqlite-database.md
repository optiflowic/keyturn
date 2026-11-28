# 0002. SQLite as the database

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-3, R-4, R-5, R-6
- Needs client agreement: yes

## Context

Accounts and tasks must be stored. The client runs the app on one small server for a few people, and does not want to manage extra services. Storing data needs a new dependency, which always needs the client's approval.

## Options considered

1. **SQLite, through the pure-Go driver `modernc.org/sqlite`**: the database is one file next to the app, with nothing else to install or run. Handles a few users easily. The driver needs no C compiler, so the build stays simple. One new dependency.
2. **PostgreSQL**: handles many users and several servers, but the client would have to install, run, secure, and back up a second service, which is too much for a few people.
3. **Plain files (JSON)**: no dependency, but no safe handling of two changes at the same time, and every query would be written by hand.
4. **SQLite, through the cgo driver `github.com/mattn/go-sqlite3`**: the same database, through the more widely used Go driver, but it is a cgo package: building the app needs a C compiler (`gcc`) and `CGO_ENABLED=1`, on every machine that builds it and in CI.

## Maintainability after delivery

- Weight: the same as fit: the requirements do not say who maintains the deliverable (the client runs the app, R-1 to R-10 say nothing about who changes its code).
- Less known choice: yes: `modernc.org/sqlite` is less used than `github.com/mattn/go-sqlite3`, but it fits clearly better: the build needs no C compiler, so anyone who maintains the app builds it with the Go toolchain alone. Both reach the same SQLite through Go's standard `database/sql`, so most of what people know about one applies to the other.

| Option | Use | Modern | Documentation | People | Stability |
|---|---|---|---|---|---|
| `modernc.org/sqlite` | 515 stars on GitLab, latest release 2026-11-22 (gitlab.com/cznic/sqlite, proxy.golang.org, checked 2026-11-28) | its documentation: "a CGo-free port of the C SQLite3 library" (pkg.go.dev, checked 2026-11-28) | its package documentation, and SQLite's own | fewer people know this driver; the code uses only `database/sql`, which every Go developer knows | frequent releases that follow SQLite's, without breaking `database/sql` use |
| PostgreSQL | very widely used (not compared further: it does not fit one small server) | current | extensive | many | stable |
| Plain files | code of the project's own: no use, documentation, or people outside it | — | only what the project writes | only those who read the code | as stable as the project's code |
| `github.com/mattn/go-sqlite3` | 9,282 stars on GitHub, latest release 2026-11-05 (github.com, proxy.golang.org, checked 2026-11-28) | its README: "_go-sqlite3_ is _cgo_ package ... you need gcc" (github.com, checked 2026-11-28) | its README, and SQLite's own | the most known Go driver for SQLite | stable, long-lived, with `database/sql` |

## Decision

SQLite, through `modernc.org/sqlite` (option 1).

## Reasons

- It fits the size of the project: a few users on one server.
- The client has one file to back up, and nothing else to run.
- Of the two SQLite drivers, the less used one fits clearly better: it keeps the build to the Go toolchain alone, for whoever maintains the app. The design summary tells the client so.
- The dependency check passed: the package exists, is actively maintained, has no OSV entries for the version pinned in `api/go.mod` (checked 2026-11-08), and uses the BSD-3-Clause license.

## Consequences

- Backing up the app means copying one file while the app is stopped, or using SQLite's online backup; copying it while the app runs can give a damaged copy, and recent changes may still be in the `-wal` file. The delivery explains how.
- If the app ever needs many users or several servers, a move to PostgreSQL needs a new ADR and a data migration.
