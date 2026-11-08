# Test report: delivery 1

- Specification: requirements version 1
- Tested commit: `task/delivery-1` at `9b02d4f`
- Date: 2026-11-08

## Summary

All 5 acceptance criteria in delivery 1 pass (AC-1 to AC-4, AC-7). AC-5, AC-6, and AC-8 belong to delivery 2 and were not tested.
No failures in the final run.

## Results

| Criterion | Covers | Result | Tests |
|---|---|---|---|
| AC-1 | R-1, R-2 | pass | `api/internal/http/account_test.go`: `TestSignUpSignOutSignIn`, `TestTasksNeedSession`; `web/e2e/account.spec.ts` |
| AC-2 | R-1 | pass | `api/internal/http/account_test.go`: `TestSignUpRejectsShortPassword` |
| AC-3 | R-3, R-4 | pass | `api/internal/http/task_test.go`: `TestCreateTaskKeepsTitleAsTyped`; `web/e2e/tasks.spec.ts` |
| AC-4 | R-7 | pass | `api/internal/http/task_test.go`: `TestOtherUserCannotListTasks`, `TestOtherUserTaskIsNotFound` |
| AC-5 | R-5 | not tested | |
| AC-6 | R-6 | not tested | |
| AC-7 | R-8 | pass | `api/internal/http/account_test.go`: `TestSignInBlockedAfterFiveFailures`, `TestBlockEndsAfterFifteenMinutes`, `TestSessionWorksWhileBlocked` |
| AC-8 | R-9 | not tested | |

## Failures

None.

## Untested areas

- AC-5, AC-6, AC-8: not in delivery 1 (planned for delivery 2).
- The look of the pages on phones: not covered by any acceptance criterion.
- The `Secure` cookie over HTTPS: the tests run on `localhost` without HTTPS. The client sets up HTTPS on their server.

## Test counts

- Tests: 39 (32 Go, 7 browser)
- Skipped or disabled tests: 0
- Coverage: 84% (Go); not measured (web)
