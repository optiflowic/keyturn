---
name: resume
description: Resume a keyturn task that stopped (usage limit, closed session, crash, a question to the client, the rework limit) from its state file, keyturn/internal/state/<task>.md on the branch task/<task>, in a new session, on another machine, or with another AI tool. With no task named, lists the tasks that can be resumed from every local and remote task branch. Checks the state file with a script first and stops on any problem instead of guessing; never continues past an unanswered decision card or before a usage limit resets.
---

# resume

Continue a stopped task from the step where it stopped, using only what is in the repository. See "Resuming Work" in keyturn's `docs/DESIGN.md`, and ADR 0011 (the state file) and ADR 0009 (no answer is not consent) in keyturn's `docs/adr/`.

## Rules

- **Never guess where to continue.** The state file decides. If the check below reports any problem, stop and report every problem; do not work out the step from the documents, the commits, or the conversation.
- **Never rely on the previous session.** A step that was stopped in the middle is rerun from its start, from its inputs (the documents and commits on the task branch). Nothing the earlier session was thinking or had not committed counts.
- **No answer is not consent.** Do not continue past a decision card or requirements the client has not answered, not even with the card's recommendation.
- **Not before the reset.** Do not continue a task stopped for a usage limit before the time it records; say when it can continue.
- **Never discard work.** Do not reset, stash, or overwrite uncommitted changes or a branch that has diverged; stop and ask.

## Inputs

- Optional: the name of the task to resume (for example, `delivery-1`). Without it, list the tasks that can be resumed.
- The project's Git repository, with its task branches `task/<task>` (local, or on a remote).
- `templates/internal/state.md` in keyturn (two folders above this skill's folder), not in the project: the fields and values of a state file. The script reads it.

## Outputs

- With no task: the list of tasks that can be resumed, for the person who asked.
- With a task: the state file, updated for the resume and committed on the task branch, and the task continued from its step. Or, when it cannot continue yet, a short message saying why and when it can.

## Procedure

The helper script `scripts/task_state.py` (in this skill's folder) checks state files and lists task branches. It needs Python 3.9 or later and Git, and uses only the standard library. Run it from inside the project's repository. Below, `task_state.py` means the script's full path. The check never depends on the clock: the same file always gives the same verdict and the same problems. `--now` (default: the current UTC time) only decides whether a reset time has passed.

### 1. Bring the branches up to date

Run `git fetch --all --prune`, so that tasks pushed from another machine are seen. If it fails (no network, no remote), say that the list may be out of date, and go on with what is there.

### 2. With no task named: list the tasks

Run `task_state.py list`. For every local and remote branch `task/<task>`, it checks the state file on that branch (without checking it out) and prints the tasks that are not done: where each stopped, why, and when it can continue. Done tasks are left out. A task whose file has problems is printed with them.

Tell the person, in their language, which tasks can be resumed now, which are waiting and for what, and which have problems. Ask which one to resume, and stop. If it prints `no tasks to resume`, say so; a new task is started with the `deliver` skill.

### 3. With a task named: check out its branch

1. Run `task_state.py list` and find the task. If it is not listed, it has no task branch or is done: say which, and stop. If it is listed with problems, stop and report them (see step 4).
2. Run `git status --porcelain`. If anything is uncommitted, stop and ask the person what to do with it; never discard it.
3. Switch to `task/<task>` (`git switch task/<task>`; this creates it from the remote branch when only the remote one exists). If `list` printed a note that the local branch is behind a remote branch, fast-forward it (`git merge --ff-only <remote branch>`). If it reported that the branches have diverged, stop and ask: the newest state cannot be chosen.

### 4. Check the state file

Run `task_state.py check keyturn/internal/state/<task>.md`.

- **Problems** (exit code 1): stop. Show the person every line it printed, and say that the task cannot be resumed until the state file is fixed. Do not fix it yourself by guessing; it is fixed by hand, to what the task branch shows, by whoever can tell, and then checked again.
- **`ok`**: it prints the task's status, current step (with that step's status in the steps table), why it stopped, and when it can continue. Go on.

### 5. Decide whether it can continue now

- **Status `done`**: there is nothing to resume. Say so, and stop.
- **Status `running`**: the session that ran it ended without recording a stop (a crash or a closed terminal), or it is still running somewhere else. Ask the person to confirm that no other session is working on this task, and go on only after they confirm.
- Then look at **Can continue**:
  - `now`: go on.
  - `after <time>`: if the script says `not yet`, stop and tell the person when the task can continue, in UTC and in their local time if you know it. The usage is checked again before every step.
  - `when the client approves: requirements version <n>`: go on only if `approval.py status` of the `spec` skill reports that version as `current` with an approved answer. Otherwise stop, and say what is waiting for the client.
  - `when the client answers: decision card <n>`: open the card linked in "Open questions". Go on only if its status is `answered` and the answer is recorded in it. Otherwise stop, and say what is waiting for the client.
  - `when the maintainer decides: <what>`: stop and ask the maintainer. Go on only after they have decided, and follow their decision.
  - `not applicable` (with status `running`): go on.
- Even when it can continue, do not run a step that a waiting item in "Open questions" blocks.

### 6. Record the resume

Edit the state file, keeping to the fields and values of `templates/internal/state.md`:

- `Status: running`, `Stopped because: none`, `Can continue: not applicable`, `Updated:` the current UTC time (`YYYY-MM-DDTHH:MMZ`).
- In "Open questions", remove the items that were answered or approved; write `None.` when nothing is left.
- In "Summary", say in one or two lines that the task was resumed and in which step.
- In "History", add one line at the end, and never change the earlier lines: ``- <time>: resumed: in <step>, from commit `<short hash of HEAD>` `` (HEAD before this commit).

Run `task_state.py check` again until it prints `ok`, and commit the file on the task branch.

### 7. Continue from the step

The step to continue is the **Current step**. Each step in the steps table is named after the keyturn skill that runs it: `spec`, `design`, `conventions`, `implement`, `qa`, `security-review`, `review`, and `deliver` (the last step, which writes the acceptance guide and the delivery report).

- Whether the step's row says `in progress` (it stopped in the middle) or `not started`, run the step from its start, from its inputs. Its earlier partial outputs are written again, not continued.
- Steps marked `done` or `skipped` are not run again.
- Continue with the `deliver` skill from that step: follow its procedure from that step on. `deliver` runs the steps, the gates between them, and keeps the state file current at every step boundary and when the task stops again. If the `deliver` skill is not available, stop and report it; `resume` does not run the pipeline itself.

## When inputs are missing

- **No Git repository**: stop and report it; tasks are found only from their branches.
- **No task branches**: say there are no tasks to resume.
- **A task branch without a state file**: stop and report it (`list` shows it as a problem). Where the task stopped cannot be told without the file; do not work it out from the outputs.
- **No template** (the script reports it cannot read `templates/internal/state.md`): stop and report it; the file cannot be checked without it.
- **A decision card or `approvals.md` named in the state file is missing**: stop and report it; the client's answer cannot be confirmed.

## Notes

- The script reads the allowed fields, values, sections, and steps from `templates/internal/state.md` at every run, so a change to the template is checked at once. If the template changes in a way the script does not understand, the script reports it; update the script and its tests with the template.
- Besides the format, the check makes sure the file says where to continue without a guess: the current step is the first step that is neither done nor skipped, a stopped task says why, a usage-limit stop says when the limit resets, and a task waiting for the client lists what it waits for in "Open questions".
