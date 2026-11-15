#!/usr/bin/env python3
"""Keep keyturn within the Claude subscription's usage windows.

Claude Code gives a status line command the plan's usage on stdin, as
rate_limits.five_hour and rate_limits.seven_day (used_percentage, resets_at in
epoch seconds), on Pro and Max plans, once the session has had an API response.
This script records those values and answers two questions from them:

  statusline   Read the status line input, record the usage, print one line.
  check        Before a new step: may it start? Exit 0 if yes, 1 if not.
               A window at or above --soft (default 80), or a value that is
               missing, out of date, or past its reset, means no.
  hook         As a PreToolUse hook: block the tool call when a window is at
               or above --hard (default 90). A missing value does not block;
               `check` stops at the next step boundary instead. Also block a
               tool call that tries to release a stop: only a person may.
  release      Run by a person: lift the stop of each window that is at or
               above --soft now, until that window resets. A window at or
               above --hard has its hard stop lifted too.

The usage is the account's, not a project's, so it is kept in one file per user:
~/.keyturn/usage.json, or the absolute path in KEYTURN_USAGE_FILE; releases are
kept next to it, in usage-release.json. The default limits can be set with
KEYTURN_SOFT_LIMIT and KEYTURN_HARD_LIMIT. KEYTURN_PLAN_WINDOWS names the windows
the plan has (default: five_hour,seven_day); a missing value of a window it leaves
out does not stop `check`, while a known one still does. A window is left out only
when a person says so there, never because Claude Code does not send it: a missing
value may only mean it has not arrived.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

WINDOWS = {"five_hour": "5-hour", "seven_day": "7-day"}
DEFAULT_SOFT = "80"
DEFAULT_HARD = "90"
# The status line runs on every assistant message, so a recording older than this
# means nothing has updated it (for example, a headless run) and it may be too low.
DEFAULT_MAX_AGE_MINUTES = "15"


# A Bash command that runs this script's release command. The hook denies it: an agent must not lift its own stop.
# Matched at the subcommand's place (after the script and its options), so that a command that only
# mentions both, such as `usage.py check && git commit -m "release notes"`, is not denied.
RELEASE_COMMAND = re.compile(r"usage\.py[\'\"]?(?:\s+-\S+(?:\s+[^-\s]\S*)?)*(?:\s|\\\n)+[\'\"]?release\b")


class ConfigError(Exception):
    """The script was set up wrongly: the person must fix it, so it is never treated as missing data."""


def usage_file() -> Path:
    configured = os.environ.get("KEYTURN_USAGE_FILE")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            # A relative path would point to a different file in each process's folder.
            raise ConfigError(f"KEYTURN_USAGE_FILE must be an absolute path: {configured}")
        return path
    try:
        return Path.home() / ".keyturn" / "usage.json"
    except RuntimeError as error:
        raise ConfigError(f"cannot find the home folder ({error}); set KEYTURN_USAGE_FILE") from None


def release_file() -> Path:
    usage = usage_file()
    return usage.with_name(usage.stem + "-release" + usage.suffix)


def plan_windows() -> list:
    configured = os.environ.get("KEYTURN_PLAN_WINDOWS")
    if configured is None:
        return list(WINDOWS)
    names = [name.strip() for name in configured.split(",") if name.strip()]
    unknown = [name for name in names if name not in WINDOWS]
    if not names or unknown:
        # Fail closed: a typo must not turn a window's stop off.
        raise ConfigError(f"KEYTURN_PLAN_WINDOWS must name one or more of {', '.join(WINDOWS)}: {configured}")
    return [name for name in WINDOWS if name in names]


def utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_window(window: object) -> bool:
    """The one check for a window's values, whether they come from Claude Code or from the file."""
    if not isinstance(window, dict):
        return False
    used, resets = window.get("used_percentage"), window.get("resets_at")
    return is_number(used) and 0 <= used <= 100 and is_number(resets) and is_time(resets)


def is_time(epoch: float) -> bool:
    """A finite number may still be outside what a date can hold; such a window must not break the others."""
    try:
        utc(epoch)
    except (OverflowError, OSError, ValueError):
        return False
    return True


# --- Recording ----------------------------------------------------------------------------------------------------


def windows_from_status(status: dict, now: float) -> dict:
    """Keep only well-formed windows; a window Claude Code left out stays out."""
    limits = status.get("rate_limits")
    if not isinstance(limits, dict):
        return {}
    return {name: {"used_percentage": float(limits[name]["used_percentage"]),
                   "resets_at": float(limits[name]["resets_at"]),
                   "recorded_at": now}
            for name in WINDOWS if valid_window(limits.get(name))}


def merge(new_windows: dict, record: dict | None, now: float) -> dict:
    """Keep a recorded window that the new input leaves out until it resets.

    Claude Code may leave rate_limits out (for example, before a session's first
    API response); that must not erase a high value the hard stop relies on.
    """
    kept = {}
    for name, window in (record or {}).get("windows", {}).items():
        if name in WINDOWS and valid_window(window) and window["resets_at"] > now:
            kept[name] = window
    kept.update(new_windows)
    return kept


