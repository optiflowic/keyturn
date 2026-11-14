# Handoff: delivery 1 (accounts, sign-in, adding and listing tasks)

- From: developer
- To: QA, security, reviewer
- Based on requirements version 1 and the design document: [design.md](design.md)
- Branch and commit: `task/delivery-1` at `4e1c9a7`

## Summary

Delivery 1 is implemented: sign-up, sign-in and sign-out with the wrong-password limit, adding a task, and the private task list.
Changing, deleting, and hiding tasks (R-5, R-6, R-9) are left for delivery 2.

## What was done

- Accounts and sessions: sign-up with the 12-character minimum, Argon2id hashing, sign-in, sign-out, 7-day sessions, and the 5-attempt block (R-1, R-2, R-8)
- Tasks: create, list, and view one task (`GET /api/tasks/{id}`), filtered by the session's user ID (R-3, R-4, R-7)
- Storage: schema for `users`, `sessions`, and `tasks`, with migrations run at start-up (R-1, R-3, R-4)
- HTTP server: routes, session middleware, and serving the built web client (R-1 to R-4, R-7, R-8)
- Web client: sign-up, sign-in, and task list pages (R-1 to R-4, R-8)

## Requirements covered

| Requirement | Status | Notes |
|---|---|---|
| R-1 | done | |
| R-2 | done | |
| R-3 | done | |
| R-4 | done | |
| R-7 | done | for the routes in this delivery: create, list, and view one task |
| R-8 | done | |

## What is left

- R-5, R-6, R-9: planned for delivery 2, so this delivery's acceptance guide stays within five "Must check" items.

## How to run

1. Install the Go version required by `api/go.mod` and the Node.js version required by `web/package.json` (its `engines` field).
2. In `web/`, run `npm ci` and `npm run build`.
3. In `api/`, run `go run ./cmd/server -db ./tasks.db -addr localhost:8080`.
4. Open `http://localhost:8080` in a browser. The database file is created on first start.
5. Run the existing tests with `go test ./...` in `api/` and `npm test` in `web/`.

## Notes for the next role

- The session length (7 days) comes from decision card 1, answered by the client.
- Repeated sign-in blocking (T-6) is not prevented: the client accepted the risk on decision card 2. Do not add a limit by network address; it would change R-8.
- QA's tests go in `api/qa/` and `web/e2e/` (design.md "QA's tests"), outside the areas this work may change. The unit tests next to the code, such as `api/internal/account/password_test.go`, are the developer's.
- The task routes for changing and deleting (`PATCH` and `DELETE /api/tasks/{id}`) do not exist yet.
