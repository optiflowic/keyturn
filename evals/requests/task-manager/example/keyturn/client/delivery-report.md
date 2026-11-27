# Delivery report: task manager, delivery 1

Based on requirements version 2. Test report: [test-report.md](test-report.md). Acceptance guide: [acceptance-guide.md](acceptance-guide.md).

## Summary

Delivery 1 is ready: signing up, signing in and out with a limit on wrong passwords, adding tasks, and a private task list, on tidy pages. Our tester checked all 10 acceptance criteria by using the pages, and all passed; every automatic check and review passed after fixes.
Not verified: how the app behaves behind HTTPS on your server, which only you can set up. Changing, deleting, and hiding tasks come in delivery 2.

## What you need to do

> [!IMPORTANT]
> - Read the test report (the acceptance guide asks no check of you), read "Remaining risks", and accept delivery 1, or tell us what to change.

## What was delivered

| Requirement | Status | Covered by | Notes |
|---|---|---|---|
| R-1: Sign up | delivered | AC-1, AC-2, AC-9 | |
| R-2: Sign in and sign out | delivered | AC-1 | |
| R-3: Add a task | delivered | AC-3 | |
| R-4: See your tasks | delivered | AC-3 | |
| R-7: Your tasks are private | delivered | AC-4 | covers adding and listing tasks; changing and deleting are checked again in delivery 2 |
| R-8: Limit wrong passwords | delivered | AC-7 | |
| R-10: The screens are tidy | delivered | AC-10 to AC-13 | on every page of this delivery, checked by our tester in a web browser; the screenshots are under "The screens" in the test report; the pages of delivery 2 are checked again then |

R-5, R-6, and R-9 are planned for delivery 2, so that each delivery covers no more than about ten acceptance criteria: this one covers ten.

## What was verified

| Check | Done by | How | Result | Details |
|---|---|---|---|---|
| Automated tests, code style, and security scans | Automated checks | ran 40 tests, the code style checks for both parts of the app, a scan for known security mistakes, a scan of every component for known problems (including the components they pull in), and a scan for leaked passwords | all pass; one ignored error was fixed, and two false alarms were explained by the security reviewer (a test value, and a known problem in a part of a component the app does not use) | gate log (not part of this example) |
| Behavior matches the requirements | Independent tester | automated tests written from the requirements only, without seeing the code, using the pages in a web browser as a person does, with a screenshot of each result; for how the pages look, the pages opened as narrow as a phone and as wide as a computer screen, measured, and photographed | all 10 acceptance criteria of this delivery pass | [test report](test-report.md), [the tester's detailed report](../internal/test-report.md) |
| Security issues tools cannot find | Security reviewer | tried to reach another account's tasks, tried many wrong passwords at the same moment, and checked every threat we listed | two serious problems were found and fixed; every listed threat now has a protection in place | [security review](../internal/security-review.md) |
| The code follows the design and is easy to maintain | Code reviewer | read the changes against the design and the coding conventions | two problems were found and fixed | [code review](../internal/review.md) |

## What was not verified

- The app behind HTTPS on your server: the tests ran on one computer without HTTPS. The sign-in only works over HTTPS (or on `localhost`), on purpose, to protect it.
- The pages in Firefox and Safari: our tester used them in Chrome's engine only. A later change that breaks the pages is found by our tester's next check, not by the automatic checks that run on every change, which do not use a browser.
- R-5, R-6, and R-9: not part of this delivery.
- Blocking changes to the main version of the code that skip keyturn's checks: your repository on GitHub has no branch protection, so such a change is noticed afterwards and reported to the maintainer, not blocked. GitHub offers branch protection on public repositories and on paid plans.

## Remaining risks

- No way to reset a forgotten password (out of scope): a person who forgets their password loses access to their tasks. You can ask us to add it later.
- If someone gets a copy of the database file, they can read everyone's tasks, and could try to guess passwords from it slowly. Keep the server and its backups private.
- Someone who knows a person's username can type wrong passwords on purpose to stop that person from signing in for 15 minutes, again and again. People already signed in keep working until their sign-in runs out (7 days after they signed in); after that, and for anyone not signed in, there is no access until the blocking stops. This is unlikely, because only you and a few friends use the app and the person blocking must repeat the block every 15 minutes (usernames are public, so finding one is easy), and not serious: no one gets in, no tasks are shown or lost, and access comes back when the blocking stops. You accepted this risk on 2026-11-08 ([decision card 2](decision-card-2.md)). If it happens, or you change your mind, tell us: we can block by network address instead, with a looser limit for the whole account; this makes password guessing a little easier, changes R-8, and needs your approval.

## Guardrails triggered

- The developer's first version changed a file outside the areas in the design (`web/vite.config.ts`). The gate flagged it; the design was updated to allow it only for the development server's address, and the change was reviewed again.
- The design left open which name the server's code is published under, which the programmer needed while building it. The architect answered it without changing the design ([answer A-1](../internal/design-answers.md)).
- The programmer also needed to know where the server's code takes the time from, so that tests can check that a sign-in block ends after 15 minutes without waiting. The architect's first answer could not be built within the rules for the code, so the maintainer had it withdrawn, and the architect gave another one that fits them ([answers A-2 to A-4](../internal/design-answers.md)). The programmer built that one.

## Models and tools used

| Used for | Model or tool | Version |
|---|---|---|
| PM, architect, reviewer, security | Claude Opus | recorded in the run log |
| Developer, QA | Claude Sonnet | recorded in the run log |
| AI tool | Claude Code | recorded in the run log |
| Go tests and checks | Go, `gofmt`, golangci-lint, `gosec`, `govulncheck`, Semgrep | Go as pinned in `api/go.mod`; the tools as recorded in the gate log |
| Web tests and checks | Node.js, Prettier, ESLint, TypeScript, Vitest, jsdom, Testing Library | as recorded in the gate log |
| Using and looking at the pages in a browser | Playwright, with Chrome Headless Shell | Playwright as pinned in `web/package.json`; the browser as recorded in the [tester's detailed report](../internal/test-report.md) |
| Secret scanning | gitleaks | recorded in the gate log |
