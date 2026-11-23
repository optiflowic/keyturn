# 0052. The recommended permission rules allow keyturn's GitHub scripts by their full path, and deny edits to the plugin's folder

- Status: accepted
- Date: 2026-11-23

## Context

`deliver` reaches GitHub only through keyturn's scripts: `task_branch.py` pushes the task branch and opens, updates, marks ready, and closes its pull request, `post_findings.py` posts the reviews, and `merge.py` merges ([ADR 0041](0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0045](0045-deliver-posts-the-review-reports-on-the-pull-request.md), [ADR 0046](0046-acceptance-record-conditions-check-and-merge-script.md)). The recommended permission rules (`adapters/claude/permission-settings.json`) deny the plain `git push` and `gh` commands those scripts replace, and allow nothing.

In the end-to-end rehearsal, Claude Code's auto mode denied `task_branch.py open <task>` as `[Undermining Oversight]`, and the task stopped at its first push (#155). Its classifier judges a command that it does not find in an allow rule; a script that pushes and opens pull requests reads to it as an outward-facing action. With the maintainer's allow rules for the three scripts added by hand, the same commands ran.

What constrains the answer:

- In auto mode, a command that matches an allow rule runs without the classifier. On entering auto mode, Claude Code drops broad allow rules that grant arbitrary code execution (for example, a wildcarded interpreter such as `Bash(python*)`); a rule that names one script by its path, with a wildcard only for its arguments, is not one of those.
- A `Bash` rule matches the command's text. A compound command (`a && b`, `a; b`) runs without a prompt only when each part is allowed, and a deny rule matches any part.
- An allow rule for a script is as safe as the script. An agent that can change the script can then run anything under that rule, without the classifier.
- `Edit` and `Write` deny rules stop the file tools, and Claude Code also applies them to the targets of redirections and of the file commands it recognizes (such as `sed` and `tee`). A program that opens a file itself (`cp`, `mv`, `python3 -c ...`, a script the agent writes) is not checked against them; such a command matches no allow rule, so it still goes to the classifier in auto mode, or to a prompt in the other modes.
- Path rules: `//path` is an absolute path; `/path` is relative to the settings file. The plugin's folder is where the person loads it from: a folder given with `--plugin-dir`, or the installed copy under `~/.claude/plugins/`, whose path changes with each version.
- Without the sandbox (#119), the permission rules stop the plain commands, not every way around them. What a changed script could do on GitHub is still guarded by the other two layers of [ADR 0048](0048-default-branch-guarded-in-three-layers.md): the detecting workflow, which runs keyturn at the commit the person fixed (`KEYTURN_COMMIT`), not the agents' copy, and branch protection where the plan has it.

## Options considered

1. **No allow rules; the person approves each script call.** Nothing is trusted that the person has not seen, but auto mode stops at every push, and an unattended run cannot get past its first step.
2. **Allow the three scripts by their full path, and deny `Edit` and `Write` under the plugin's folder.** The scripts run in auto mode. The file tools, and the shell writes Claude Code recognizes, cannot change them. A shell command that writes there another way is left to the classifier or a prompt, as every command that matches no allow rule is.
3. **Option 2, plus deny rules for the shell commands that could write under the plugin's folder** (`cp`, `mv`, `install`, `git -C <plugin folder>`, ...). Each rule stops one way of writing, the list can never be complete (`python3 -c` alone reaches every file), and it adds to the deny list rules that a person would have to fill in with the folder's path, for no layer that the classifier and the detecting workflow do not already give.
4. **A hook in the plugin that allows the scripts.** Needs no path filled in, but the plugin's hooks are for safety guardrails only ("Gates" in `docs/design/architecture.md`), and an allowing hook is not one.

## Decision

Option 2. `adapters/claude/permission-settings.json` gets:

- `allow`: `Bash(python3 <path to the keyturn plugin>/github/scripts/<script> *)` for `task_branch.py`, `post_findings.py`, and `merge.py`;
- in `deny`: `Edit(/<path to the keyturn plugin>/**)` and `Write(/<path to the keyturn plugin>/**)`.

The person replaces `<path to the keyturn plugin>` with the absolute path of the folder the plugin is loaded from, so that the rules read, for example, `Bash(python3 /Users/me/keyturn/github/scripts/task_branch.py *)` and `Edit(//Users/me/keyturn/**)`. The path is written out in full, with no `*` in it: a wildcard in the path would also match a script of the same name in a folder the agent can write (for example, through `..`). A shell command that writes under the plugin's folder in a way Claude Code does not check against the deny rules is not stopped by a rule: in auto mode the classifier judges it, otherwise the person is asked, and what a changed script then does on GitHub is detected by the detecting workflow (and refused by branch protection where the plan has it), as for any command that goes around the scripts (ADR 0048). The sandbox (#119) closes it.

`deliver` runs each script as a command of its own, by its full path with `python3`, so that the rule matches it.

## Reasons

- The scripts are the only way the procedure touches GitHub, and each checks what it acts on (the branch, the pull request, the conditions); allowing them is what makes the deny rules on the plain commands workable in auto mode.
- Denying the file tools under the plugin's folder closes the plain way of changing a script before running it under its allow rule, and Claude Code applies the same rules to the shell writes it recognizes.
- A deny list for every shell command that can write a file cannot be complete; the classifier, the prompt, and the detecting workflow already stand behind the commands it would miss.

## Consequences

- The person fills in the path once, in the same place as the deny rules, and again when the folder changes (a plugin update moves its installed copy). With a wrong path, the scripts go to the classifier again, and the rules on the folder protect nothing; the permission rules' trial in `AGENTS.md` checks both.
- A changed script can still run under its rule when it was changed in a way the rules do not see. That is the same gap ADR 0036 and ADR 0041 name for every command written another way, and it is closed by the sandbox (#119).
- Other scripts the skills run (`task_state.py`, `approval.py`, the gate, `usage.py check`) get no allow rule: auto mode did not stop them in the rehearsal. If it does, they are added the same way.
