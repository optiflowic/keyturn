# 0001. One repository for the API and the web client

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8, R-9, R-10
- Needs client agreement: no

## Context

The task manager has a Go API and a React web client (stack profiles `go` and `react-spa`). It is small (nine requirements), has one developer team, and the client runs it on one server. The two parts change together: almost every requirement touches both.

## Options considered

1. **One repository with `api/` and `web/` folders**: one pull request per change, one gate run, one place for the documents. The two parts can still be built and tested separately.
2. **Two repositories with a versioned API contract**: clear ownership per part, but every change needs two linked pull requests and contract tests, which is overhead without benefit at this size.

## Maintainability after delivery

- Weight: the same as fit: the requirements do not say who maintains the deliverable.
- Less known choice: no.

| Option | Use | Modern | Documentation | People | Stability |
|---|---|---|---|---|---|
| One repository, `api/` and `web/` | an approach with no package: `api/` follows the "Server project" layout of Go's "Organizing a Go module", with its `go.mod` at the part's root (go.dev/doc/modules/layout, checked 2026-11-28); `web/` follows the `react-spa` profile's layout | the same documentation | the same documentation | anyone who knows Go or React finds their part laid out as that documentation shows | nothing to upgrade |
| Two repositories | not compared: it does not fit (two linked pull requests for every change, at this size) | | | | |

## Decision

One repository, with the API in `api/` and the web client in `web/` (option 1).

## Reasons

- The project is small and the parts change together, so separate repositories would only add coordination.
- The client creates and manages one repository instead of two.

## Consequences

- The gate runs both profiles on every pull request.
- If the project grows into several independent services, this decision is superseded by a new ADR.
