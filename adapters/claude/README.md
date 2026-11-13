# Claude Code adapter

The parts of keyturn that only Claude Code uses. Everything shared (skills, templates) stays outside `adapters/`.

## Usage limits

keyturn must not use up a subscription's usage windows ("Subscription usage limits" in [`docs/DESIGN.md`](../../docs/DESIGN.md)). Claude Code gives a status line command the plan's usage, as `rate_limits.five_hour` and `rate_limits.seven_day` (`used_percentage`, and `resets_at` in epoch seconds), on Pro and Max plans once the session has had an API response.

[`scripts/usage.py`](scripts/usage.py) (Python 3.9 or later, standard library only) works from that:

| Command | Where it runs | What it does |
|---|---|---|
| `usage.py statusline` | the status line | Records both windows in `~/.keyturn/usage.json` (one file per user: the windows belong to the account, not to a project) and prints them, for example `5-hour 42%  7-day 13%`. |
| `usage.py check` | before each new step (the `deliver` skill) | Soft stop. Exits 0 when both windows are below `--soft` (default 80). Exits 1, with a `stop:` line per reason, when a window is at or above it, or when a value is unknown: nothing recorded, a window missing, a recording older than 15 minutes (`--max-age-minutes`), or a window past its reset with no newer value. A stop for usage says when it can continue. |
| `usage.py hook` | every tool call, as a PreToolUse hook | Hard stop. Denies the call when a recorded window is at or above `--hard` (default 90) and has not reset yet, even if the recording is old (usage only grows until the reset). A missing value never blocks a tool call; `check` stops at the next step boundary instead. |

Both limits apply to the 5-hour and the 7-day window. To change them, pass `--soft` to `check` and `--hard` to `hook`.

### Setting it up

- The hook is part of the plugin ([`hooks/hooks.json`](../../hooks/hooks.json)), so it is on whenever the plugin is enabled, also inside subagents.
- A plugin cannot set the status line, so add it to your user settings (`~/.claude/settings.json`), as in [`statusline-settings.json`](statusline-settings.json), with the path of the plugin's folder (your working copy, when you load it with `claude --plugin-dir .`). If you already have a status line, call `usage.py statusline` from it with the same input on stdin, and print its line with yours.
- The file can also be moved with `KEYTURN_USAGE_FILE`, set the same way for the status line, the hook, and `check`.

### What is not known yet

- Headless runs (`claude -p`) and subagents may not run the status line. Then no recording is fresh, and `check` stops every new step: run the pipeline in an interactive session until a usage source exists for those runs.
- Codex needs its own usage source (phase 10).
