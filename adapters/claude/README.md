# Claude Code adapter

The parts of keyturn that only Claude Code uses. Everything shared (skills, templates) stays outside `adapters/`.

## Subagents

`deliver` runs every role in a context of its own ("Separate the 'what' from the 'who'" in [`docs/design/architecture.md`](../../docs/design/architecture.md#separate-the-what-from-the-who)). In Claude Code, each is a subagent defined in [`agents/`](agents/) and listed in [`plugin.json`](../../.claude-plugin/plugin.json). With the plugin enabled, they appear as `keyturn:<name>`:

| Subagent | Runs | Model |
|---|---|---|
| `pm` | the `spec` skill | `opus` |
| `architect` | the `design` skill | `opus` |
| `standards` | the `conventions` skill | `sonnet` |
| `developer` | the `implement` skill | `sonnet` |
| `qa` | the `qa` skill | `sonnet` |
| `security` | the `security-review` skill | `opus` |
| `reviewer` | the `review` skill | `opus` |
| `pm-delivery` | the last step of `deliver`: the acceptance guide and the delivery report | `opus` |

Each one preloads its skill (as `keyturn:<skill>`; a bare name can load another skill or command of the same name) and gets only `Read`, `Grep`, `Glob`, `Edit`, `Write`, and `Bash`; `pm` and `architect` also get `Skill` (for the `localize` and `project-config` skills) and `Agent` (for the `localize` skill's translations). No web tool and no MCP tools (the shell can still reach the network). The subagent `pm` or `architect` starts for a translation is not one of these, so it may have every tool of the session until the translation subagent exists (#119). Why, and what that does not limit, is in [ADR 0035](../../docs/adr/0035-subagent-tools-and-models.md).

- `deliver` does not name them: it starts each role in a context of its own, and Claude Code picks the subagent by its description, which names the step of `deliver` it is for. Start them as subagents, not as the main session with `claude --agent`: started that way, the skill is not preloaded.
- To run a role on another model, pass the model when the subagent is started; the definitions set the defaults.
- Claude Code ignores `hooks`, `mcpServers`, and `permissionMode` in a plugin's subagents. The plugin's hooks (the usage limits) and your permission rules still apply inside them.

## Permission settings

During the MVP, agents run without a sandbox ("4. The environment limits the damage" in [`docs/design/guardrails.md`](../../docs/design/guardrails.md#4-the-environment-limits-the-damage)). [`permission-settings.json`](permission-settings.json) holds the recommended rules: they deny `git push` as it is usually written, and the plain forms of commands that discard work for good (a recursive `rm`, `find ... -delete`, `git reset --hard`, `git clean` of more than a named path, `git checkout .`, `git restore .`, deleting branches and refs, `filter-branch` and `filter-repo`, dropping stashes), `sudo`, `gh repo delete`, and the `gh pr` commands that change a pull request (`merge`, `create`, `edit`, `ready`, `close`, `review`, `comment`, `reopen`, `update-branch`, `lock`), so that a closed pull request is never reopened outside the script either, and `gh api`, which could do the same and post on the pull request around the script that posts the reviews ([ADR 0036](../../docs/adr/0036-minimal-permission-rules.md), [ADR 0041](../../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0044](../../docs/adr/0044-task-branch-and-pull-request-kept-in-step-with-origin.md), [ADR 0045](../../docs/adr/0045-deliver-posts-the-review-reports-on-the-pull-request.md)).

- Add its `permissions.deny` list to `.claude/settings.local.json` in each project keyturn works on (not committed), or to your user settings (`~/.claude/settings.json`) to cover every project. If the file already has a `deny` list, add these to it. Deny rules apply in every permission mode, auto mode included, and inside subagents.
- `deliver` pushes the task branch and opens its pull request only through keyturn's script, `github/scripts/task_branch.py`, which pushes only `task/<task>`, never with force ([ADR 0041](../../docs/adr/0041-agents-push-task-branches-and-open-pull-requests.md)); the rules keep the plain commands from being a second way. Until the merge step exists (#141), merge the pull request yourself.
- The rules match the command as written, and list the usual forms only. A command written another way (`/usr/bin/git push`, `git -C . push`, `rm -rv`, `git clean -f -d`, `bash -c '...'`), a script that does the same, or a deletion through the file tools is not stopped: they are a guardrail, not a sandbox. Protect the default branch on the Git host (branch protection) so that a push to it is refused for certain.

## Usage limits

keyturn must not use up a subscription's usage windows ("Subscription usage limits" in [`docs/design/guardrails.md`](../../docs/design/guardrails.md#subscription-usage-limits)). Claude Code gives a status line command the plan's usage, as `rate_limits.five_hour` and `rate_limits.seven_day` (`used_percentage`, and `resets_at` in epoch seconds), on Pro and Max plans once the session has had an API response.

[`scripts/usage.py`](scripts/usage.py) (Python 3.9 or later, standard library only) works from that:

| Command | Where it runs | What it does |
|---|---|---|
| `usage.py statusline` | the status line | Records both windows in `~/.keyturn/usage.json` (one file per user: the windows belong to the account, not to a project) and prints them, for example `5-hour 42%  7-day 13%`. A window the input leaves out (for example, before the session's first API response) keeps its last value until it resets, so a high value is never erased. |
| `usage.py check` | before each new step (the `deliver` skill runs it) | Soft stop. Exits 0 when every window the plan has is below `--soft` (default 80), or released. Exits 1, with a `stop:` line per reason, when a window is at or above it, or when a value is unknown: nothing recorded, a window missing, a recording older than 15 minutes (`--max-age-minutes`), or a window past its reset with no newer value. A stop for usage says when it can continue. |
| `usage.py hook` | every tool call, as a PreToolUse hook | Hard stop. Denies the call when a recorded window is at or above `--hard` (default 90), has not reset yet, and is not released, even if the recording is old (usage only grows until the reset). A missing value never blocks a tool call; `check` stops at the next step boundary instead. Also denies a tool call that tries to release a stop (below). |
| `usage.py release` | run by a person, in a terminal of their own ([ADR 0023](../../docs/adr/0023-releasing-usage-stops.md)) | Lifts the stop of each recorded window that is at or above `--soft` (or `--hard`, if that is lower) now (also one the plan leaves out, since the hook still stops on it), until that window's reset time: the soft stop, and the hard stop too when the window is at or above `--hard`. A window released at the soft stop stops again at the hard stop, and can be released again there. The next window (a new reset time) stops again at the same limits. A window whose value is unknown cannot be released. Exits 1 when there is nothing to release, or on a setup or unexpected error, as `check` does. |

Both limits apply to the 5-hour and the 7-day window (for a plan without one, see "Plans without a 5-hour window"). To change them, set `KEYTURN_SOFT_LIMIT` and `KEYTURN_HARD_LIMIT` (percentages) in the environment Claude Code starts in, or pass `--soft` to `check` and `--hard` to `hook`. The installed hook in `hooks/hooks.json` passes no `--hard`, so it uses `KEYTURN_HARD_LIMIT`, or 90 without it: set the variable rather than editing the file.

### Releasing a stop

A stop is released by a person ([ADR 0023](../../docs/adr/0023-releasing-usage-stops.md)): it is there so that an agent does not use up the plan's usage on its own. Run `python3 <path to the keyturn plugin>/adapters/claude/scripts/usage.py release` in a terminal of your own, with the same `KEYTURN_USAGE_FILE`, `KEYTURN_SOFT_LIMIT`, and `KEYTURN_HARD_LIMIT` as the session, if you set them: with other limits, the release may lift the soft stop only while the session's hook still stops at its hard limit. The release is kept next to the usage file, in `usage-release.json`, and ends by itself at the window's reset. To end it sooner, delete that file. A release of the hard stop lifts every stop for that window until its reset, so the window can then be used up.

The hook denies an agent's tool call that runs `usage.py release` (with or without options before `release`, or with `release` in quotes), or that names `usage-release.json` in a command or a file path. It catches the plain ways to try, not every one (for example, a script the agent writes first that does the same, `release` in a shell variable, a made-up recording written to the usage file, or deleting the usage file, after which nothing blocks until the status line writes it again; or `check` run with lower limits or with `KEYTURN_PLAN_WINDOWS` set in front of it): it is a guardrail, not a sandbox. A command that has `usage.py`, then options, then the word `release` is denied even when it does not run the script (for example, `grep 'usage.py release' README.md`).

### Plans without a 5-hour window

Claude Code sends a window only when the plan has it, and only after the session's first API response, so a missing window cannot tell "not sent yet" from "this plan has none". `check` treats a missing window as unknown and stops, unless you say which windows your plan has: set `KEYTURN_PLAN_WINDOWS` to the windows it has, separated by commas (`five_hour`, `seven_day`; default both), in the environment Claude Code starts in, and for `check` and `release`. For example, on a plan with only a weekly limit, `KEYTURN_PLAN_WINDOWS=seven_day` ([ADR 0024](../../docs/adr/0024-windows-a-plan-has-are-a-setting.md)). A missing value of a window left out does not stop `check`; a value that is recorded still counts, so a window the setting leaves out by mistake still stops when Claude Code sends it at or above the limit. A window listed there stops `check` until its value arrives. A value that is empty, or that names anything other than `five_hour` and `seven_day` (in lowercase), is a setup error and stops `check`. The hook still denies on any window recorded at or above the hard limit.

The status line can also send `spend_limit` (behind a Claude apps gateway with spend limits). It is not a subscription window, and `usage.py` neither records nor checks it.

A value in the file that is missing, out of range, or of the wrong type counts as unknown. A setup error (a limit that is not a percentage, or a `KEYTURN_USAGE_FILE` that is not an absolute path) fails closed: `check` stops, and the hook blocks every tool call with the error until it is fixed. Any other unexpected error makes `check` stop and lets the hook allow the call, as for a missing value.

### Setting it up

- The hook is part of the plugin ([`hooks/hooks.json`](../../hooks/hooks.json)), so it is on whenever the plugin is enabled, also inside subagents.
- A plugin cannot set the status line, so add it to your user settings (`~/.claude/settings.json`), as in [`statusline-settings.json`](statusline-settings.json), with the path of the plugin's folder (your working copy, when you load it with `claude --plugin-dir .`). If you already have a status line, call `usage.py statusline` from it with the same input on stdin, and print its line with yours.
- The file can also be moved with `KEYTURN_USAGE_FILE`, an absolute path, set the same way for the status line, the hook, and `check` (in the environment Claude Code starts in).

### What is not known yet

- Headless runs (`claude -p`) and subagents may not run the status line. Then no recording is fresh, and `check` stops every new step: run the pipeline in an interactive session until a usage source exists for those runs.
- Without a subscription (an API key), Claude Code gives no `rate_limits`, so `check` stops every new step. The limits are for subscription plans; there is no way to turn `check` off yet: `KEYTURN_PLAN_WINDOWS` must name at least one window, and a named window stops `check` until its value arrives.
- The hook runs `python3`. If it is not on the `PATH`, Claude Code treats the failed hook as a non-blocking error, and the hard stop is off without a warning.
- Codex needs its own usage source (phase 10).
