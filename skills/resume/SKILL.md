---
name: resume
description: Resume a keyturn task that stopped (usage limit, closed session, crash, a question to the client, the rework limit) from its state file, keyturn/internal/state/<task>.md on the branch task/<task>, in a new session, on another machine, or with another AI tool. With no task named, lists the tasks that can be resumed from every local and remote task branch. Checks the state file with a script first and stops on any problem instead of guessing; never continues past an unanswered decision card or before a usage limit resets.
---

# resume

Continue a stopped task from the step where it stopped, using only what is in the repository. Everything this skill needs is in this file, the script next to it, and the files it names. For background, see "Resuming Work" in keyturn's `docs/DESIGN.md` and ADRs 0009 and 0011; the procedure does not depend on them.

Paths below that start with `scripts/`, `../`, or `../../` are relative to the folder of this `SKILL.md` file. Paths that start with `keyturn/` are in the project's repository.

## Rules

- **Never guess where to continue.** The state file decides. If the script reports any problem, stop and report every problem; do not work out the step from the documents, the commits, or the conversation.
- **Never rely on the previous session.** A step that was stopped in the middle is rerun from its start, from its inputs (the documents and commits on the task branch). Nothing the earlier session was thinking or had not committed counts.
- **No answer is not consent.** Do not continue past a decision card or requirements the client has not answered, not even with the card's recommendation. Work that depends on the answer waits.
- **Not before the reset.** Do not continue a task stopped for a usage limit before the time it records; say when it can continue.
- **Never discard work.** Do not reset, stash, or overwrite uncommitted changes or a branch that has diverged; stop and ask.

## Inputs

- Optional: the name of the task to resume (for example, `delivery-1`). Without it, list the tasks that can be resumed.
- The project's Git repository, with its task branches `task/<task>` (local, or on a remote).
- `../../templates/internal/state.md`: the fields and values of a state file. The script reads it; you need it only to edit the state file in step 5.
- For a task waiting for the client: the decision card or `keyturn/client/approvals.md` named in its "Open questions", and the scripts `../spec/scripts/approval.py` and `../project-config/scripts/project_config.py`.
- To continue: the `deliver` skill, `../deliver/SKILL.md`.

## Outputs

- With no task: the list of tasks that can be resumed, for the person who asked.
- With a task: the state file, updated for the resume and committed on the task branch, and the task continued from its step. Or, when it cannot continue, a short message saying why and, if known, when it can.

## Procedure

The helper script `scripts/task_state.py` checks state files and lists task branches. It needs Python 3.9 or later and Git, and uses only the standard library. Run it from inside the project's repository; below, `task_state.py` means its full path.

