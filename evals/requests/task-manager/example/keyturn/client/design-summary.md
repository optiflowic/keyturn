# Design summary: task manager

Status: agreed

Based on requirements version 2.

## Summary

The app is one program that serves the pages and keeps the data in a single file on your server. People sign in with a username and a password, and the server checks on every request that a person only reaches their own tasks.
You agreed to the three decisions that needed your agreement: where the data is kept, how signing in works, and the components the web pages are built with.

You did not say who will maintain the app's code after delivery, so in every choice we weighed how easily other people could maintain it as much as how well it fits. If your own team, or another company, will maintain it, or already works with particular tools, tell us before the work starts: it can change our choices.

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
- A more widely used component for reading the same database: more people know it, but building the app with it needs an extra program (a C compiler) on every computer that builds it.

**For whoever maintains it**: This counted as much as how well each option fits, because you did not say who will maintain the app (see "Summary").

- The component we chose: used by fewer people than the other one below, and maintained, with its latest update in November 2026. Its own documentation describes it as the same database made to build without the extra program. The app's code reaches it only through the Go language's standard way of reading databases, which every Go developer knows.
- The more widely used component for the same database: far more people follow it, and it is maintained too, but its own documentation says that building with it needs the extra program (a C compiler).
- Checked on 28 November 2026.

**What it means for you**: To back up the app, you stop it and copy one file (copying it while the app runs can give a damaged copy). We checked the extra component: it is maintained, has no known security problems, and its license lets you use it freely. It is less widely known than the other component for the same database, so fewer people will have used it before; we still chose it because whoever maintains the app can build it without the extra program, and the app's code uses it only through the Go language's standard way of reading databases, which every Go developer knows.

**If you do not answer**: We do not start storing accounts or tasks (R-1, R-3 to R-6), so no work on the app itself starts.

### Decision 0003: Password sign-in with sessions stored on the server

- Agreement: agreed
- Serves: R-1, R-2, R-7, R-8
- Decision record (the full details): [decision record 0003](../internal/adr/0003-password-sign-in-with-server-sessions.md)

**What we decided**: When a person signs in, the server remembers the sign-in for 7 days, or until they sign out. Passwords are stored only in a scrambled form that is slow to check, so guessing them from a copied database is very hard, though a weak password can still be guessed. This uses one extra component from the team that makes the Go programming language.

**Why**: Signing out takes effect at once, and someone who copies the database would have to guess each password, which the scrambled form makes slow.

**Other options we considered**:

- Keeping the sign-in only in the browser: signing out could not end it at once, and it is easier to steal.
- Signing in with an outside account (for example, Google): you asked for your own accounts with a password, and it would send sign-ins to an outside company.

**For whoever maintains it**: This counted as much as how well each option fits, because you did not say who will maintain the app (see "Summary").

- The sessions use only what comes with the Go language, which every Go developer knows. The password scrambling comes from the team that makes Go, and its current documentation recommends exactly the method we use; it was last updated in November 2026.
- No other option was compared: the others do not fit (see above).
- Checked on 28 November 2026.

**What it means for you**: People stay signed in for 7 days (you chose this in decision card 1). We checked the extra component: it is maintained, and its license lets you use it freely. It has one known security problem, in a part the app does not use; our automatic checks confirm that it stays unused.

**If you do not answer**: We do not start on signing up, signing in, or anything that needs it (R-1, R-2, R-7, R-8).

### Decision 0004: React and Vite for the web pages

- Agreement: agreed
- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-8, R-9, R-10
- Decision record (the full details): [decision record 0004](../internal/adr/0004-react-and-vite-for-the-web-client.md)

**What we decided**: The web pages are built with two widely used components from other teams: React, which draws the pages, and Vite, which prepares them for your server.

**Why**: Our automatic checks fully cover them, and React shows task titles as plain text by default, which protects against harmful titles (R-3).

**Other options we considered**:

