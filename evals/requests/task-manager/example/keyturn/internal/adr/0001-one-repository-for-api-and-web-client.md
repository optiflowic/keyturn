# 0001. One repository for the API and the web client

- Status: accepted
- Date: 2026-11-08
- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8, R-9
- Needs client agreement: no

## Context

The task manager has a Go API and a React web client (stack profiles `go` and `react-spa`). It is small (nine requirements), has one developer team, and the client runs it on one server. The two parts change together: almost every requirement touches both.

## Options considered

1. **One repository with `api/` and `web/` folders**: one pull request per change, one gate run, one place for the documents. The two parts can still be built and tested separately.
2. **Two repositories with a versioned API contract**: clear ownership per part, but every change needs two linked pull requests and contract tests, which is overhead without benefit at this size.

## Decision

One repository, with the API in `api/` and the web client in `web/` (option 1).

## Reasons

- The project is small and the parts change together, so separate repositories would only add coordination.
- The client creates and manages one repository instead of two.

## Consequences

- The gate runs both profiles on every pull request.
- If the project grows into several independent services, this decision is superseded by a new ADR.
