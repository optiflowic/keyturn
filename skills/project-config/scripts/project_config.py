#!/usr/bin/env python3
"""Create, check, and read keyturn's project configuration (keyturn/config.json). See ADR 0014.

Usage:
  project_config.py check                   Print "ok", or every problem (one per line) and exit 1.
  project_config.py get SETTING             Check the file, then print one setting's value.
  project_config.py init --client-language LANG (--english-only | --no-english-only)
                                            Write a new configuration. Refuses to overwrite one.

Paths are resolved from the root of the Git repository, whatever the current folder.
The result is deterministic: the same file always gives the same output and exit code.
Needs Python 3.9 or later and Git. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path("keyturn") / "config.json"
LANG_RE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")

# Every setting, in the order problems are reported. Add a setting here, and to the tests, in the pull request that uses it.
SETTINGS = ("client_language", "english_only")


class ConfigError(Exception):
    """The configuration cannot be used. Holds every problem found."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def repo_root() -> Path:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0:
        raise ConfigError(["not inside a Git repository"])
    return Path(result.stdout.strip())


def setting_problems(name: str, value: object) -> list[str]:
    """Return the problems with one known setting's value."""
    if name == "client_language":
        if not isinstance(value, str) or not LANG_RE.fullmatch(value):
            return [f"client_language: not a language code: {json.dumps(value)} (use e.g. \"ja\", \"de\", \"pt-BR\")"]
    elif name == "english_only":
        if not isinstance(value, bool):
            return [f"english_only: must be true or false, not {json.dumps(value)}"]
    return []


class Pairs(dict):
    """A parsed JSON object that also keeps every key-value pair as written, repeated keys included."""

    def __init__(self, pairs: list[tuple[str, object]]):
        super().__init__(pairs)
        self.pairs = pairs


def validate(data: object) -> list[str]:
    """Return every problem with parsed configuration data, in a fixed order.

    Order: settings given more than once, then each known setting (missing, or each invalid value as written), then unknown settings.
    """
    if not isinstance(data, dict):
        return ["the configuration must be a JSON object ({...})"]
    pairs = data.pairs if isinstance(data, Pairs) else list(data.items())
    names = [name for name, _ in pairs]
    problems = [f"{name}: set more than once" for name in sorted({n for n in names if names.count(n) > 1})]
    for name in SETTINGS:
        values = [value for key, value in pairs if key == name]
        if not values:
            problems.append(f"{name}: missing")
        for value in values:  # every occurrence, so an invalid first value is not hidden by a valid later one
            for problem in setting_problems(name, value):
                if problem not in problems:
                    problems.append(problem)
    for name in sorted(set(names) - set(SETTINGS)):
        problems.append(f"{name}: unknown setting")
    return problems


def load(root: Path) -> dict:
    """Read and check the configuration. Raise ConfigError with every problem if it cannot be used."""
    path = root / CONFIG_PATH
    if not path.is_file():
        raise ConfigError([f"{CONFIG_PATH}: missing (create it with: project_config.py init)"])
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise ConfigError([f"{CONFIG_PATH}: not UTF-8 text"]) from None
    except OSError as error:
        raise ConfigError([f"{CONFIG_PATH}: cannot read: {error.strerror or error}"]) from None

    try:
        # Keep every pair as written, so repeated settings and each of their values are checked, not only the last one.
        data = json.loads(text, object_pairs_hook=Pairs)
    except json.JSONDecodeError as error:
        raise ConfigError([f"{CONFIG_PATH}: not valid JSON: {error.msg} (line {error.lineno}, column {error.colno})"]) from None
    problems = validate(data)
    if problems:
        raise ConfigError(problems)
    return data


def render(data: dict) -> str:
    """The canonical text of a configuration: settings in order, two-space indent, final newline."""
    return json.dumps({name: data[name] for name in SETTINGS}, indent=2, ensure_ascii=False) + "\n"


def cmd_check(root: Path) -> None:
    load(root)
    print("ok")


def cmd_get(root: Path, name: str) -> None:
    if name not in SETTINGS:
        raise ConfigError([f"{name}: unknown setting (known: {', '.join(SETTINGS)})"])
    print(json.dumps(load(root)[name], ensure_ascii=False).strip('"'))


def cmd_init(root: Path, client_language: str, english_only: bool) -> None:
    path = root / CONFIG_PATH
    exists = ConfigError([f"{CONFIG_PATH}: already exists; edit it, then run check"])
    if os.path.lexists(path):  # also true for a broken symbolic link, which exists() misses
        raise exists
    data = {"client_language": client_language, "english_only": english_only}
    problems = validate(data)
    if problems:
        raise ConfigError(problems)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:  # for example, "keyturn" is a file, or the folder is read-only
        raise ConfigError([f"{CONFIG_PATH}: cannot write: {error.strerror or error}"]) from None
    try:
        # "x" fails if anything appeared at the path since the check above, so nothing is ever overwritten.
        with open(path, "xb") as file:
            file.write(render(data).encode("utf-8"))
    except FileExistsError:
        raise exists from None
    except OSError as error:
        raise ConfigError([f"{CONFIG_PATH}: cannot write: {error.strerror or error}"]) from None
    print(f"wrote {CONFIG_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create, check, and read keyturn/config.json.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check the configuration")
    get = commands.add_parser("get", help="check the configuration, then print one setting")
    get.add_argument("setting")
    init = commands.add_parser("init", help="write a new configuration")
    init.add_argument("--client-language", required=True)
    mode = init.add_mutually_exclusive_group(required=True)
    mode.add_argument("--english-only", dest="english_only", action="store_true")
    mode.add_argument("--no-english-only", dest="english_only", action="store_false")
    args = parser.parse_args()

    try:
        root = repo_root()
        if args.command == "check":
            cmd_check(root)
        elif args.command == "get":
            cmd_get(root, args.setting)
        else:
            cmd_init(root, args.client_language, args.english_only)
    except ConfigError as error:
        for problem in error.problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
