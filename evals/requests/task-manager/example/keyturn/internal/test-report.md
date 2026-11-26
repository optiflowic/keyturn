# Test report: delivery 1

- Specification: requirements version 2
- Tested commit: `task/delivery-1` at `9b02d4f`
- Date: 2026-11-08

## Summary

All 6 acceptance criteria in delivery 1 that tests can check pass (AC-1 to AC-4, AC-7, AC-9). AC-10 to AC-13 (the look) are in delivery 1 but were not tested: `jsdom` does not lay pages out, so the client checks them by hand. AC-5, AC-6, and AC-8 belong to delivery 2 and were not tested.
No failures in the final run.

## Results

| Criterion | Covers | Result | Tests |
|---|---|---|---|
| AC-1 | R-1, R-2 | pass | `api/qa/account_test.go`: `TestSignUpSignOutSignIn`, `TestTasksNeedSession`; `web/qa/account.test.tsx` |
| AC-2 | R-1 | pass | `api/qa/account_test.go`: `TestSignUpRejectsShortPassword` |
| AC-3 | R-3, R-4 | pass | `api/qa/task_test.go`: `TestCreateTaskKeepsTitleAsTyped`; `web/qa/tasks.test.tsx` |
| AC-4 | R-7 | pass | `api/qa/task_test.go`: `TestOtherUserCannotListTasks`, `TestOtherUserTaskIsNotFound` |
| AC-5 | R-5 | not tested | |
| AC-6 | R-6 | not tested | |
| AC-7 | R-8 | pass | `api/qa/account_test.go`: `TestSignInBlockedAfterFiveFailures`, `TestBlockEndsAfterFifteenMinutes`, `TestSessionWorksWhileBlocked` |
| AC-8 | R-9 | not tested | |
| AC-9 | R-1 | pass | `api/qa/account_test.go`: `TestSignUpRejectsUsernameWithAt` |
| AC-10 | R-10 | not tested | |
| AC-11 | R-10 | not tested | |
| AC-12 | R-10 | not tested | |
| AC-13 | R-10 | not tested | |

## Failures

None.

## Untested areas

- AC-5 (R-5, Must), AC-6 (R-6, Must), AC-8 (R-9, Nice): not in delivery 1 (planned for delivery 2).
- AC-10 to AC-13 (R-10, Must): the look of the pages; QA's web tests render them in `jsdom`, which does not lay them out, so no test can see where a label sits or whether a page scrolls sideways. The client checks them in checks 3 and 4 of the acceptance guide.
- The pages in a real browser: QA's web tests render them in `jsdom`, with the API's answers stubbed; the client checks AC-1 and AC-3 in a browser in the acceptance guide.
- The `Secure` cookie over HTTPS: the tests run on `localhost` without HTTPS. The client sets up HTTPS on their server.

## Test counts

- Tests: 40 (33 Go, 7 web)
- Skipped or disabled tests: 0
- Coverage: 84% (Go, measured across all packages with `-coverpkg=./...`, because the tests in `api/qa/` are in a package of their own); not measured (web)
