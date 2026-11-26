# Test report: delivery 1

- Specification: requirements version 2
- Tested commit: `task/delivery-1` at `9b02d4f`
- Date: 2026-11-08

## Summary

All 10 acceptance criteria in delivery 1 pass (AC-1 to AC-4, AC-7, AC-9, and AC-10 to AC-13, the look, checked on the pages in a browser at the design's widths, with screenshots). AC-5, AC-6, and AC-8 belong to delivery 2 and were not tested.
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
| AC-10 | R-10 | pass | `web/qa/look/look.spec.ts`: `AC-10: each label sits above its field with 4 px between them` (each page, each width) |
| AC-11 | R-10 | pass | `web/qa/look/look.spec.ts`: `AC-11: every button is 44 px high and overlaps nothing` (each page, each width) |
| AC-12 | R-10 | pass | `web/qa/look/look.spec.ts`: `AC-12: nothing runs off the side` (each page, each width) |
| AC-13 | R-10 | pass | `web/qa/look/look.spec.ts`: `AC-13: every control shows a 2 px outline when reached with Tab` (each page) |

## Failures

None.

## Look

- Browser: Chrome Headless Shell, at the version that Playwright, as pinned in `web/package.json`, installs (the version Playwright's install printed is not written in this example)
- Screenshots: `keyturn/client/evidence/delivery-1/`

| Criterion | Widths | Measured | Judged from the screenshots | Screenshots |
|---|---|---|---|---|
| AC-10 | 360, 599, 600, 1280 px | on the sign-up, sign-in, and task list pages, every label is above its field, at the same left edge, with 4 px (`--space-1`) between them, and 16 px (`--space-3`) between one field and the next: pass | it is clear which label belongs to which field: pass | `sign-up-360.png`, `sign-up-1280.png`, `sign-in-360.png`, `sign-in-1280.png`, `task-list-360.png`, `task-list-1280.png` |
| AC-11 | 360, 599, 600, 1280 px | every button is 44 px high (`--control-height`), with 16 px (`--space-3`) inside on each side, and no button overlaps another or any text; the tasks of delivery 1 have no buttons, so the row of a task's buttons is checked in delivery 2: pass | the buttons of each form line up on the left under its fields, and the main button stands out: pass | the same six |
| AC-12 | 360, 599, 600, 1280 px | no page scrolls sideways, no element ends past the right edge of the window, and each page's content is at most 640 px wide (`--page-max-width`) with 16 px (`--space-3`) on each side: pass | no text or button is cut off at 360 px; a long task title wraps inside its row: pass | `sign-up-360.png`, `sign-in-360.png`, `task-list-360.png` |
| AC-13 | 1280 px | every link, field, and button reached with Tab shows a solid 2 px outline (`--focus-outline`) 2 px (`--focus-offset`) from it, the date field included: pass | the outline is clearly visible around the focused field: pass | `sign-up-1280-focus.png`, `sign-in-1280-focus.png`, `task-list-1280-focus.png` |

## Untested areas

- AC-5 (R-5, Must), AC-6 (R-6, Must), AC-8 (R-9, Nice): not in delivery 1 (planned for delivery 2).
- The look in Firefox and Safari (R-10, Must): the pages were checked in Chromium only.
- The pages' behavior in a real browser: QA's web tests render them in `jsdom`, with the API's answers stubbed, and the look tests only look at the pages; the client checks AC-1 and AC-3 in a browser in the acceptance guide.
- The `Secure` cookie over HTTPS: the tests run on `localhost` without HTTPS. The client sets up HTTPS on their server.

## Test counts

- Tests: 82 (33 Go, 7 web, 42 browser)
- Skipped or disabled tests: 0
- Coverage: 84% (Go, measured across all packages with `-coverpkg=./...`, because the tests in `api/qa/` are in a package of their own); not measured (web, browser)
