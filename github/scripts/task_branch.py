#!/usr/bin/env python3
"""Push a task's branch and open its pull request on GitHub, and nothing else (ADR 0041).

Usage (from inside the project's repository):
  task_branch.py push TASK    push HEAD to refs/heads/task/TASK on origin; never with force
  task_branch.py open TASK    open the task's pull request as a draft, to the default branch, or update its description
  task_branch.py ready TASK   write its description again, from the head, and mark it ready for review

`push` checks that the current branch is task/TASK and that it is not the default branch, and pushes only that branch,
without a "+" or --force, so a push that would rewrite the remote branch is refused by Git. `open` and `ready` use the
GitHub CLI (`gh`) and act only on the open pull request whose branch is task/TASK in this repository (never a fork's);
when that pull request was closed or merged, they stop instead of opening another. The description carries the delivery
report's first two sections (its summary and what the client needs to do) and links the client's documents on the
branch; the files stay the source of truth.

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
# The delivery report's sections the description carries, by their place in the template (the headings are in the
# client's language): "Summary" and "What you need to do".
REPORT = "keyturn/client/delivery-report.md"
REPORT_SECTIONS = 2
EXIT_DONE, EXIT_REFUSED, EXIT_SETUP = 0, 1, 2
# The variables that would point git at another repository, or gh at another repository or host, are dropped; the ones
# that authenticate (GIT_ASKPASS, GIT_SSH_COMMAND, GH_TOKEN, ...) are kept. Nothing may wait for a terminal prompt.
REPOSITORY_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
                        "GIT_NAMESPACE", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GH_REPO", "GH_HOST")
ENV = {name: value for name, value in os.environ.items()
       if name not in REPOSITORY_VARIABLES and not name.startswith("GIT_CONFIG")}
ENV["GIT_TERMINAL_PROMPT"] = "0"
ENV["GH_PROMPT_DISABLED"] = "1"
TIMEOUT_SECONDS = 300
GITHUB_URL_RE = re.compile(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?")


class SetupError(Exception):
    pass


class Refused(Exception):
    pass


def run(args: list[str], root: Path | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, cwd=root, capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL,
                              timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise SetupError(f"{' '.join(args[:3])}: no answer in {TIMEOUT_SECONDS // 60} minutes") from None


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


def origin_repository(root: Path) -> str:
    """origin's GitHub repository, as OWNER/NAME; the push and every gh call go to it, and nowhere else."""
    # The URLs as configured: what gh reads. (`git remote get-url` applies url.<base>.insteadOf, which gh does not.)
    fetch = run(["git", "config", "--get", "remote.origin.url"], root)
    if fetch.returncode != 0:
        raise SetupError("no remote named origin: a task is delivered through a pull request on it")
    url = fetch.stdout.strip()
    pushurls = run(["git", "config", "--get-all", "remote.origin.pushurl"], root).stdout.split()
    if any(push != url for push in pushurls):
        raise SetupError(f"origin pushes to {', '.join(pushurls)}, not to {url}: the pull request would not be where the push went")
    return github_name(url)


def github_name(url: str) -> str:
    match = GITHUB_URL_RE.fullmatch(url)
    if match is None:
        raise SetupError(f"origin is not a GitHub repository: {url}")
    return f"{match.group(1)}/{match.group(2)}"


def default_branch(root: Path) -> str:
    """The default branch's name, from origin's HEAD."""
    origin_repository(root)
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
    # No tags, no submodules, whatever the configuration says: only this branch.
    result = run(["git", "-c", "push.followTags=false", "-c", "push.recurseSubmodules=no", "push", "--no-verify",
                  "--no-follow-tags", "--recurse-submodules=no", "origin", f"HEAD:refs/heads/{branch}"], root)
    if result.returncode != 0:
        message = f"the push of {branch} was refused: {result.stderr.strip()}"
        if re.search(r"non-fast-forward|fetch first|\[rejected\]", result.stderr):
            message += (f"; {branch} on origin has commits this branch does not have: the maintainer looks at them and "
                        "discards them (keyturn's github/README.md, \"When the task branch on origin moved\")")
        raise Refused(message)
    print(f"pushed {branch} at {git(root, 'rev-parse', 'HEAD')[:12]}")


def gh(root: Path, *args: str) -> str:
    """A gh command on origin's repository only (--repo), never on the one gh would pick by itself."""
    try:
        result = run(["gh", *args[:2], "--repo", origin_repository(root), *args[2:]], root)
    except FileNotFoundError:
        raise SetupError("the GitHub CLI (gh) is not installed: https://cli.github.com/") from None
    if result.returncode != 0:
        raise Refused(f"gh {args[0]} {args[1] if len(args) > 1 else ''}: {result.stderr.strip() or 'failed'}")
    return result.stdout