- Writing the pages without components: nothing extra to trust, but more code written by hand, where harmful text is most often let through by mistake, and fewer automatic checks.

**For whoever maintains it**: This counted as much as how well each option fits, because you did not say who will maintain the app (see "Summary").

- React and Vite: two of the most widely used components for web pages, used millions of times a week, so many people know them, and Vite was updated in the last weeks. React's documentation now recommends a ready-made framework for new apps, but still describes building one with Vite, which fits three pages.
- Writing the pages without components: everything would be our own code, so whoever maintains it must first learn how it works from the code alone, with no outside documentation or people who already know it.
- Checked on 28 November 2026.

**What it means for you**: We checked both components: they are maintained, the versions we use have no known security problems, and their license lets you use them freely.

**If you do not answer**: We do not start on the web pages (everything you see in the browser).

## For information: other main decisions

### Decision 0001: One repository for the server part and the web pages

- Serves: R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8, R-9, R-10
- Decision record (the full details): [decision record 0001](../internal/adr/0001-one-repository-for-api-and-web-client.md)

**What we decided**: All the code is kept in one repository, in two folders: one for the server part and one for the web pages.

**Why**: The app is small and almost every change touches both parts, so one place keeps changes simple.

**Other options we considered**:

- Two repositories: useful for large teams, but every change would need two linked changes.

**For whoever maintains it**: This counted as much as how well each option fits, because you did not say who will maintain the app (see "Summary").

- One repository: the server part is laid out as the Go language's own documentation shows, and the web pages as the usual setup for React apps, so anyone who knows Go or React finds their way around.
- No other option was compared: two repositories do not fit an app this size (see above).
- Checked on 28 November 2026.

**What it means for you**: You create one repository for the project.

### Decision 0005: How the pages are styled

- Serves: R-10
- Decision record (the full details): [decision record 0005](../internal/adr/0005-css-modules-and-one-token-file.md)

**What we decided**: You left the look to us (decision card 3), so we took today's usual way for this kind of app: each part of a page has its own style rules, and every size, space, and color comes from one short list, written in one place.

**Why**: Every page then uses the same spaces, sizes, and colors, so labels, fields, and buttons line up the same way everywhere (R-10), and nothing extra is added to the app.

**Other options we considered**:

- One style file for all the pages: nothing extra either, but a rule for one page can change another.
- A ready-made styling component (Tailwind CSS): widely used, but one more component to agree to and keep up to date, which three plain pages do not need.

**For whoever maintains it**: This counted as much as how well each option fits, because you did not say who will maintain the app (see "Summary").

- What we chose: part of what the app is already built with (Vite and the browser), and Vite's current documentation describes it, so whoever maintains the pages needs to know only CSS, the standard language for the look of web pages.
- Tailwind CSS: very widely used, used millions of times a week and updated in November 2026, and many people know it; it has its own documentation. Its last major update changed how it is set up and renamed parts of it, so updates can mean work.
- Checked on 28 November 2026.

**What it means for you**: Nothing to do. If you later want the pages to look more worked out, the list of sizes, spaces, and colors is where it changes.

## For information: development tools approved by the stack profile

These tools only check, format, and test the code; none of them is part of the app you receive. The standard setups we follow for the server part and the web pages name them, so they do not need your agreement. We checked each one like any other extra component: it is maintained, the version we use has no known security problems, and its license lets you use it freely.

- ESLint: reads the code of the web pages and points out common mistakes.
- Prettier: keeps the code of the web pages in one consistent layout.
- golangci-lint: reads the code of the server part and points out common mistakes.
- Vitest: runs automatic tests of the parts of the web pages.
- Testing Library and jsdom: let the automatic tests show the web pages and use them the way a person would, without a real browser.
- Playwright: lets our tester open the web pages in a real browser (Chrome's engine), at the size of a phone and of a computer screen, to check how they look and take the screenshots you see at delivery.
