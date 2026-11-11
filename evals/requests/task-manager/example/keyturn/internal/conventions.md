# Conventions: task manager

Based on the design document: [design.md](design.md) (requirements version 1).

- Stack profile: No profile: see "Assumed defaults"
- Changed only by: an ADR in [adr/](adr/), listed under "Changes". The developer does not change this file or the files under "Tool rules".

## Summary

`gofmt` and `golangci-lint` check the Go API, Prettier and ESLint check the web client, and one Semgrep rule checks that every task query includes the user ID.
The handlers may not reach the database, and the web client may not render text as HTML; both are tool rules.
The reviewer checks names, comments, unused abstractions, and whether code sits in the part the design gives it.

## Tool rules

| File | Tool | What it enforces | Based on |
|---|---|---|---|
| none | `gofmt` | the only accepted layout for `api/` | assumed default |
| `api/.golangci.yml` | golangci-lint | `govet`, `staticcheck`, `errcheck`, `unused`; `gocyclo` at most 10; `funlen` at most 60 lines and 40 statements; `nestif` at most 4 | assumed default |
| `api/.golangci.yml` | golangci-lint (`depguard`) | `api/internal/http/` may not import `api/internal/store` or `database/sql` | design "HTTP server" (handlers never query the database directly) |
| `.semgrep/task-queries.yml` | Semgrep | every SQL string in `api/internal/` that names the `tasks` table also names `user_id` | design "Tasks", T-1 |
| `web/.prettierrc.json` | Prettier | the only accepted layout for `web/src/`; excludes `web/dist/` (build output) | assumed default |
| `web/eslint.config.js` | ESLint | `@eslint/js` and `typescript-eslint` recommended rules; `complexity` at most 10; `max-lines-per-function` at most 60; `max-depth` at most 4; excludes `web/dist/` (build output) | assumed default |
| `web/eslint.config.js` | ESLint (`no-restricted-syntax`) | no `dangerouslySetInnerHTML` anywhere in `web/src/` | design "Web client", T-4 |

## Reviewer checklist

| ID | Check | Why no tool checks it |
|---|---|---|
| C-1 | Names say what a value or function is, in the words of the requirements and the design (for example, `failedSignins`, not `cnt`). | A linter checks the form of a name, not whether it says what the value is. |
| C-2 | Comments explain why the code does something, not what it does. | Whether a comment explains a reason needs reading it. |
| C-3 | No unused abstractions or speculative extension points: no interface with one implementation, no option nothing sets. | `unused` finds code nothing calls, not code that is called but not needed. |
| C-4 | Code sits in the part the design says, and each part does only what the design gives it (for example, rules such as the password minimum are in the account service, not in a handler). | The import rules cover which packages a part may use; what a part is responsible for needs the design. |
| C-5 | Errors returned to the web client say what went wrong in the user's terms and never include internal details (SQL, file paths, stack traces). | Whether a message reveals internals or makes sense to a user needs reading it. |

## Assumed defaults

- Formatters: `gofmt` and Prettier, the most widely used for Go and TypeScript; no profile exists yet.
- Linters: golangci-lint and ESLint with `typescript-eslint`, the most widely used for Go and TypeScript.
- Limits: complexity 10, 60 lines per function, nesting depth 4, the skill's starting values; to be replaced by the `go` and `react-spa` profiles.
- Tools: `gofmt`, golangci-lint, and Semgrep are installed by the gate, not added to `api/go.mod`. Prettier, ESLint, and `typescript-eslint` are development dependencies pinned in `web/package.json`.

## Changes

| Date | ADR | What changed |
|---|---|---|
| 2026-11-08 | none (first version) | first version |