def write_json(path: Path, content: dict) -> None:
    """Write atomically, through a temporary file of its own, so a check never reads half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(json.dumps(content, indent=2) + "\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_record(windows: dict, now: float) -> None:
    write_json(usage_file(), {"written_at": now, "windows": windows})


def status_text(windows: dict) -> str:
    if not windows:
        return "usage: unknown"
    return "  ".join(f"{WINDOWS[name]} {windows[name]['used_percentage']:.0f}%" for name in WINDOWS if name in windows)


def cmd_statusline(now: float) -> int:
    """Never fail: a broken status line would hide the session's state from the person."""
    try:
        status = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        status = {}
    new_windows = windows_from_status(status if isinstance(status, dict) else {}, now)
    try:
        write_record(merge(new_windows, read_record(), now), now)
    except (OSError, ConfigError) as error:
        print(f"usage: not recorded ({getattr(error, 'strerror', None) or error})")
        return 0
    print(status_text(new_windows))
    return 0


# --- Reading ------------------------------------------------------------------------------------------------------


def read_record() -> dict | None:
    try:
        record = json.loads(usage_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return record if isinstance(record, dict) and isinstance(record.get("windows"), dict) else None


def read_releases() -> dict:
    """A release that cannot be read counts as none: the stop stays."""
    try:
        releases = json.loads(release_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return releases if isinstance(releases, dict) else {}


def is_released(releases: dict, name: str, state: dict, stop: str) -> bool:
    """A release holds only for the window it was made for: a new window (a new reset time) stops again.

    If Claude Code ever moved a window's reset time, the release would end early: that fails safe.
    """
    release = releases.get(name)
    if not isinstance(release, dict) or "used" not in state or release.get("resets_at") != state["resets_at"]:
        return False
    return release.get("stop") == "hard" or (stop == "soft" and release.get("stop") == "soft")


def window_states(record: dict | None, now: float, max_age_minutes: float) -> dict:
    """For each window: its used percentage and reset time, or why it is unknown."""
    states = {}
    for name, label in WINDOWS.items():
        if record is None:
            states[name] = {"unknown": f"{label} window: no usage recorded ({usage_file()})"}
            continue
        window = record["windows"].get(name)
        recorded_at = window.get("recorded_at") if isinstance(window, dict) else None
        if not valid_window(window) or not is_number(recorded_at):
            states[name] = {"unknown": f"{label} window: not in the last recording"}
        elif window["resets_at"] <= now:
            states[name] = {"unknown": f"{label} window: reset at {utc(window['resets_at'])}, no newer value yet"}
        elif now - recorded_at > max_age_minutes * 60:
            states[name] = {"unknown": f"{label} window: last recorded at {utc(recorded_at)}, more than {max_age_minutes:g} minutes ago"}
        else:
            states[name] = {"used": window["used_percentage"], "resets_at": window["resets_at"]}
    return states


def cmd_check(soft: float, now: float, max_age_minutes: float) -> int:
    windows = plan_windows()
    states = window_states(read_record(), now, max_age_minutes)
    releases = read_releases()
    stops, notes = [], []
    for name, label in WINDOWS.items():
        state = states[name]
        if "unknown" in state and name not in windows:
            continue  # the person said the plan does not have it; a known value still counts below
        if "unknown" in state:
            stops.append(f"stop: {state['unknown']}; treat it as unknown")
        elif state["used"] >= soft and is_released(releases, name, state, "soft"):
            notes.append(f"{label} window at {state['used']:.0f}%, released by a person until {utc(state['resets_at'])}")
        elif state["used"] >= soft:
            stops.append(f"stop: {label} window at {state['used']:.0f}% (limit {soft:g}%), "
                         f"can continue after {utc(state['resets_at'])}")
    if stops:
        print("\n".join(stops))
        return 1
    print("ok: " + ", ".join(f"{WINDOWS[name]} window at {states[name]['used']:.0f}%" for name in WINDOWS if "used" in states[name]))
    for note in notes:
        print(f"note: {note}")
    return 0


def tries_to_release(tool_call: object) -> bool:
    """Whether a tool call runs the release command or touches the release file.

    This catches the plain ways an agent would try; it is a guardrail, not a sandbox.
    """
    if not isinstance(tool_call, dict) or not isinstance(tool_call.get("tool_input"), dict):
        return False
    tool_input = tool_call["tool_input"]
    command = tool_input.get("command")
    if isinstance(command, str) and (RELEASE_COMMAND.search(command) or release_file().name in command):
        return True
    paths = [value for key, value in tool_input.items() if key.endswith("path") and isinstance(value, str)]
    return any(Path(path).name == release_file().name for path in paths)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


def cmd_hook(hard: float, now: float) -> int:
    """Block only on a known value at or above the limit; never on missing data.

    An old value still counts here: usage only grows until the window resets.
    """
    try:
        tool_call = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        tool_call = None
    if tries_to_release(tool_call):
        deny("keyturn: only a person can release a usage stop, by running `usage.py release` themselves. "
             "Do not try it through a tool: stop and ask the person.")
        return 0
    states = window_states(read_record(), now, max_age_minutes=float("inf"))
    releases = read_releases()
    reasons = [f"{label} window at {states[name]['used']:.0f}% (limit {hard:g}%), resets at {utc(states[name]['resets_at'])}"
               for name, label in WINDOWS.items()
               if "used" in states[name] and states[name]["used"] >= hard and not is_released(releases, name, states[name], "hard")]
    if reasons:
        # Every tool call is denied, so the agent cannot save anything now: resume uses the
        # state saved at the last step boundary.
        deny("keyturn hard stop: " + "; ".join(reasons)
             + ". Stop now and start no new work until the window resets; resume continues from the state saved at the last step.")
    return 0


def cmd_release(soft: float, hard: float, now: float) -> int:
    """Lift the stop of each window that has one now, until that window resets.

    Like the hook, an old value counts: a hard stop denies the tool calls that would refresh it.
    """
    states = window_states(read_record(), now, max_age_minutes=float("inf"))
    releases = {name: release for name, release in read_releases().items()
                if name in WINDOWS and isinstance(release, dict) and is_number(release.get("resets_at")) and release["resets_at"] > now}
    released, lines = [], []
    windows = plan_windows()
    for name, label in WINDOWS.items():
        state = states[name]
        if "unknown" in state and name not in windows:
            continue  # the plan does not have it, and the hook stops only on a known value
        if "unknown" in state:
            lines.append(f"not released: {state['unknown']}; a window can be released only while its value is known")
        elif state["used"] >= min(soft, hard):
            stop = "hard" if state["used"] >= hard else "soft"
            if is_released(releases, name, state, "hard"):
                stop = "hard"  # releasing again, with other limits, never takes back a hard release of the same window
            releases[name] = {"resets_at": state["resets_at"], "stop": stop, "released_at": now}
            released.append(name)
            lines.append(f"released: {label} window at {state['used']:.0f}%, {stop} stop"
                         f"{' and soft stop' if stop == 'hard' else ''} lifted until {utc(state['resets_at'])}")
    if not released:
        lines.append(f"nothing to release: no window is at or above {min(soft, hard):g}%")
        print("\n".join(lines))
        return 1
    try:
        write_json(release_file(), releases)
    except OSError as error:
        print(f"stop: the release was not recorded ({release_file()}: {error.strerror or error}); nothing was released")
        return 1
    print("\n".join(lines))
    return 0


# --- Arguments ----------------------------------------------------------------------------------------------------


def percentage(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a percentage between 0 and 100: {value}") from None
    if not (math.isfinite(number) and 0 < number <= 100):
        raise argparse.ArgumentTypeError(f"not a percentage between 0 and 100: {value}")
    return number


def minutes(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a positive number of minutes: {value}") from None
    if not (math.isfinite(number) and number > 0):
        raise argparse.ArgumentTypeError(f"not a positive number of minutes: {value}")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep keyturn within the Claude subscription's usage windows.")
    parser.add_argument("--now", type=float, default=None, help=argparse.SUPPRESS)  # epoch seconds, for tests
    parser.add_argument("--max-age-minutes", type=minutes, default=DEFAULT_MAX_AGE_MINUTES)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("statusline", help="record the usage from the status line input and print it")
    check = commands.add_parser("check", help="exit 0 if a new step may start, 1 if not")
    # argparse applies `type` to a string default too, so a wrong KEYTURN_*_LIMIT is reported like a wrong option.
    check.add_argument("--soft", type=percentage, default=os.environ.get("KEYTURN_SOFT_LIMIT") or DEFAULT_SOFT)
    hook = commands.add_parser("hook", help="PreToolUse hook: deny tool calls at the hard limit")
    hook.add_argument("--hard", type=percentage, default=os.environ.get("KEYTURN_HARD_LIMIT") or DEFAULT_HARD)
    release = commands.add_parser("release", help="run by a person: lift the current stops until each window resets")
    release.add_argument("--soft", type=percentage, default=os.environ.get("KEYTURN_SOFT_LIMIT") or DEFAULT_SOFT)
    release.add_argument("--hard", type=percentage, default=os.environ.get("KEYTURN_HARD_LIMIT") or DEFAULT_HARD)
    args = parser.parse_args()

    now = time.time() if args.now is None else args.now
    try:
        if args.command == "statusline":
            return cmd_statusline(now)
        if args.command == "check":
            return cmd_check(args.soft, now, args.max_age_minutes)
        if args.command == "release":
            return cmd_release(args.soft, args.hard, now)
        return cmd_hook(args.hard, now)
    except ConfigError as error:
        # Set up wrongly: fail closed. Exit 2 makes Claude Code block the tool call and show the message.
        print(f"keyturn usage: {error}", file=sys.stderr)
        if args.command in ("check", "release"):
            print(f"stop: {error}")
            return 1
        return 2
    except Exception as error:  # an unexpected error must never look like "ok"
        print(f"keyturn usage: unexpected error: {error!r}", file=sys.stderr)
        if args.command in ("check", "release"):
            print(f"stop: cannot read the usage ({error!r}); treat it as unknown")
            return 1
        return 1  # hook: a non-blocking error, like missing data; check stops at the next step


if __name__ == "__main__":
    sys.exit(main())
