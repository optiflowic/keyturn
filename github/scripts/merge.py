#!/usr/bin/env python3
"""Merge a task's pull request when its conditions hold, and nothing else (ADR 0042, ADR 0046).

Usage (from inside the project's repository, on the branch task/TASK):
  merge.py TASK [--wait-minutes N]   (deliver passes --wait-minutes 9, so that one call fits in a tool call)

It refuses (exit 1), and never merges, unless all of these hold, in this order:
  - the task's pull request is open, ready for review, goes to the default branch, and its branch is in this repository
    itself (a fork's pull request runs the fork's workflow, ADR 0043);
  - its head is the local HEAD and the task branch on origin;
  - the checks "keyturn gate" and "keyturn conditions" from GitHub Actions on that head have finished and passed; it waits
    for them up to N minutes (default 9), since a push starts them and the merge step comes right after one (ADR 0044);
  - keyturn's conditions check (gates/conditions.sh, next to this script's keyturn copy) passes on that head.
Then it squash-merges the pull request naming that head, so that GitHub refuses the merge if the head moved meanwhile,
and the branch protection refuses it without the required checks. A merge GitHub refused is never tried again.

Exit codes: 0 merged; 1 refused (the message says why); 2 it could not run (a wrong branch, no origin, no gh);
3 the checks have not finished yet (nothing else was wrong so far): run it again later.
Needs Python 3.9 or later, Git, and the GitHub CLI (`gh`). Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_branch  # the same checks of the branch, origin, and pull request as the push
from task_branch import EXIT_DONE, EXIT_REFUSED, EXIT_SETUP, Refused, SetupError, git, run

KEYTURN_ROOT = Path(__file__).resolve().parent.parent.parent
CONDITIONS = KEYTURN_ROOT / "gates" / "conditions.sh"
# The required checks, by the names of the jobs in github/workflows/keyturn-gate.yml, and the app that must have run them.
CHECKS = ("keyturn gate", "keyturn conditions")
CHECKS_APP = "github-actions"
POLL_SECONDS = 30
# GitHub may not show a push on the pull request at once: how long to wait for its head to be the local one.
HEAD_WAIT_SECONDS = 30
EXIT_PENDING = 3


class Pending(Exception):
    """The checks have not finished: not a refusal, the merge step runs again later."""


def remote_head(root: Path, branch: str) -> str:
    """The task branch's commit on origin, read from origin itself (a fetch could be stale)."""
    output = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    heads = [line.split()[0] for line in output.splitlines() if line.endswith(f"\trefs/heads/{branch}")]
    if not heads:
        raise Refused(f"{branch} is not on origin: push it first (task_branch.py push)")
    return heads[0]


def check_runs(root: Path, sha: str) -> dict[str, dict]:
    """The newest run of each required check on the commit, from GitHub Actions only."""
    runs: dict[str, dict] = {}
    page = 1
    while True:
        data = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/commits/{sha}/check-runs?per_page=100&page={page}"))
        for check in data.get("check_runs", []):
            name = check.get("name")
            if name not in CHECKS or (check.get("app") or {}).get("slug") != CHECKS_APP:
                continue
            if name not in runs or check.get("id", 0) > runs[name].get("id", 0):
                runs[name] = check
        if len(data.get("check_runs", [])) < 100:
            return runs
        page += 1


def wait_for_checks(root: Path, sha: str, wait_seconds: float) -> None:
    deadline = time.monotonic() + wait_seconds
    while True:
        runs = check_runs(root, sha)
        pending = [name for name in CHECKS if runs.get(name, {}).get("status") != "completed"]
        if not pending:
            break
        if time.monotonic() >= deadline:
            raise Pending(f"the checks {', '.join(pending)} on {sha[:12]} have not finished (or not started) in "
                          f"{wait_seconds / 60:g} minutes; run merge.py again later")
        time.sleep(POLL_SECONDS)
    failed = [f"{name} ({runs[name].get('conclusion')}, {runs[name].get('html_url', '')})" for name in CHECKS
              if runs[name].get("conclusion") != "success"]
    if failed:
        raise Refused(f"the checks on {sha[:12]} did not pass: {'; '.join(failed)}")


def run_conditions(root: Path, task: str, default: str, sha: str) -> None:
    git(root, "fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{default}:refs/remotes/origin/{default}")
    result = run([str(CONDITIONS), "--task", task, "--default-branch", f"origin/{default}", "--head", sha], root)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise Refused(f"the merge conditions do not hold on {sha[:12]} (conditions.sh exit {result.returncode}):\n{output}")


def cmd_merge(root: Path, task: str, wait_seconds: float) -> None:
    branch = task_branch.check_task(root, task)
    default = task_branch.default_branch(root)
    head = git(root, "rev-parse", "HEAD")
    deadline = time.monotonic() + HEAD_WAIT_SECONDS
    while True:
        pr = task_branch.open_pull_request(root, branch)  # never a fork's: those are left out
        if pr is None or pr.get("headRefOid") == head or time.monotonic() >= deadline:
            break
        time.sleep(5)
    if pr is None:
        raise Refused(f"no open pull request from {branch}")
    task_branch.check_base(pr, default)
    if pr.get("isDraft"):
        raise Refused(f"{pr['url']} is a draft; the deliver step marks it ready first (task_branch.py ready)")
    if pr.get("headRefOid") != head:
        raise Refused(f"{pr['url']} is at {str(pr.get('headRefOid'))[:12]}, not at the local HEAD {head[:12]}; push first")
    if remote_head(root, branch) != head:
        raise Refused(f"{branch} on origin is not at the local HEAD {head[:12]}; push first")
    wait_for_checks(root, head, wait_seconds)
    run_conditions(root, task, default, head)
    # The sha makes GitHub refuse the merge if the head moved after the checks above.
    task_branch.gh_api(root, f"repos/{{repo}}/pulls/{pr['number']}/merge", "-X", "PUT", "-f", "merge_method=squash",
                       "-f", f"sha={head}", "-f", f"commit_title=keyturn: {task} (#{pr['number']})")
    print(f"merged {pr['url']} at {head[:12]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge a task's pull request when its conditions hold (ADR 0046).")
    parser.add_argument("task", help="the task's name; its branch is task/<task>")
    parser.add_argument("--wait-minutes", type=float, default=9, help="how long to wait for the checks (default: 9)")
    args = parser.parse_args()
    try:
        cmd_merge(task_branch.repo_root(), args.task, max(args.wait_minutes, 0) * 60)
    except SetupError as error:
        print(f"setup error: {error}", file=sys.stderr)
        return EXIT_SETUP
    except Pending as error:
        print(f"not yet: {error}", file=sys.stderr)
        return EXIT_PENDING
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_DONE


if __name__ == "__main__":
    sys.exit(main())
