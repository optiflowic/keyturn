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
               `check` stops at the next step boundary instead.

The usage is the account's, not a project's, so it is kept in one file per user:
~/.keyturn/usage.json, or the path in KEYTURN_USAGE_FILE.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WINDOWS = {"five_hour": "5-hour", "seven_day": "7-day"}
DEFAULT_SOFT = 80.0
DEFAULT_HARD = 90.0
# The status line runs on every assistant message, so a recording older than this
# means nothing has updated it (for example, a headless run) and it may be too low.
DEFAULT_MAX_AGE_MINUTES = 15


def usage_file() -> Path:
    return Path(os.environ.get("KEYTURN_USAGE_FILE") or Path.home() / ".keyturn" / "usage.json")


def utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


# --- Recording ----------------------------------------------------------------------------------------------------


def windows_from_status(status: dict) -> dict:
    """Keep only well-formed windows; a window Claude Code left out stays out."""
    limits = status.get("rate_limits")
    found = {}
    if not isinstance(limits, dict):
        return found
    for name in WINDOWS:
        window = limits.get(name)
        if not isinstance(window, dict):
            continue
        used, resets = window.get("used_percentage"), window.get("resets_at")
        if isinstance(used, (int, float)) and isinstance(resets, (int, float)):
            found[name] = {"used_percentage": float(used), "resets_at": float(resets)}
    return found


def write_record(windows: dict, now: float) -> None:
    """Write atomically, so a check never reads half a file."""
    path = usage_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps({"written_at": now, "windows": windows}, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


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
    windows = windows_from_status(status if isinstance(status, dict) else {})
    try:
        write_record(windows, now)
    except OSError as error:
        print(f"usage: not recorded ({error.strerror or error})")
        return 0
    print(status_text(windows))
    return 0


# --- Reading ------------------------------------------------------------------------------------------------------


def read_record() -> dict | None:
    try:
        record = json.loads(usage_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return record if isinstance(record, dict) and isinstance(record.get("windows"), dict) else None


def window_states(record: dict | None, now: float, max_age_minutes: float) -> dict:
    """For each window: its used percentage and reset time, or why it is unknown."""
    states = {}
    for name, label in WINDOWS.items():
        if record is None:
            states[name] = {"unknown": f"{label} window: no usage recorded ({usage_file()})"}
            continue
        window = record["windows"].get(name)
        written_at = record.get("written_at")
        if not isinstance(window, dict) or not isinstance(written_at, (int, float)):
            states[name] = {"unknown": f"{label} window: not in the last recording"}
        elif window["resets_at"] <= now:
            states[name] = {"unknown": f"{label} window: reset at {utc(window['resets_at'])}, no newer value yet"}
        elif now - written_at > max_age_minutes * 60:
            states[name] = {"unknown": f"{label} window: last recorded at {utc(written_at)}, more than {max_age_minutes:g} minutes ago"}
        else:
            states[name] = {"used": window["used_percentage"], "resets_at": window["resets_at"]}
    return states


def cmd_check(soft: float, now: float, max_age_minutes: float) -> int:
    states = window_states(read_record(), now, max_age_minutes)
    stops = []
    for name, label in WINDOWS.items():
        state = states[name]
        if "unknown" in state:
            stops.append(f"stop: {state['unknown']}; treat it as unknown")
        elif state["used"] >= soft:
            stops.append(f"stop: {label} window at {state['used']:.0f}% (limit {soft:g}%), "
                         f"can continue after {utc(state['resets_at'])}")
    if stops:
        print("\n".join(stops))
        return 1
    print("ok: " + ", ".join(f"{WINDOWS[name]} window at {states[name]['used']:.0f}%" for name in WINDOWS))
    return 0


def cmd_hook(hard: float, now: float) -> int:
    """Block only on a known value at or above the limit; never on missing data.

    An old value still counts here: usage only grows until the window resets.
    """
    states = window_states(read_record(), now, max_age_minutes=float("inf"))
    reasons = [f"{label} window at {states[name]['used']:.0f}% (limit {hard:g}%), resets at {utc(states[name]['resets_at'])}"
               for name, label in WINDOWS.items() if "used" in states[name] and states[name]["used"] >= hard]
    if reasons:
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "keyturn hard stop: " + "; ".join(reasons)
                + ". Save the task's state and stop until the window resets.",
            }
        }
        print(json.dumps(decision))
    return 0


def percentage(value: str) -> float:
    number = float(value)
    if not 0 < number <= 100:
        raise argparse.ArgumentTypeError(f"not a percentage between 0 and 100: {value}")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep keyturn within the Claude subscription's usage windows.")
    parser.add_argument("--now", type=float, default=None, help=argparse.SUPPRESS)  # epoch seconds, for tests
    parser.add_argument("--max-age-minutes", type=float, default=DEFAULT_MAX_AGE_MINUTES)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("statusline", help="record the usage from the status line input and print it")
    check = commands.add_parser("check", help="exit 0 if a new step may start, 1 if not")
    check.add_argument("--soft", type=percentage, default=DEFAULT_SOFT)
    hook = commands.add_parser("hook", help="PreToolUse hook: deny tool calls at the hard limit")
    hook.add_argument("--hard", type=percentage, default=DEFAULT_HARD)
    args = parser.parse_args()

    now = time.time() if args.now is None else args.now
    if args.command == "statusline":
        return cmd_statusline(now)
    if args.command == "check":
        return cmd_check(args.soft, now, args.max_age_minutes)
    return cmd_hook(args.hard, now)


if __name__ == "__main__":
    sys.exit(main())
