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

## Decision

SQLite, through `modernc.org/sqlite` (option 1).

## Reasons

- It fits the size of the project: a few users on one server.
- The client has one file to back up, and nothing else to run.
- The dependency check passed: the package exists, is actively maintained, has no OSV entries for the version pinned in `api/go.mod` (checked 2026-11-08), and uses the BSD-3-Clause license.

## Consequences

- Backing up the app means copying one file while the app is stopped, or using SQLite's online backup; copying it while the app runs can give a damaged copy, and recent changes may still be in the `-wal` file. The delivery explains how.
- If the app ever needs many users or several servers, a move to PostgreSQL needs a new ADR and a data migration.
