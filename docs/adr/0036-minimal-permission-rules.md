# 0036. During the MVP, the recommended permission rules deny pushes and the commands that discard work, in the person's local settings

- Status: accepted
- Date: 2026-11-21

## Context

During the MVP, agents run without a sandbox, and the Claude Code adapter ships only permission rules that block direct pushes to the default branch and destructive commands ("4. The environment limits the damage" in `docs/design/guardrails.md`, [ADR 0025](0025-mvp-first.md)). The question is which rules, and where the person puts them.

What constrains the answer:

- A Claude Code `Bash` rule matches the text of the command, not the branch it acts on. `git push` with no arguments, run on the default branch, pushes the default branch, and no rule can tell it from the same command on a task branch.
- During the MVP, no role and not `deliver` pushes, merges, or opens a pull request: a person pushes the task branch, opens the pull request, and merges it (`skills/deliver/SKILL.md`).
- The skills discard their own uncommitted outputs path by path, with `git restore --source=HEAD --staged --worktree -- <path>` and `git clean -f -- <path>`, and `deliver` deletes the gate's log with `rm -f -- <path>`. A rule must not block these.
- Deny rules apply in every permission mode (auto mode and `bypassPermissions` included) and inside subagents, and are combined across settings files. A rule catches the command as written, not the same program run another way (`/usr/bin/git push`, `bash -c '...'`, a script); Claude Code's documentation points to the sandbox for that.
- A plugin cannot set permission rules for the person; they go in a settings file. A project's committed files stay free of tool-specific names ("Agent instruction files" in `docs/design/architecture.md`).

## Options considered

1. **Deny `git push` in the forms it is usually written (`git push ...`), and the plain forms of the commands that discard work for good: a recursive `rm`, `find ... -delete`, `git reset --hard`, `git clean` of more than a named path, `git checkout .` and `git restore .`, deleting branches and refs, expiring the reflog, rewriting history with `filter-branch` or `filter-repo`, dropping stashes, `sudo`, and `gh repo delete` and `gh pr merge`. The person adds them to the project's `.claude/settings.local.json`.** Blocks the bare `git push` on the default branch too, and every force push. The person pushes from a terminal of their own, which the MVP already expects. The local settings file is not committed, so the project's files stay free of Claude Code's names.
2. **Deny only pushes that name the default branch** (`git push * main`, `git push * HEAD:main`, and the like). Leaves pushes to task branches to agents, but not the bare `git push` on the default branch, and the default branch's name differs per project, so the rules would have to be written for each.
3. **A `PreToolUse` hook that reads the current branch and the push's target.** Can tell a push to the default branch from any other, but parses the same command text as a rule, so it is bypassed the same ways, and it is code to write and test for something no step needs during the MVP. A plain hook that denies the same commands, always on while the plugin is enabled like the usage hook, would not depend on the person installing anything; it was not weighed, because no hook is added to the plugin until the auto mode stops seen with the plugin loaded (#121) are resolved.
4. **The rules in the project's committed `.claude/settings.json`.** Shared by everyone who works on the project, but commits a Claude Code file to the client's repository.

## Decision

Option 1. `adapters/claude/permission-settings.json` holds the deny rules, and the adapter's README says to add them to `.claude/settings.local.json` of each project keyturn works on (or to the user settings, to cover every project).

## Reasons

- Denying pushes, not only those that name the default branch, is the only rule that covers the bare `git push` on the default branch, and no step needs to push during the MVP.
- The rules list the forms that lose work Git cannot bring back (uncommitted changes, untracked files, deleted branches, rewritten history) or that reach outside the repository, and leave out the path-by-path forms the skills use, which were tried against these rules.
- Settings that are not committed keep the project free of a tool's files, and deny rules from any settings file still apply.

## Consequences

- The person pushes task branches and opens pull requests from a terminal of their own, as during the rest of the MVP. Phase 7 (GitHub integration) changes the push rule, when a step pushes.
- The rules stop the plain forms only. A command written another way (for example, `git -C . push`, `rm -rv`, or `git clean -f -d`), a script that does the same, or a deletion through the file tools, is not stopped. The sandbox (#119) closes that, and every delivery report made during the MVP says agents ran without one. Branch protection on the default branch, set by the person on the Git host, is what blocks a push to it for certain.
- The rules are on only when the person installs them, and nothing checks that they did. During the MVP, the end-to-end run (#63) checks `.claude/settings.local.json` by hand before it starts; how it is checked automatically (a `PreToolUse` hook, or a first check in `deliver`) is decided in #119.
- A person who wants to run one of these commands in a session with the rules has to run it in a terminal of their own.
