# 0059. The roles write files through the tool's file operations, try things in a new scratch folder each time, and never delete recursively

- Status: accepted
- Date: 2026-11-23

## Context

The recommended permission rules deny the plain forms of commands that discard work for good: a recursive `rm`, `find ... -delete`, and `git clean` of more than a named path (`-d`, `-x`, `-X`) among them ([ADR 0036](0036-minimal-permission-rules.md), [ADR 0041](0041-agents-push-task-branches-and-open-pull-requests.md)). A denied command is a command that did not run, and a role that meets one stops ("A script the tool refuses to run did not run" in `deliver`).

The skills name some of the commands a role runs, and leave the rest to the agent. In the end-to-end rehearsal (#63), the second task stopped in `conventions` three times on commands no skill names, each denied as intended:

- the step wrote repository files through the shell (`cat > <file> <<'EOF'`), and tried a tool config on a sample in a scratch folder that it deleted with `rm -rf` and made again, all bundled in one call with `mkdir` and the redirections, so the denial stopped all of it;
- it put back what an install created with `rm -rf <the part's folder>`;
- `deliver`, discarding the interrupted step's outputs as "Interrupted outputs" says, ran `git clean -fd -- <the part's folder>`: the skill names `git clean -f -- <path>` for an untracked file and says nothing about a folder.

With a path, `git clean -f -- <path>` removes every untracked file under it, a folder included, so `-d` is never needed. It leaves the files Git ignores (such as `node_modules`), and the agent cannot remove them with the commands the rules allow.

## Options considered

1. **A rule in every role's skill**: write and change files with the tool's file operations; create a scratch folder new each time, outside the repository, and leave it; never delete recursively or run `git clean` with `-d`, `-x`, or `-X`; delete one path per command; do not bundle unrelated actions in one command. Name `git clean -f -- <path>` where a skill removes a folder, and say that ignored files stay. The commands the skills lead to are then ones the rules allow, and a skill still names no tool.
2. **Loosen the permission rules** to allow `rm -rf` in scratch folders and `git clean -fd -- <path>`: the rules match a command's text, so they cannot tell a scratch folder or a named path from the repository root once a recursive delete is allowed. It reopens what ADR 0036 closed.
3. **Leave it to the agent**, and let the maintainer approve each denied command: every task stops on commands that change nothing the client gets.

## Decision

Option 1. Every role that writes files or runs commands in a task (`spec`, `design`, `conventions`, `implement`, `qa`, `security-review`, `review`, `deliver`, `resume`) has the rule in its "Rules":

- Files are written and changed with the file operations of the tool the role runs in, never through the shell (a redirection, `tee`, or a here-document).
- A scratch folder, to try something on a sample or to resolve a dependency tree, is created new each time, outside the repository (`mktemp -d`), and left there. A role never deletes one to start again.
- A role never deletes recursively (`rm -r`, `rm -rf`, `find ... -delete`) and never runs `git clean` with `-d`, `-x`, or `-X`. Inside the repository it deletes one path per command: `git rm -- <file>` for a tracked file, `rm -f -- <file>` or `git clean -f -- <path>` for what Git does not track; the latter removes an untracked folder too.
- Unrelated actions are not bundled in one command, so that a command the tool refuses stops only that action.

`deliver`'s "Interrupted outputs" and `conventions`' put-back of an install use `git clean -f -- <path>` for an untracked folder too. Each first removes the uncommitted files the step wrote (a `.gitignore` among them), then removes every untracked folder `git status --porcelain` shows, again until none is left: a folder that only a removed `.gitignore` ignored (the step's own, or one a package ships) shows as untracked once that file is gone. What a committed `.gitignore` ignores stays: Git does not show it, and the gate runs in temporary worktrees and never reads it.

## Reasons

- The rules are a guardrail that must stay on; the skills can keep within them at no cost, since nothing a role does needs a recursive delete.
- A new scratch folder each time needs no cleanup, and the machine's temporary folder is cleared by the system. Leaving it costs disk space only.
- Writing through the file operations keeps every change visible to the tool's own checks (for example, the rules that deny edits to the plugin's folder), and a shell redirection hides a file's content inside a command.
- Saying it in words a skill can use on any tool keeps the skills tool-neutral; the commands named are Git's and the shell's, which every tool runs.

## Consequences

- The role skills get one more rule each; `deliver` and `conventions` name `git clean -f -- <path>` for folders.
- Scratch folders pile up in the machine's temporary folder until the system clears it.
- Ignored files an interrupted step left (such as `node_modules`) stay in the working tree. They do not change what the gate checks, which runs in temporary worktrees. A later install in the same folder may reuse them where no lock file is committed, so a new lock file can differ from a fresh resolution; the gate's checks of the lock file still apply.
- Agents can still write a command another way; the rules match the text only, as ADR 0036 says. The rule makes the skills lead to the allowed commands; it does not enforce them.
