# 0017. QA's tests live in their own folder, outside the areas the developer may change

- Status: accepted
- Date: 2026-11-11

## Context

"Guardrails" 1 in `docs/DESIGN.md` says that the developer cannot change tests written by QA, and that the gate detects such a change mechanically. "Guardrails" 2 says that the gate compares the changed files with the areas listed in the design ("Areas the work may change" in `templates/internal/design.md`). The gate does both in phase 4, by path.

Nothing says where QA's tests live. In the worked example, QA's Go tests are `api/internal/http/*_test.go`, inside the developer's area `api/internal/http/**`. A check by path cannot tell those tests from the developer's code next to them, so it cannot tell whether the developer changed a QA test. An independent run of the `design` skill (#54) had to guess where QA's tests go.

The question is how QA's tests are kept apart from the developer's files, so that a path check can protect them. The `design` (#54) and `qa` (#57) skills need the answer in phase 3. What constrains it:

- QA writes tests from the specification only, never from the implementation (design principle 5).
- The developer still writes unit tests for their own code; those are part of the developer's work and the developer may change them.
- Each stack has its own conventions for where tests live (for example, Go keeps `_test.go` files next to the code), and the stack profiles that know them come in phase 4.

## Options considered

1. **A separate folder**: QA's tests live in one or more folders of their own, which the design names and keeps out of "Areas the work may change". The path alone protects them: any change by the developer under those folders is outside the areas, and is a change to a protected path. Where a stack keeps tests next to the code, as Go does, QA's tests in a folder of their own can reach the code only through what it exports or through its external interface (HTTP, the browser).
2. **A file-name convention**, such as `*_qa_test.go` or `*.qa.spec.ts`, protected by a pattern: QA's tests can sit inside the developer's packages and use their internals. But every stack needs its own naming rule, a file named wrongly is not protected at all, and the areas would need exclusion patterns, which are easier to get wrong than a folder.
3. **Leave it to each stack profile in phase 4**: each profile decides how QA's tests are told apart. It fits each stack best, but leaves the `design` and `qa` skills without a rule until then, and the example cannot be checked by path.

## Decision

Option 1. QA's tests live in their own folders, which the design lists under "QA's tests" and never under "Areas the work may change". Changes by the developer under those folders are changes to a protected path ("Guardrails" 1), and the gate's scope check (phase 4) flags them by path alone. The developer's own unit tests stay inside the developer's areas, next to the code they test.

Until the stack profiles exist, the design names the folders. From phase 4, each stack profile sets the folder name for its stack, and the design follows it.

## Reasons

- A path check is the simplest check the gate can make, and a folder is the simplest thing it can check: no naming rule per stack, and no exclusion patterns inside the developer's areas.
- A test file that is in the wrong place shows up as a change outside the areas, instead of silently losing its protection, as a wrongly named file would under option 2.
- Testing only through exported or external interfaces fits QA writing tests from the specification only: the tests check what the deliverable does, not how it is built.
- Naming the folders in the design now gives the `design` and `qa` skills a rule in phase 3; the profiles can fix the names per stack later without changing the rule.

## Consequences

- `docs/DESIGN.md` "Guardrails" 1 says where QA's tests live, and "Stack profiles" lists the folder for QA's tests among what a profile defines.
- `templates/internal/design.md` gets a "QA's tests" section listing the folders, with a note that they are never listed under "Areas the work may change".
- `templates/internal/test-report.md`: the tests named in "Results" are in QA's folders from the design.
- In the worked example, QA's Go tests move from `api/internal/http/` to `api/qa/`, and the browser tests stay in `web/e2e/`; the design lists both under "QA's tests", outside the areas.
- A Go test in its own folder is in its own package, so it can only use exported names and the HTTP interface, not the package's internals. QA tests the API through HTTP, which is how the client and the web app use it. Coverage of the code under test has to be measured across packages (for example, with `go test -coverpkg`).
- The `design` skill (#54) names QA's folders, and the `qa` skill (#57) writes tests only there. The gate's protected-path and scope checks (phase 4) read the folders from the design, and the `go` and `react-spa` profiles set their default names.
