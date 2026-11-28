# Test report: delivery 1

- Specification: requirements version 2
- Tested commit: `task/delivery-1` at `9b02d4f`
- Date: 2026-11-08

## Summary

All 10 acceptance criteria in delivery 1 pass: AC-1 to AC-4, AC-7, and AC-9 operated on the pages in a browser, as a person does, with a screenshot of each expected result (AC-7's 15-minute block also through HTTP, with a clock a test moves), and AC-10 to AC-13, the look, checked on the pages at the design's widths, with screenshots. AC-5, AC-6, and AC-8 belong to delivery 2 and were not tested.
No failures in the final run.

## Results

| Criterion | Covers | Result | Tests |
|---|---|---|---|
| AC-1 | R-1, R-2 | pass | `web/qa/e2e/account.spec.ts`: `AC-1: an account works from sign-up to sign-in`; `api/qa/account_test.go`: `TestSignUpSignOutSignIn`, `TestTasksNeedSession`; `web/qa/account.test.tsx` |
| AC-2 | R-1 | pass | `web/qa/e2e/account.spec.ts`: `AC-2: a short password is refused`; `api/qa/account_test.go`: `TestSignUpRejectsShortPassword` |
| AC-3 | R-3, R-4 | pass | `web/qa/e2e/tasks.spec.ts`: `AC-3: a new task appears in the list as typed`; `api/qa/task_test.go`: `TestCreateTaskKeepsTitleAsTyped`; `web/qa/tasks.test.tsx` |
| AC-4 | R-7 | pass | `web/qa/e2e/tasks.spec.ts`: `AC-4: another account cannot see or open the task`; `api/qa/task_test.go`: `TestOtherUserCannotListTasks`, `TestOtherUserTaskIsNotFound` |
| AC-5 | R-5 | not tested | |
| AC-6 | R-6 | not tested | |
| AC-7 | R-8 | pass | `web/qa/e2e/account.spec.ts`: `AC-7: five wrong passwords block signing in`; `api/qa/account_test.go`: `TestSignInBlockedAfterFiveFailures`, `TestBlockEndsAfterFifteenMinutes`, `TestSessionWorksWhileBlocked` |
| AC-8 | R-9 | not tested | |
| AC-9 | R-1 | pass | `web/qa/e2e/account.spec.ts`: `AC-9: a username with @ is refused`; `api/qa/account_test.go`: `TestSignUpRejectsUsernameWithAt` |
| AC-10 | R-10 | pass | `web/qa/e2e/look.spec.ts`: `AC-10: each label sits above its field with 4 px between them` (each page, each width) |
| AC-11 | R-10 | pass | `web/qa/e2e/look.spec.ts`: `AC-11: every button is 44 px high and overlaps nothing` (each page, each width) |
| AC-12 | R-10 | pass | `web/qa/e2e/look.spec.ts`: `AC-12: nothing runs off the side` (each page, each width) |
| AC-13 | R-10 | pass | `web/qa/e2e/look.spec.ts`: `AC-13: every control shows a 2 px outline when reached with Tab` (each page, each width) |

## Checks

The browser steps ran in Chrome Headless Shell at the design's desktop width, 1280 px, against the deliverable started as "How to run" says. Each test signs up accounts of its own.

### AC-1: An account works from sign-up to sign-in

- Steps: 1. Open the start page, choose "Sign up", and sign up with a new username and a 14-character password. 2. Choose "Sign out". 3. Open the task list's address, `/tasks`. 4. Sign in with the same username and password.
- Observed: after step 3, the sign-in page was shown instead of a task list; after step 4, the page "Your tasks" was shown, with "No tasks yet." Through HTTP, the task list answered "not signed in" without a session, and the list with one.
- Screenshots: `ac-1-tasks-shows-sign-in.png`: the sign-in page shown at `/tasks` after signing out; `ac-1-signed-in.png`: the empty task list after signing in

### AC-2: A short password is refused

- Steps: 1. Open the sign-up page. 2. Sign up with a new username and the 11-character password `abcdefghijk`. 3. Try to sign in with that username and password.
- Observed: in step 2 the page stayed on "Sign up" and showed "The password must be at least 12 characters long." under the password field; in step 3 signing in failed, so no account had been created. Through HTTP, the sign-up was refused with the same message.
- Screenshots: `ac-2-short-password.png`: the message under the password field

### AC-3: A new task appears in your list

- Steps: 1. Sign up and sign in. 2. In "Title", type `<b>Buy milk</b>`; in "Due date", choose 2026-11-09; choose "Add". 3. Reload the page.
- Observed: the list showed one task with the title `<b>Buy milk</b>`, the `<b>` and `</b>` shown as text and nothing in bold, and "Due 2026-11-09", before and after the reload. Through HTTP, the task came back with the title exactly as sent.
- Screenshots: `ac-3-task-added.png`: the task in the list, with its title as typed and its due date

### AC-4: Another person cannot see or open your tasks

- Steps: 1. Sign up as a first account, and add the task "Private task". 2. Open the task, and copy the address the browser shows. 3. Sign out, and sign up as a second account. 4. Look at the task list. 5. Open the copied address.
- Observed: in step 4 the list showed "No tasks yet."; in step 5 the page showed "Task not found". Through HTTP, the second account's list had no tasks, and the first account's task answered "not found" to it.
- Screenshots: `ac-4-second-account-list.png`: the second account's empty list; `ac-4-task-not-found.png`: "Task not found" at the copied address

### AC-7: Wrong passwords block signing in for a while

- Steps: on the pages: 1. Sign up, and sign out. 2. Sign in with that username and a wrong password, 5 times. 3. Sign in with the right password. Through HTTP, with a clock the test sets (design answer A-4): 4. Do steps 2 and 3 again on a new account at 14:20. 5. Move the clock to 14:34 and sign in with the right password, then to 14:35 and sign in again. 6. Sign in on another session of the account before step 4, and use it during the block.
- Observed: in step 3 the page stayed on "Sign in" and showed "Too many wrong passwords. You can try again at 14:35.", 15 minutes after the fifth wrong password. In step 5, signing in was refused at 14:34 and worked at 14:35. In step 6, the session that was already signed in kept working during the block.
- Screenshots: `ac-7-blocked.png`: the message after the right password

### AC-9: A username with `@` is refused

- Steps: 1. Open the sign-up page. 2. Sign up with the username `me@example.com` and a 14-character password. 3. Try to sign in with them.
- Observed: in step 2 the page stayed on "Sign up" and showed "A username cannot contain @." under the username field; in step 3 signing in failed. Through HTTP, the sign-up was refused with the same message.
- Screenshots: `ac-9-username-with-at.png`: the message under the username field

### AC-10: Labels sit with their fields

See Look.

### AC-11: Buttons line up

See Look.

### AC-12: The pages fit a phone

See Look.

### AC-13: You can see where you are with the keyboard

See Look.

## Failures

None.

## Look

- Browser: Chrome Headless Shell, driven by Playwright, the E2E tool of the `react-spa` profile, at the versions pinned in `web/package.json` (the versions Playwright printed are not written in this example)
- Screenshots: `keyturn/client/evidence/delivery-1/`

| Criterion | Widths | Measured | Judged from the screenshots | Screenshots |
|---|---|---|---|---|
| AC-10 | 360, 599, 600, 1280 px | on the sign-up, sign-in, and task list pages, every label is above its field, at the same left edge, with 4 px (`--space-1`) between them, and 16 px (`--space-3`) between one field and the next: pass | it is clear which label belongs to which field: pass | `sign-up-360.png`, `sign-up-1280.png`, `sign-in-360.png`, `sign-in-1280.png`: each label above its field; `task-list-360.png`, `task-list-1280.png`: the title and due date fields with their labels, and the list |
| AC-11 | 360, 599, 600, 1280 px | every button is 44 px high (`--control-height`), with 16 px (`--space-3`) inside on each side, and no button overlaps another or any text; the tasks of delivery 1 have no buttons, so the row of a task's buttons is checked in delivery 2: pass | the buttons of each form line up on the left under its fields, and the main button stands out: pass | the same six |
| AC-12 | 360, 599, 600, 1280 px | no page scrolls sideways, no element ends past the right edge of the window, and each page's content is at most 640 px wide (`--page-max-width`) with 16 px (`--space-3`) on each side: pass | no text or button is cut off at 360 px; a long task title wraps inside its row: pass | `sign-up-360.png`, `sign-in-360.png`, `task-list-360.png`: each page at 360 px, with a long task title wrapped in its row |
| AC-13 | 360, 599, 600, 1280 px | every link, field, and button reached with Tab shows a solid 2 px outline (`--focus-outline`) 2 px (`--focus-offset`) from it, the date field included: pass | the outline is clearly visible around the focused control: pass | `sign-up-360-focus.png`, `sign-up-1280-focus.png`, `sign-in-360-focus.png`, `sign-in-1280-focus.png`: the username field marked after one press of Tab; `task-list-360-focus.png`, `task-list-1280-focus.png`: the "Sign out" button marked after one press of Tab |

## Untested areas

- AC-5 (R-5, Must), AC-6 (R-6, Must), AC-8 (R-9, Nice): not in delivery 1 (planned for delivery 2).
- The look (R-10, Must) and the steps of AC-1 to AC-4, AC-7, and AC-9 in Firefox and Safari: the browser tests ran in Chromium only.
- The `Secure` cookie over HTTPS: the tests run on `localhost` without HTTPS. The client sets up HTTPS on their server, after the delivery.

## Test counts

- Tests: 97 (33 Go, 7 web, 57 browser: 6 for the steps of AC-1 to AC-4, AC-7, and AC-9, and 51 for the look)
- Skipped or disabled tests: 0
- Coverage: 84% (Go, measured across all packages with `-coverpkg=./...`, because the tests in `api/qa/` are in a package of their own); not measured (web, browser)