def gh_api(root: Path, endpoint: str, *args: str) -> str:
    """A gh api call; {repo} in the endpoint is origin's repository, never the one gh would pick by itself."""
    endpoint = endpoint.replace("{repo}", origin_repository(root))
    try:
        result = run(["gh", "api", endpoint, *args], root)
    except FileNotFoundError:
        raise SetupError("the GitHub CLI (gh) is not installed: https://cli.github.com/") from None
    if result.returncode != 0:
        raise Refused(f"gh api {endpoint}: {(result.stderr or result.stdout).strip() or 'failed'}")
    return result.stdout


def open_pull_request(root: Path, branch: str) -> dict | None:
    """The open pull request from the task's branch in this repository, or None when it never had one.

    A task has one pull request: when it was closed or merged, a person decides what happens, so this stops instead of
    letting a new one be opened (a task's name, and so its branch, is never used again).
    """
    found = json.loads(gh(root, "pr", "list", "--head", branch, "--state", "all", "--limit", "100",
                          "--json", "number,url,state,isDraft,isCrossRepository,baseRefName,headRefOid"))
    found = [pr for pr in found if not pr.get("isCrossRepository")]
    opened = [pr for pr in found if pr.get("state", "OPEN") == "OPEN"]
    if len(opened) > 1:
        raise Refused(f"more than one open pull request from {branch}: " + ", ".join(pr["url"] for pr in opened))
    if opened:
        return opened[0]
    if found:
        raise Refused(f"the pull request from {branch} was " + ", ".join(f"{pr['state'].lower()} ({pr['url']})" for pr in found)
                      + ": it is never opened again by this script; ask the maintainer what to do")
    return None


def report_sections(root: Path) -> list[str]:
    """The delivery report's first sections at HEAD, without comments, or nothing before the report exists."""
    result = run(["git", "show", f"HEAD:{REPORT}"], root)
    if result.returncode != 0:
        return []
    text = re.sub(r"<!--.*?-->", "", result.stdout, flags=re.DOTALL)
    sections = re.split(r"^(?=## )", text, flags=re.MULTILINE)[1:1 + REPORT_SECTIONS]
    return [re.sub(r"\n{3,}", "\n\n", section).strip() for section in sections]


def description(root: Path, task: str) -> str:
    # Links to the documents at the pushed commit: a pull request description does not resolve relative paths, and the
    # commit pins what the client reads.
    head = git(root, "rev-parse", "HEAD")
    blob = f"https://github.com/{origin_repository(root)}/blob/{head}"
    lines = [f"Delivery of the task `{task}` by keyturn.", "",
             "The client decides from these documents; the code is here for the reviews and the record.", ""]
    for section in report_sections(root):
        lines += [section.replace("## ", "### ", 1), ""]
    for name, path in DOCUMENTS:
        if run(["git", "cat-file", "-e", f"HEAD:{path}"], root).returncode == 0:
            lines.append(f"- [{name}]({blob}/{path})")
    lines += ["", f"The task's state is in `keyturn/internal/state/{task}.md`."]
    return "\n".join(lines) + "\n"


def with_description(root: Path, task: str, act) -> None:
    """Write the description to a file, and give its path to act."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as body:
        body.write(description(root, task))
    try:
        act(body.name)
    finally:
        os.unlink(body.name)


def check_base(existing: dict, base: str) -> None:
    if existing["baseRefName"] != base:
        raise Refused(f"{existing['url']} goes to {existing['baseRefName']}, not to the default branch {base}")


def cmd_open(root: Path, task: str) -> None:
    branch = check_task(root, task)
    base = default_branch(root)
    existing = open_pull_request(root, branch)

    def act(body: str) -> None:
        if existing is None:
            url = gh(root, "pr", "create", "--draft", "--base", base, "--head", branch,
                     "--title", f"keyturn: {task}", "--body-file", body).strip()
            print(f"opened {url}")
        else:
            check_base(existing, base)
            gh(root, "pr", "edit", str(existing["number"]), "--body-file", body)
            print(f"updated {existing['url']}")

    with_description(root, task, act)


def cmd_ready(root: Path, task: str) -> None:
    branch = check_task(root, task)
    existing = open_pull_request(root, branch)
    if existing is None:
        raise Refused(f"no open pull request from {branch}: open it first")
    check_base(existing, default_branch(root))
    # Written again from the head, so that what the client reads first is the delivery that is ready.
    with_description(root, task, lambda body: gh(root, "pr", "edit", str(existing["number"]), "--body-file", body))
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
