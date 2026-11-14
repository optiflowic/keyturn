# Requirements: task manager

Status: waiting for approval

This status, and "What you need to do", describe this version as it was sent to you. Whether it is approved, and what to do now, is in [approvals.md](approvals.md).

## Summary

A to-do list web app for you and a few friends. Each person signs up, signs in, and keeps a private list of tasks that nobody else can see or change.
You will know it works by following the acceptance guide we send with each delivery.

## What you need to do

> [!IMPORTANT]
> - Read R-1 to R-9 and AC-1 to AC-8, check the priority of each requirement, and approve them, or tell us what to change.

## Background

You want a simple to-do list for yourself and a few friends. You will run it on your own small server. You do not read code, so every check must be something you can do in a web browser.

## Requirements

### R-1: Sign up

Priority: Must

A person creates an account with a username they choose and a password. The password must be at least 12 characters long. One username can have only one account: if a username is taken, the sign-up page says so, and the person chooses another. Usernames are not secret: anyone can find out whether a username is taken. The app asks for no email address.

### R-2: Sign in and sign out

Priority: Must

A person signs in with their username and password, and signs out. Someone who is not signed in sees only the sign-in and sign-up pages.

### R-3: Add a task

Priority: Must

A signed-in person adds a task with a title and an optional due date. The title is shown exactly as typed, as plain text, even if it looks like code.

### R-4: See your tasks

Priority: Must

A signed-in person sees a list of their own tasks, with the title, the due date, and whether each task is done.

### R-5: Change a task

Priority: Must

A signed-in person changes the title or due date of one of their tasks, and marks it as done or not done.

### R-6: Delete a task

Priority: Must

A signed-in person deletes one of their tasks. A deleted task cannot be brought back.

### R-7: Your tasks are private

Priority: Must

A person can see, change, and delete only their own tasks. This holds for every page and every link, including a link to someone else's task.

### R-8: Limit wrong passwords

Priority: Must

After 5 wrong passwords in a row for one account, signing in to that account is blocked for 15 minutes, even with the right password. The person sees a message saying when they can try again.

### R-9: Hide finished tasks

Priority: Nice to have

A signed-in person can choose to hide the tasks that are done, and show them again.

## Acceptance criteria

### AC-1: An account works from sign-up to sign-in

- Covers: R-1, R-2
- When: you sign up with a new username and a password of 12 or more characters, sign out, and sign in again with the same username and password
- Expected result: after signing in, you see your task list. After signing out, opening the task list page shows the sign-in page instead.

### AC-2: A short password is refused

- Covers: R-1
- When: you try to sign up with a password of 11 characters
- Expected result: no account is created, and the page says the password must be at least 12 characters long

### AC-3: A new task appears in your list

- Covers: R-3, R-4
- When: you add a task with the title `<b>Buy milk</b>` and a due date
- Expected result: the task appears in your list with exactly that title, including the `<b>` and `</b>`, and with the due date

### AC-4: Another person cannot see or open your tasks

- Covers: R-7
- When: you copy the link of one of your tasks, sign out, sign in as a second account, look at the task list, and open the copied link
- Expected result: the second account's list does not show your task, and the copied link shows "Task not found"

### AC-5: A task can be changed and marked as done

- Covers: R-5
- When: you change the title of a task, and mark it as done
- Expected result: the list shows the new title, and the task is marked as done. After reloading the page, both changes are still there.

### AC-6: A deleted task is gone

- Covers: R-6
- When: you delete a task and reload the page
- Expected result: the task is no longer in the list

### AC-7: Wrong passwords block signing in for a while

- Covers: R-8
- When: you type a wrong password 5 times in a row for one account, then type the right password
- Expected result: you are not signed in, and the page says when you can try again (15 minutes after the fifth wrong password)

### AC-8: Finished tasks can be hidden

- Covers: R-9
- When: you mark a task as done and choose to hide finished tasks, then choose to show them again
- Expected result: the finished task disappears from the list, and comes back when you show finished tasks again

## Misuse

- Another signed-in person reads, changes, or deletes your tasks, for example by changing a link: prevented by R-7
- Someone who is not signed in opens the task list or a task link: prevented by R-2 and R-7
- Someone guesses a password by trying many passwords: prevented by R-1 (long passwords) and R-8
- Someone puts code in a task title so that it runs in another person's browser: prevented by R-3 (titles are shown as plain text) and R-7 (other people never see your titles)
- Someone finds out whether a username has an account, from the sign-up page, the sign-in page, or the block after wrong passwords: not a problem, because usernames are public on purpose (R-1)

## Out of scope

- Resetting a forgotten password
- Sharing tasks with other people
- Email addresses: the app keeps none and sends no email
- A phone app
- Setting up the server, the domain, or backups (you run it yourself)

## Changelog

| Version | Date | Change |
|---|---|---|
| 1 | 2026-11-08 | First version |
| 2 | 2026-11-08 | R-1, R-2, AC-1: sign up and sign in with a username instead of an email address, so that the app keeps no email address; Misuse and Out of scope updated to match. The PM proposed it. |
