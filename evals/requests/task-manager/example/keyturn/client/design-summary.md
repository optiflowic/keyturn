# Design summary: task manager

Status: agreed

Based on requirements version 1.

## Summary

The app is one program that serves the pages and keeps the data in a single file on your server. People sign in with an email address and a password, and the server checks on every request that a person only reaches their own tasks.
You agreed to the three decisions that needed your agreement: where the data is kept, how signing in works, and the components the web pages are built with.

## What you need to do

> [!IMPORTANT]
> - Nothing right now.

## Must agree: decisions that need your agreement

### Decision 0002: SQLite as the database

- Agreement: agreed
- Serves: R-1, R-3, R-4, R-5, R-6
- Decision record (the full details): [decision record 0002](../internal/adr/0002-sqlite-database.md)

**What we decided**: Accounts and tasks are kept in one database file next to the app, using a database called SQLite. Reading that file needs one extra component (a "dependency") written by another team.

**Why**: It fits a few people on one server, and you have nothing extra to install or run.

**Other options we considered**:

- A separate database server (PostgreSQL): made for many users, but you would have to install, run, and back up a second program.
- Plain files: no extra component, but two changes at the same moment could overwrite each other.

**What it means for you**: To back up the app, you stop it and copy one file (copying it while the app runs can give a damaged copy). We checked the extra component: it is maintained, has no known security problems, and its license lets you use it freely.

**If you do not answer**: We do not start storing accounts or tasks (R-1, R-3 to R-6), so no work on the app itself starts.

### Decision 0003: Password sign-in with sessions stored on the server

- Agreement: agreed
- Serves: R-1, R-2, R-7, R-8
- Decision record (the full details): [decision record 0003](../internal/adr/0003-password-sign-in-with-server-sessions.md)

**What we decided**: When a person signs in, the server remembers the sign-in for 7 days, or until they sign out. Passwords are stored only in a scrambled form that is slow to check, so guessing them from a copied database is very hard, though a weak password can still be guessed. This uses one extra component from the team that makes the Go programming language.

**Why**: Signing out takes effect at once, and someone who copies the database would have to guess each password, which the scrambled form makes slow.

**Other options we considered**:

- Keeping the sign-in only in the browser: signing out could not end it at once, and it is easier to steal.
- Signing in with an outside account (for example, Google): you asked for email and password, and it would send sign-ins to an outside company.

**What it means for you**: People stay signed in for 7 days (you chose this in decision card 1). We checked the extra component: it is maintained, and its license lets you use it freely. It has one known security problem, in a part the app does not use; our automatic checks confirm that it stays unused.

**If you do not answer**: We do not start on signing up, signing in, or anything that needs it (R-1, R-2, R-7, R-8).

### Decision 0004: React and Vite for the web pages

- Agreement: agreed
- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-8, R-9
- Decision record (the full details): [decision record 0004](../internal/adr/0004-react-and-vite-for-the-web-client.md)

**What we decided**: The web pages are built with two widely used components from other teams: React, which draws the pages, and Vite, which prepares them for your server.

**Why**: Our automatic checks fully cover them, and React shows task titles as plain text by default, which protects against harmful titles (R-3).

**Other options we considered**:

- Writing the pages without components: nothing extra to trust, but more code written by hand, where harmful text is most often let through by mistake, and fewer automatic checks.

**What it means for you**: We checked both components: they are maintained, the versions we use have no known security problems, and their license lets you use them freely.

**If you do not answer**: We do not start on the web pages (everything you see in the browser).

## For information: other main decisions

### Decision 0001: One repository for the server part and the web pages

- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8, R-9
- Decision record (the full details): [decision record 0001](../internal/adr/0001-one-repository-for-api-and-web-client.md)

**What we decided**: All the code is kept in one repository, in two folders: one for the server part and one for the web pages.

**Why**: The app is small and almost every change touches both parts, so one place keeps changes simple.

**Other options we considered**:

- Two repositories: useful for large teams, but every change would need two linked changes.

**What it means for you**: You create one repository for the project.

## For information: development tools approved by the stack profile

These tools only check and test the code; none of them is part of the app you receive. The standard setup we follow for web pages names them, so they do not need your agreement. We checked each one like any other extra component: it is maintained, the version we use has no known security problems, and its license lets you use it freely.

- ESLint: reads the code of the web pages and points out common mistakes.
- Vitest: runs automatic tests of the parts of the web pages.
- Playwright: runs automatic tests that use the app in a real browser, the way a person would.
