# Delivery report: task manager, delivery 1

Based on requirements version 1. Acceptance guide: [acceptance-guide.md](acceptance-guide.md).

## Summary

Delivery 1 is ready: signing up, signing in and out with a limit on wrong passwords, adding tasks, and a private task list. Every automatic check and review passed after fixes.
Not verified: how the app behaves behind HTTPS on your server, which only you can set up. Changing, deleting, and hiding tasks come in delivery 2.

## What you need to do

> [!IMPORTANT]
> - Do the 5 "Must check" items in the acceptance guide, read "Remaining risks", and accept delivery 1, or tell us what to change.

## What was delivered

| Requirement | Status | Covered by | Notes |
|---|---|---|---|
| R-1: Sign up | delivered | AC-1, AC-2 | |
| R-2: Sign in and sign out | delivered | AC-1 | |
| R-3: Add a task | delivered | AC-3 | |
| R-4: See your tasks | delivered | AC-3 | |
| R-7: Your tasks are private | delivered | AC-4 | covers adding and listing tasks; changing and deleting are checked again in delivery 2 |
| R-8: Limit wrong passwords | delivered | AC-7 | |

R-5, R-6, and R-9 are planned for delivery 2, so that this delivery has no more than five "Must check" items.

## What was verified

| Check | Done by | How | Result | Details |
|---|---|---|---|---|
| Automated tests, code style, and security scans | Automated checks | ran 38 tests, the code style checks for both parts of the app, a scan for known security mistakes, a scan of every component for known problems, and a scan for leaked passwords | all pass; one ignored error was fixed, and one false alarm about a test value was explained by the security reviewer | gate log (not part of this example) |
| Behavior matches the requirements | Independent tester | automated tests written from the requirements only, without seeing the code | all 5 acceptance criteria of this delivery pass | [test report](../internal/test-report.md) |
| Security issues tools cannot find | Security reviewer | tried to reach another account's tasks, tried many wrong passwords at the same moment, and checked every threat we listed | two serious problems were found and fixed; every listed threat now has a protection in place | [security review](../internal/security-review.md) |
| The code follows the design and is easy to maintain | Code reviewer | read the changes against the design and the coding conventions | two problems were found and fixed | [code review](../internal/review.md) |

## What was not verified

- The app behind HTTPS on your server: the tests ran on one computer without HTTPS. The sign-in only works over HTTPS (or on `localhost`), on purpose, to protect it.
- How the pages look on phones: no requirement covers it, so nobody checked it.
- R-5, R-6, and R-9: not part of this delivery.

## Remaining risks

- No way to reset a forgotten password (out of scope): a person who forgets their password loses access to their tasks. You can ask us to add it later.
- If someone gets a copy of the database file, they can read everyone's tasks (passwords stay protected). Keep the server and its backups private.

## Guardrails triggered

- The developer's first version changed a file outside the areas in the design (`web/vite.config.ts`). The gate flagged it; the design was updated to allow it only for the development server's address, and the change was reviewed again.

## Models and tools used

| Used for | Model or tool | Version |
|---|---|---|
| PM, architect, reviewer, security | Claude Opus | claude-opus-5-5 |
| Developer, QA | Claude Sonnet | claude-sonnet-5-5 |
| AI tool | Claude Code | 2.3.0 |
| Go tests and checks | Go, `go vet`, `gosec`, `govulncheck` | 1.23.4, 1.23.4, 2.21.4, 1.1.4 |
| Web tests and checks | Node.js, ESLint, Vitest, Playwright | 22.11.0, 9.15.0, 2.1.8, 1.49.1 |
| Secret scanning | gitleaks | 8.21.2 |