- `task_state.py list [--task <task>]` checks the state file on every `task/<task>` branch, local and remote, without checking anything out. For each task that is not done (with `--task`, for that task even when it is done) it prints `<task> (<branch>):` and, indented, its status, current step (with that step's status in the steps table), why it stopped, and when it can continue.
- `task_state.py check <file>` checks one file and prints `ok` and the same lines.
- Both print every problem on its own line, `error: <where>: <problem>` (in `list`, indented under the task's heading), and then exit 1. In the full `list`, exit 1 means that some task has problems; the tasks without problems are still listed. The check never depends on the clock: the same file always gives the same verdict and the same problems. `--now YYYY-MM-DDTHH:MMZ` (default: the current UTC time) only decides whether a reset time has passed.

### 1. Bring the branches up to date

Run `git remote`. If it prints nothing, there is no remote: only this machine's task branches can be seen, so say so when you report. Otherwise run `git fetch --all --prune`. If that fails (for example, no network), say that tasks pushed from another machine may be missing or out of date, and go on with what is there.

### 2. With no task named: list the tasks, then stop

Run `task_state.py list`. Tell the person, in their language, which tasks can continue now, which are waiting and for what, and which have problems (the `error:` lines under a task's heading), and that done tasks are left out. Ask which one to resume, and stop. If it prints `no tasks to resume`, say so; a new task is started with the `deliver` skill.

### 3. With a task named: check it and check out its branch

1. Run `task_state.py list --task <task>`. Look only at this output; other tasks do not matter here.
   - Any `error:` line (indented under the task's heading): stop. Show the person every line, and say the task cannot be resumed until they are fixed. Do not fix the state file by guessing: it is fixed by hand, to what the task branch shows, by someone who can tell, and checked again. The lines you may see besides problems in the file itself:
     - `error: task/<task>: has no local or remote branch`: there is no such task.
     - `error: task/<task>: should not have diverged: <branches>; ...`: the local and remote branches both have commits the other lacks. Ask the person how to merge them.
     - `error: <branch>:keyturn/internal/state/<task>.md: is missing`: where the task stopped cannot be told; do not work it out from the outputs.
   - `status: done`: there is nothing to resume. Say so, and stop.
2. Run `git status --porcelain`. If it prints anything, stop and ask the person what to do with those changes; never discard them.
3. Run `git switch task/<task>` (this creates the local branch from the remote one when only the remote one exists). If `list` printed `note: task/<task> is behind <remote>/task/<task>; fast-forward it before resuming`, run `git merge --ff-only <remote>/task/<task>`.

### 4. Decide whether it can continue now

Use the lines `list` printed.

- **`status: running`**: the session that ran it ended without recording a stop (a crash or a closed terminal), or it is still running somewhere else. Ask the person who asked you to resume it to confirm that no other session is working on this task, and go on only after they confirm. Their confirmation is recorded in the History line in step 5.
- Then **`can continue:`**:
  - `now`, or `not applicable` with status `running`: go on.
  - `after <time>`: if the line ends with `not yet (now ...)`, stop and tell the person the task can continue after `<time>` (UTC). If it ends with `the time has passed`, go on. This skill does not check the current usage itself; `deliver` checks it before it starts each step and stops again if the limit is still near.
  - `when the client approves: requirements version <n>: only once the client's answer is recorded` or `when the client answers: decision card <n>: only once the client's answer is recorded`: check whether the client has answered, as below. If they have, go on. If not, only the work that depends on the answer waits: the "Blocks:" part of that item in "Open questions" says which steps. If it blocks the current step (for example, "design and every later step" when the current step is design), stop and say what is waiting for the client. If it does not, go on: the item stays in "Open questions", and `deliver` stops again before a step it blocks.
  - `when the maintainer decides: <what>: only once the maintainer has decided`: stop and ask the maintainer. Go on only after they have decided, and follow their decision.
- Whatever "Can continue" says, do not run the current step while any unanswered item in "Open questions" lists it under "Blocks:".

How to tell whether the client has answered:

- **Requirements version `<n>`**: run `project_config.py get english_only` and, if it prints `true`, `project_config.py get client_language`. Then run `approval.py status`, adding `--lang <client_language>` when `english_only` is `true`. The client has approved only if its first line is `version <n>: current, answer: <answer>` with that same `<n>`, and `<answer>` is exactly `approved` (or, when `approvals.md` is written in another language, that one word in its language) and nothing else. `waiting`, an empty answer, "not approved", and an approval with conditions are not approvals. If the only errors it prints are about the kept copy of the translation, the approval still counts; tell the person, because the `spec` skill needs to know. When you are unsure what an answer means, ask whoever runs `spec`; do not decide it.
- **Decision card `<n>`**: open the card linked in "Open questions". The client has answered only if its `Status:` line is `answered` and, under "Your answer", the `Answer:` and `Date:` lines are filled in: not empty, and no longer the template's text in angle brackets (`<option, and any comment>`, `<YYYY-MM-DD>`).
- **Before writing anything**, check that the `deliver` skill (`../deliver/SKILL.md`) is available. If it is not, stop and report it: `resume` does not run the pipeline itself, and recording a resume that nothing runs would leave the task marked `running`.

### 5. Record the resume

Edit `keyturn/internal/state/<task>.md`, keeping to the fields and values of `../../templates/internal/state.md`:

- `Status: running`, `Stopped because: none`, `Can continue: not applicable`.
- `Updated:` the current UTC time, rounded down to the minute, in the form `YYYY-MM-DDTHH:MMZ`. Take it once (for example, with `date -u +%Y-%m-%dT%H:%MZ`) and use the same time in the History line below; if you pass `--now` to the script, pass that time too.
- Leave the steps table as it is, including the current step's row when it says `in progress`: the step is rerun from its start in step 6, and `deliver` updates the row when it runs it.
- In "Open questions", remove the items that were answered or approved, and keep the ones still waiting; write `None.` when nothing is left.
- In "Summary", say in one or two lines that the task was resumed, naming the step by its name in the steps table (for example, "Resumed in the implement step after the usage limit reset."). Like the whole state file, it is written in English, in plain words (the template asks for lines a client could follow).
- In "History", add one line at the end, and never change the earlier lines: ``- <time>: resumed: in <step>, from commit `<hash>` ``, where `<hash>` is the short hash that `git rev-parse --short HEAD` prints before you commit (usually 7 characters). The check does not read hashes in History; in the steps table it accepts 7 to 40 hexadecimal characters in backticks. For a task that was `running`, add ` (the earlier session ended without recording a stop; confirmed that no other session runs it)`.

Run `task_state.py check keyturn/internal/state/<task>.md` until it prints `ok`. Commit only that file on the task branch, with the message `chore(state): resume <task> in <step>` (for example, `chore(state): resume delivery-1 in implement`).

### 6. Continue from the step

The step to continue is the **current step**. Each step in the steps table is named after the keyturn skill that runs it: `spec`, `design`, `conventions`, `implement`, `qa`, `security-review`, `review`, and `deliver` (the last step, which writes the acceptance guide and the delivery report).

- Whether the step's row says `in progress` (it stopped in the middle) or `not started`, run the step from its start, from its inputs. Its earlier partial outputs are written again, not continued.
- Steps marked `done` or `skipped` are not run again.
- Continue with the `deliver` skill from that step: follow its procedure from that step on. `deliver` runs the steps and the gates between them, and keeps the state file current at every step boundary and when the task stops again.

## When inputs are missing

- **No Git repository**: stop and report it; tasks are found only from their branches.
- **No task branches**: say there are no tasks to resume.
- **A task branch without a state file**: stop and report it (step 3).
- **No template** (the script reports that `../../templates/internal/state.md` cannot be read): stop and report it; the file cannot be checked without it.
- **A decision card or `approvals.md` named in the state file is missing**: stop and report it; the client's answer cannot be confirmed.
- **No `deliver` skill**: stop before recording the resume (step 4).

## Notes

- The script reads the allowed fields, values, sections, and steps from the template at every run. If the template changes in a way the script does not understand, the script reports it; update the script and its tests with the template.
- Besides the format, the check makes sure the file says where to continue without a guess: the title and `Branch:` name the task, the current step is the first step that is neither done nor skipped, a stopped task says why, a usage-limit stop says when the limit resets, and a task waiting for the client lists what it waits for in "Open questions", where "Blocks:" names only steps of the template (or "every later step" right after one) and requirements (`R-n`).
- The check does not look up commit hashes in Git: a hash in the steps table or History must have the right form, but is not checked to exist.
