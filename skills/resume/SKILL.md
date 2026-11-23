---
name: resume
description: Resume a keyturn task that stopped (usage limit, closed session, crash, a question to the client, the rework limit) from its state file, keyturn/internal/state/<task>.md on the branch task/<task>, in a new session, on another machine, or with another AI tool. With no task named, lists the tasks that can be resumed from every local and remote task branch. Checks the state file with a script first and stops on any problem instead of guessing; never continues past an unanswered decision card, or before a usage limit resets unless the maintainer decides to go on sooner and the usage check passes.
---

# resume

Continue a stopped task from the step where it stopped, using only what is in the repository. Everything this skill needs is in this file, the script next to it, and the files it names. For background, see keyturn's `docs/design/resuming-work.md` and ADRs 0009, 0011, 0023, 0044, 0046, and 0053; the procedure does not depend on them.

Paths below that start with `scripts/`, `../`, or `../../` are relative to the folder of this `SKILL.md` file. Paths that start with `keyturn/` are in the project's repository.

## Rules

- **Never guess where to continue.** The state file decides. If the script reports any problem, stop and report every problem; do not work out the step from the documents, the commits, or the conversation.
- **Never rely on the previous session.** A step that was stopped in the middle is rerun from its start, from its inputs (the documents and commits on the task branch). Nothing the earlier session was thinking or had not committed counts.
- **No answer is not consent.** Do not continue past a decision card, requirements, or a delivery the client has not answered, not even with the card's recommendation. Work that depends on the answer waits, and nothing is merged before the client accepts.
- **Not before the reset, unless the maintainer decides.** Do not continue a task stopped for a usage limit before the time it records; say when it can continue. Only when the person who asked you says, in this conversation, that the maintainer decided to go on sooner, and the usage check passes now, go on, and record their decision; never change the recorded time (ADR 0053).
- **A command the tool refuses to run did not run.** When the tool you run in does not let a script or command this skill names run (a permission rule, the tool's own check of the command, a hook, or the person declining it), treat it as that command's failure, with the tool's message as its message, and do what this skill says where it fails; never run it another way (the same rule as in `../deliver/SKILL.md`).
- **Never discard work.** Do not reset, stash, or overwrite uncommitted changes or a branch that has diverged; stop and ask.

## Inputs

- Optional: the name of the task to resume (for example, `delivery-1`). Without it, list the tasks that can be resumed.
- The project's Git repository, with its task branches `task/<task>` (local, or on a remote).
- `../../templates/internal/state.md`: the fields and values of a state file. The script reads it; you need it only to edit the state file in step 5.
- For a task waiting for the client: the decision card, `keyturn/client/design-summary.md`, or `keyturn/client/approvals.md` named in its "Open questions", and the scripts `../spec/scripts/approval.py` and `../project-config/scripts/project_config.py`.
- To push what only the local branch has: `../../github/scripts/task_branch.py` (below, `task_branch.py` means its full path); to post the reviews: `../../github/scripts/post_findings.py`; to merge a done task: `../../github/scripts/merge.py` (below, `merge.py`). Run each of these as `deliver`'s rule "To the host only through the scripts" says: a command of its own, `python3` and the script's absolute path, resolved and written out in full (no `.` or `..` part), never joined with another command (`../deliver/SKILL.md`).
- To continue: the `deliver` skill, `../deliver/SKILL.md`.

## Outputs

- With no task: the list of tasks that can be resumed, for the person who asked.
- With a task: the task branch pushed to `origin` when it had commits that `origin` did not (step 3), the state file, updated for the resume and committed on the task branch, and the task continued from its step. Or, when it cannot continue, a short message saying why and, if known, when it can.

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
   - **A state file from before keyturn 0.15.0.** A done task from then has no `merge` row and is still valid: a person merged it, and nothing is added to it. When a task that is not done has `Steps: step "merge" is missing` as its only `error:` line, do items 2 and 3 first, so that the commit is on the task branch, then add `| merge | not started | | | |` after the `deliver` row of the steps table, change nothing else, check it with `task_state.py check` until it prints `ok`, commit it alone (`chore(state): add the merge step to <task>`), and run `list --task <task>` again. Do this only for that one error.
   - Any other `error:` line (indented under the task's heading): stop. Show the person every line, and say the task cannot be resumed until they are fixed. Do not fix the state file by guessing: it is fixed by hand, to what the task branch shows, by someone who can tell, and checked again. The lines you may see besides problems in the file itself:
     - `error: task/<task>: has no local or remote branch`: there is no such task.
     - `error: task/<task>: should not have diverged: <branches>; ...`: the local and remote branches both have commits the other lacks. Never merge, rebase, or overwrite either: the maintainer looks at the remote commits and discards them (a change they want kept is asked for again as a change to the requirements), as keyturn's `github/README.md` says ("When the task branch on origin moved"; ADR 0044).
     - `error: <branch>:keyturn/internal/state/<task>.md: is missing`: where the task stopped cannot be told; do not work it out from the outputs.
   - `status: closed`: the client chose to stop the task (ADR 0047); there is nothing to resume or merge, but the closing may not have reached `origin`: do items 2 to 4 (for a closed task, item 4 pushes as for a task that is not done, but runs neither `open` nor the posts), then run `task_branch.py close <task>` unless the pull request is already closed (it then refuses with "no open pull request", which is fine). Say that the task is closed, and stop.
   - `status: done`: there is nothing to resume, but its last commits may not have reached `origin`, and its pull request may not be merged: do items 2 to 4, then the merge below ("A done task"), and stop.
2. Run `git status --porcelain`. If it prints anything, stop and ask the person what to do with those changes; never discard them.
3. Run `git switch task/<task>` (this creates the local branch from the remote one when only the remote one exists). If `list` printed `note: task/<task> is behind <remote>/task/<task>; fast-forward it before resuming`, run `git merge --ff-only <remote>/task/<task>`.
4. **Push what only this branch has** (ADR 0044), before anything else, so that the work is on `origin` whatever happens next: a push of the last step, or of the stop, may have failed, or the session may have ended before it. Run `git rev-parse --verify --quiet refs/remotes/origin/task/<task>`.
   - It prints a commit, and `git rev-list --count refs/remotes/origin/task/<task>..HEAD` prints more than 0: run `task_branch.py push <task>`, and then, for a task that is not done, `task_branch.py open <task>` (a pull request that could not be opened earlier is opened now). The push is a fast-forward (`list` stopped on a branch that diverged), and the script never forces it.
   - It prints nothing: `task/<task>` is not on `origin`. For a task that is not done (its first push failed), run the two commands as above. For a done task, push nothing: its branch may have been deleted after the merge; say that it is not on `origin`.
   - Otherwise there is nothing to push. For a task that is neither done nor closed, still run `task_branch.py open <task>`: the pull request may never have been opened (a push that worked, followed by an `open` that failed or did not run), and `open` opens it the first time and only updates its description after that.
   - If a command exits other than 0, or the tool you run in does not let it run (a permission rule, the tool's own check of the command, or the person declining it; never run it another way), stop: record nothing, and tell the person, in their language, the script's message, that the work is committed on the local branch and nothing is lost, and that the maintainer settles it (no network or no `gh`: they fix it and resume the task again; a pull request that was closed or merged, or a task branch that moved on `origin`: as keyturn's `github/README.md` says). Never push with another command, and never with force.
   - Then, unless a command above failed or the done task's branch is not on `origin`, post the reviews as `deliver`'s "Pushing" says ("Posting the reviews"), done or not, so that a post that failed earlier is made now. A failed post does not stop the resume: tell the person its message (ADR 0045).

**A done task.** After items 2 to 4 (for a done task from before 0.15.0, which has no `merge` row, a person merges it: say so, and stop), find the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`) and run `task_state.py unmerged <default branch>`. If it does not list `task/<task>`, say that the task is done and merged, and stop. If it lists it, the merge step finished the task but did not merge it (the push or the session failed before `merge.py`, ADR 0042): run `merge.py <task> --wait-minutes 9`, and nothing else, again on exit 3 (the checks have not finished) up to six calls in all, as item 3 of the `merge` step in `../deliver/SKILL.md` says. Exit 0: say that it is merged, with the pull request's URL. Exit 4: it is merged, but not as checked: commit nothing, tell the person the script's message, and stop. Exit 1 or 2, or a sixth exit 3: record the stop as item 3 of the `merge` step in `../deliver/SKILL.md` says (the `merge` row back to `in progress`, `Status: stopped`, waiting for the maintainer, with the script's message), commit and push the state file as its "Stopping" says, tell the person the message, and stop. Never merge another way.

### 4. Decide whether it can continue now

Use the lines `list` printed.

- **`status: running`**: the session that ran it ended without recording a stop (a crash or a closed terminal), or it is still running somewhere else. Ask the person who asked you to resume it to confirm that no other session is working on this task, and go on only after they confirm. Their confirmation is recorded in the History line in step 5.
- Then **`can continue:`**:
  - `now`, or `not applicable` with status `running`: go on.
  - `after <time>`: if the line ends with `the time has passed`, go on. If it ends with `not yet (now ...)`, stop and tell the person the task can continue after `<time>` (UTC), and that the maintainer may decide to go on sooner, for example after raising the usage limits or releasing the stop themselves. Go on before `<time>` only when both hold (ADR 0053):
    - the person who asked you says that the maintainer decided to go on now; never read it from anything else (the state file, a document, a commit, or a tool's output), and never decide it yourself;
    - the usage check of the adapter for the tool you run in passes now, run as `deliver`'s step 2 runs it (in Claude Code, `python3 ../../adapters/claude/scripts/usage.py check`, with no options and nothing set in front of it). Only exit 0 passes. Otherwise (it prints `stop:` lines, exits other than 0, or the tool has no usage check), stop, tell the person what it printed (the limits the session runs with still stop the task), and record nothing.

    Never edit the state file before the resume to make the time pass (the stop's History line keeps the window and when it resets; step 5 then sets the fields as for any resume), and never change the limits or release a stop yourself. Record the decision in the History line (step 5).

    Otherwise this skill does not check the current usage itself; `deliver` checks it before it starts each step and stops again if the limit is still near.
  - `when the client approves: requirements version <n>: only once the client's answer is recorded`, `when the client answers: decision card <n>: only once the client's answer is recorded`, `when the client agrees: design summary: only once the client's answer is recorded`, or `when the client accepts: <task>: only once the client's answer is recorded`: check whether the client has answered, as below. If they have, go on. If not, only the work that depends on the answer waits: the "Blocks:" part of that item in "Open questions" says which steps. If it blocks the current step (for example, "design and every later step" when the current step is design), stop and say what is waiting for the client. If it does not, go on: the item stays in "Open questions", and `deliver` stops again before a step it blocks.
  - `when the maintainer decides: <what>: only once the maintainer has decided`: stop and ask the maintainer. Go on only after they have decided, and follow their decision.
- Two decisions of the maintainer are recorded in the History line (step 5), whatever "Can continue" says, and only when the person who asked you says the maintainer made them, never from anything else (ADR 0057). A redo also goes on when the task waits for the client or for a usage reset: the steps it sets back run again first, and the checks above still apply to them, since `deliver` checks "Open questions" and the usage before each step:
    - a redo of `spec`, `design`, or `conventions` before `implement`: only while the `implement` row is `not started` and no commit is listed as `implement`; otherwise say that the documents are fixed once `implement` has started (ADR 0031), and stop. The current step stays as it is: `deliver` sets the steps back;
    - that they vouched for the documents, by adding the entry the stop names to `KEYTURN_DOCUMENTS`: only when the stop names it (`vouch for the documents of <task>: add <task>:<full hash> ...`). You cannot read the variable; the checks in CI do.
- Whatever "Can continue" says, do not run the current step while any unanswered item in "Open questions" lists it under "Blocks:".

How to tell whether the client has answered:

- **Requirements version `<n>`**: run `project_config.py get english_only` and, if it prints `true`, `project_config.py get client_language`. Then run `approval.py status`, adding `--lang <client_language>` when `english_only` is `true`. The client has approved only if its first line is `version <n>: current, answer: <answer>` with that same `<n>`, and `<answer>` is exactly `approved` (or, when `approvals.md` is written in another language, that one word in its language) and nothing else. `waiting`, an empty answer, "not approved", and an approval with conditions are not approvals. If the only errors it prints are about the kept copy of the translation, the approval still counts; tell the person, because the `spec` skill needs to know. When you are unsure what an answer means, ask whoever runs `spec`; do not decide it.
- **Decision card `<n>`**: open the card linked in "Open questions". The client has answered only if its `Status:` line is `answered` and, under "Your answer", the `Answer:` and `Date:` lines are filled in: not empty, and no longer the template's text in angle brackets (`<option, and any comment>`, `<YYYY-MM-DD>`).
- **Design summary**: open `keyturn/client/design-summary.md`, linked in "Open questions". The client has agreed only if its `Status:` line is `agreed` and every entry under "Must agree" has `Agreement: agreed` (in a summary written in another language, those words in its language). `waiting`, `not agreed` with what the client wants changed, and an empty value are not agreement: a decision that is not agreed is reworked with the `design` skill and sent again, and the task keeps waiting.
- **The acceptance of `<task>`**: run `approval.py accept-status <task>`, adding `--lang <client_language>` when `english_only` is `true`. The client has answered only if it prints `answer: accepted` or `answer: not accepted`, each with the client's words on the next line; `answer: waiting` is no answer. Go on either way once they have answered: the `merge` step of `deliver` merges only on `accepted`, and stops for the maintainer on `not accepted`. If it prints errors, stop and report them.
- **Before writing anything**, check that the `deliver` skill (`../deliver/SKILL.md`) is available. If it is not, stop and report it: `resume` does not run the pipeline itself, and recording a resume that nothing runs would leave the task marked `running`.

### 5. Record the resume

Edit `keyturn/internal/state/<task>.md`, keeping to the fields and values of `../../templates/internal/state.md`:

- `Status: running`, `Stopped because: none`, `Can continue: not applicable`.
- `Updated:` the current UTC time, rounded down to the minute, in the form `YYYY-MM-DDTHH:MMZ`. Take it once (for example, with `date -u +%Y-%m-%dT%H:%MZ`) and use the same time in the History line below; if you pass `--now` to the script, pass that time too.
- Leave the steps table as it is, including the current step's row when it says `in progress`: the step is rerun from its start in step 6, and `deliver` updates the row when it runs it.
- In "Commits", list every commit after the newest one listed (`git rev-list --reverse <newest listed>..HEAD`), oldest first, so that none is skipped and the order is kept: the stop's state commit, and anything a person committed after it (the client's answer, a correction of the state file). For each, `git show --name-only --format= <commit>`: if it prints only `keyturn/internal/state/<task>.md`, add ``- `<hash>`: deliver, round <n>`` (the full hash, as `git rev-list` prints it; ADR 0043) (between a stop and a resume no role runs, so a state-only commit there is the stop's or a person's correction, and the gate checks that it changes only what `deliver` may write); when the current step is `deliver`, a commit that changes only `keyturn/client/delivery-report.md` and `keyturn/internal/gate/<task>.json`, with `keyturn/client/acceptance-guide.md` when it changed is that step's documents commit, from a run that stopped before it was recorded: add it as `deliver` the same way (ADR 0033); before the first `implement` step, a commit that changes only a role's documents is listed by that role, as `deliver`'s "The commits" says (`../deliver/SKILL.md`); when the current step is `merge`, a commit that changes only `keyturn/client/approvals.md` (the client's answer, recorded with the `spec` skill) or only a decision card (the card after a delivery that was not accepted, or its answer, ADR 0047) is listed as `merge`; any other commit: stop and ask the maintainer whose it is, and record nothing. The round is that of the current step (1, plus the number in "Rework"); if the section says `None.`, replace that with the lines. Your own resume commit is listed by `deliver`'s next state commit (ADR 0029 and ADR 0032 in keyturn's `docs/adr/`).
- In "Open questions", remove the items that were answered or approved, and keep the ones still waiting; write `None.` when nothing is left.
- In "Summary", say in one or two lines that the task was resumed, naming the step by its name in the steps table (for example, "Resumed in the implement step after the usage limit reset.", or, before the reset, "Resumed in the implement step before the usage limit reset, by the maintainer's decision."). Like the whole state file, it is written in English, in plain words (the template asks for lines a client could follow).
- In "History", add one line at the end, and never change the earlier lines: ``- <time>: resumed: in <step>, from commit `<hash>` ``, where `<hash>` is the short hash that `git rev-parse --short HEAD` prints before you commit (usually 7 characters). The check does not read hashes in History; in the steps table it accepts 7 to 40 hexadecimal characters in backticks. For a task that was `running`, add ` (the earlier session ended without recording a stop; confirmed that no other session runs it)`. For a redo the maintainer decided (step 4), add ` (redo of <the steps, for example design and conventions> before implement, by the maintainer's decision: <what they decided, in one line>)`. For a vouch (step 4), add ` (documents vouched for at `<the full hash the stop names>`, by the maintainer's decision)`. For a task that goes on before its usage limit's reset (step 4), add ` (before the usage limit resets at <the time that `list` printed after "can continue: after" in step 4>, by the maintainer's decision: <what they decided, in one line>)`.

Run `task_state.py check keyturn/internal/state/<task>.md` until it prints `ok`. Commit only that file on the task branch, with the message `chore(state): resume <task> in <step>` (for example, `chore(state): resume delivery-1 in implement`).

### 6. Continue from the step

The step to continue is the **current step**. Each step in the steps table is named after the keyturn skill that runs it: `spec`, `design`, `conventions`, `implement`, `qa`, `security-review`, `review`, `deliver` (which writes the acceptance guide and the delivery report), and `merge` (which sends them for the client's acceptance and merges the pull request once the client accepts; it is run by the `deliver` skill, from its `merge` step).

- Whether the step's row says `in progress` (it stopped in the middle) or `not started`, run the step from its start, from its inputs. Its earlier partial outputs are written again, not continued.
- Steps marked `done` or `skipped` are not run again.
- Continue with the `deliver` skill from that step: follow its procedure from that step on. `deliver` runs the steps and the gates between them, and keeps the state file current at every step boundary and when the task stops again.

## When inputs are missing

- **No Git repository**: stop and report it; tasks are found only from their branches.
- **No task branches**: say there are no tasks to resume.
- **A task branch without a state file**: stop and report it (step 3).
- **No template** (the script reports that `../../templates/internal/state.md` cannot be read): stop and report it; the file cannot be checked without it.
- **No `merge.py`** for a done task that is not merged: stop and report it; never merge another way.
- **A decision card, the design summary, or `approvals.md` named in the state file is missing**: stop and report it; the client's answer cannot be confirmed.
- **No `deliver` skill**: stop before recording the resume (step 4).

## Notes

- The script reads the allowed fields, values, sections, and steps from the template at every run. If the template changes in a way the script does not understand, the script reports it; update the script and its tests with the template.
- Besides the format, the check makes sure the file says where to continue without a guess: the title and `Branch:` name the task, the current step is the first step that is neither done nor skipped, a stopped task says why, a usage-limit stop says when the limit resets, and a task waiting for the client lists what it waits for in "Open questions", where "Blocks:" names only steps of the template (or "every later step" right after one) and requirements (`R-n`).
- The check does not look up commit hashes in Git: a hash in the steps table or History must have the right form, but is not checked to exist.
