# Evaluation request: task manager

The first evaluation request for keyturn. It is written the way a client would write it: short, in plain words, without technical choices.

## What it checks

- A small web application built end to end in new-project mode, on the first two stack profiles (`go` and `react-spa`, see ADR 0003 in `docs/adr/`).
- Requirements that commonly lead to vulnerabilities: sign-in, and per-user data isolation (one user must never see or change another user's tasks).
- That the PM splits the work when one delivery would need too many "Must check" items.

The worked example in [`example/`](example/) shows every template filled in by hand for this request, as the roles would fill them in. See [`example/README.md`](example/README.md).

## The request

> I want a simple to-do list web app for myself and a few friends.
>
> Each of us signs up with an email address and a password, and then keeps our own list of tasks: add a task with an optional due date, change it, mark it as done, and delete it. It would be nice to hide the tasks that are already done.
>
> My tasks are private. Nobody else using the app, and nobody who is not signed in, should be able to see or change them.
>
> I will run it myself on a small server, so I do not need help with hosting. I do not read code, so tell me how to check that it works.
