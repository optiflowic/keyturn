# Conventions: task manager

Based on the design document: [design.md](design.md) (requirements version 1).

- Stack profile: `go` for `api/`, `react-spa` for `web/`
- Changed only by: an ADR in [adr/](adr/), listed under "Changes". The developer does not change this file or the files under "Tool rules".

## Summary

`gofmt` and `golangci-lint` check the Go API, Prettier and ESLint check the web client, and one Semgrep rule checks that every task query includes the user ID.
The handlers may not reach the database, and the web client may not render text as HTML; both are tool rules.
The reviewer checks names, comments, unused abstractions, and whether code sits in the part the design gives it.

## Tool rules

| File | Tool | Tool kind | What it enforces | Based on |
|---|---|---|---|---|
| none | `gofmt` | toolchain | the only accepted layout for `api/`, including QA's tests in `api/qa/` | profile `go` |
| `api/.golangci.yml` | golangci-lint | gate scanner | on all of `api/`, including `api/qa/`: `govet`, `staticcheck`, `errcheck`, `unused`; `gocyclo` at most 10; `funlen` at most 60 lines and 40 statements; `nestif` at most 4 | profile `go` |
| `api/.golangci.yml` | golangci-lint (`depguard`) | gate scanner | `api/internal/http/` may not import `api/internal/store` or `database/sql` | design "HTTP server" (handlers never query the database directly) |
| `.semgrep/task-queries.yml` | Semgrep | gate scanner | every SQL string in `api/internal/` that names the `tasks` table also names `user_id` | design "Tasks", T-1 |
| `web/.prettierrc.json` | Prettier | profile tool (`react-spa`) | the only accepted layout for `web/`, including QA's tests in `web/e2e/`; excludes `web/dist/` (build output) | profile `react-spa` |
| `web/eslint.config.js` | ESLint | profile tool (`react-spa`) | on `web/src/` and `web/e2e/`: `@eslint/js` and `typescript-eslint` recommended rules; `complexity` at most 10; `max-lines-per-function` at most 60; `max-depth` at most 4; excludes `web/dist/` (build output) | profile `react-spa` |
| `web/eslint.config.js` | ESLint (`no-restricted-syntax`) | profile tool (`react-spa`) | no `dangerouslySetInnerHTML` anywhere in `web/src/` | design "Web client", T-4 |

## Reviewer checklist

| ID | Check | Why no tool checks it |
|---|---|---|
| C-1 | Names say what a value or function is, in the words of the requirements and the design (for example, `failedSignins`, not `cnt`). | A linter checks the form of a name, not whether it says what the value is. |
| C-2 | Comments explain why the code does something, not what it does. | Whether a comment explains a reason needs reading it. |
| C-3 | No unused abstractions or speculative extension points: no interface with one implementation, no option nothing sets. | `unused` finds code nothing calls, not code that is called but not needed. |
| C-4 | Code sits in the part the design says, and each part does only what the design gives it (for example, rules such as the password minimum are in the account service, not in a handler). | The import rules cover which packages a part may use; what a part is responsible for needs the design. |
| C-5 | Errors returned to the web client say what went wrong in the user's terms and never include internal details (SQL, file paths, stack traces). | Whether a message reveals internals or makes sense to a user needs reading it. |

## Assumed defaults

None: every default comes from the stack profile.

## Changes

| Date | ADR | What changed |
|---|---|---|
| 2026-11-08 | none (first version) | first version |
