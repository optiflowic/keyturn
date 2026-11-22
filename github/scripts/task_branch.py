#!/usr/bin/env python3
"""Push a task's branch and open its pull request on GitHub, and nothing else (ADR 0041).

Usage (from inside the project's repository):
  task_branch.py push TASK    push HEAD to refs/heads/task/TASK on origin; never with force
  task_branch.py open TASK    open the task's pull request as a draft, to the default branch, or update its description
  task_branch.py ready TASK   mark the task's pull request ready for review

`push` checks that the current branch is task/TASK and that it is not the default branch, and pushes only that branch,
without a "+" or --force, so a push that would rewrite the remote branch is refused by Git. `open` and `ready` use the
GitHub CLI (`gh`) and act only on the open pull request whose branch is task/TASK in this repository (never a fork's).
The description lists the client's documents on the branch; the files stay the source of truth.

Exit codes: 0 done; 1 the push or the pull request was refused (the message says why); 2 it could not run (a wrong
branch, no origin, no default branch, no gh).
Needs Python 3.9 or later, Git, and, for open and ready, the GitHub CLI. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TASK_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
# The client's documents, in the order a reader meets them, linked in the description when they exist on the branch.
DOCUMENTS = [
    ("Requirements", "keyturn/client/requirements.md"),
    ("Approvals", "keyturn/client/approvals.md"),
    ("Design summary", "keyturn/client/design-summary.md"),
    ("Acceptance guide", "keyturn/client/acceptance-guide.md"),
    ("Delivery report", "keyturn/client/delivery-report.md"),
]
EXIT_DONE, EXIT_REFUSED, EXIT_SETUP = 0, 1, 2
# Git's variables of the caller would point git at another repository.
ENV = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}


class SetupError(Exception):
    pass


class Refused(Exception):
    pass


def run(args: list[str], root: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=root, capture_output=True, text=True, env=ENV)


def git(root: Path, *args: str) -> str:
    result = run(["git", *args], root)
    if result.returncode != 0:
        raise SetupError(f"git {' '.join(args)}: {result.stderr.strip() or 'failed'}")
    return result.stdout.strip()


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise SetupError("not inside a Git repository")
    return Path(result.stdout.strip())


def default_branch(root: Path) -> str:
    """The default branch's name, from origin's HEAD."""
    if run(["git", "remote", "get-url", "origin"], root).returncode != 0:
        raise SetupError("no remote named origin: a task is delivered through a pull request on it")
    result = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)
    if result.returncode != 0 or not result.stdout.strip().startswith("origin/"):
        raise SetupError("origin's default branch is not known (run: git remote set-head origin --auto)")
    return result.stdout.strip()[len("origin/"):]


def check_task(root: Path, task: str) -> str:
    """The task's branch name, after checking that it is the current branch and not the default branch."""
    if not TASK_RE.fullmatch(task):
        raise SetupError(f"{task}: not a task name (lowercase letters and digits with single hyphens)")
    branch = f"task/{task}"
    current = run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], root).stdout.strip()
    if current != branch:
        raise SetupError(f"the current branch is {current or 'none (a detached HEAD)'}, not {branch}")
    if default_branch(root) == branch:
        raise SetupError(f"{branch} is the default branch; a task's branch never is")
    return branch


def cmd_push(root: Path, task: str) -> None:
    branch = check_task(root, task)
    # An explicit refspec without "+": only this branch, and Git refuses anything but a fast-forward.
    result = run(["git", "push", "--no-verify", "origin", f"HEAD:refs/heads/{branch}"], root)
    if result.returncode != 0:
        raise Refused(f"the push of {branch} was refused: {result.stderr.strip()}")
    print(f"pushed {branch} at {git(root, 'rev-parse', 'HEAD')[:12]}")


def gh(root: Path, *args: str) -> str:
    try:
        result = run(["gh", *args], root)
    except FileNotFoundError:
        raise SetupError("the GitHub CLI (gh) is not installed: https://cli.github.com/") from None
    if result.returncode != 0:
        raise Refused(f"gh {args[0]} {args[1] if len(args) > 1 else ''}: {result.stderr.strip() or 'failed'}")
    return result.stdout


def open_pull_request(root: Path, branch: str) -> dict | None:
    """The open pull request from the task's branch in this repository, or None."""
    found = json.loads(gh(root, "pr", "list", "--head", branch, "--state", "open",
                          "--json", "number,url,isDraft,isCrossRepository,baseRefName"))
    found = [pr for pr in found if not pr.get("isCrossRepository")]
    if len(found) > 1:
        raise Refused(f"more than one open pull request from {branch}: " + ", ".join(pr["url"] for pr in found))
    return found[0] if found else None


def description(root: Path, task: str) -> str:
    lines = [f"Delivery of the task `{task}` by keyturn.", "",
             "The client decides from these documents; the code is here for the reviews and the record.", ""]
    for name, path in DOCUMENTS:
        if run(["git", "cat-file", "-e", f"HEAD:{path}"], root).returncode == 0:
            lines.append(f"- [{name}]({path})")
    lines += ["", f"The task's state is in `keyturn/internal/state/{task}.md`."]
    return "\n".join(lines) + "\n"


def cmd_open(root: Path, task: str) -> None:
    branch = check_task(root, task)
    base = default_branch(root)
    existing = open_pull_request(root, branch)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as body:
        body.write(description(root, task))
    try:
        if existing is None:
            url = gh(root, "pr", "create", "--draft", "--base", base, "--head", branch,
                     "--title", f"keyturn: {task}", "--body-file", body.name).strip()
            print(f"opened {url}")
        else:
            if existing["baseRefName"] != base:
                raise Refused(f"{existing['url']} goes to {existing['baseRefName']}, not to the default branch {base}")
            gh(root, "pr", "edit", str(existing["number"]), "--body-file", body.name)
            print(f"updated {existing['url']}")
    finally:
        os.unlink(body.name)


def cmd_ready(root: Path, task: str) -> None:
    branch = check_task(root, task)
    existing = open_pull_request(root, branch)
    if existing is None:
        raise Refused(f"no open pull request from {branch}: open it first")
    if existing["isDraft"]:
        gh(root, "pr", "ready", str(existing["number"]))
    print(f"ready {existing['url']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push a task's branch and open its pull request (ADR 0041).")
    parser.add_argument("command", choices=["push", "open", "ready"])
    parser.add_argument("task", help="the task's name; its branch is task/<task>")
    args = parser.parse_args()
    try:
        root = repo_root()
        {"push": cmd_push, "open": cmd_open, "ready": cmd_ready}[args.command](root, args.task)
    except SetupError as error:
        print(f"setup error: {error}", file=sys.stderr)
        return EXIT_SETUP
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_DONE


if __name__ == "__main__":
    sys.exit(main())
