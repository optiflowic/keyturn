#!/usr/bin/env python3
"""Merge a task's pull request when its conditions hold, and nothing else (ADR 0042, ADR 0046, ADR 0048).

Usage (from inside the project's repository, on the branch task/TASK):
  merge.py TASK [--wait-minutes N]   (deliver passes --wait-minutes 9, so that one call fits in a tool call)
  merge.py TASK --protection         prints "protected" when the default branch has branch protection (a ruleset or a
                                     classic rule) that requires both checks, and "not protected" otherwise; merges nothing

It refuses (exit 1), and never merges, unless all of these hold, in this order:
  - the task's pull request is open, ready for review, goes to the default branch, and its branch is in this repository
    itself (a fork's pull request runs the fork's workflow, ADR 0043);
  - its head is the local HEAD and the task branch on origin;
  - that head contains the default branch's tip on origin ("up to date"): a task branch is never updated from the
    default branch (ADR 0031), so when the default branch moved after the task started, the maintainer decides;
  - the checks "keyturn gate" and "keyturn conditions" from GitHub Actions on that head have finished and passed;
  - the check "keyturn watch" from GitHub Actions on the default branch's tip passed, in a run that started after the
    last push to the default branch in the repository's activity, so that an old success on a commit the branch was
    reset to does not count (ADR 0048). When the workflow is not on the default branch, it refuses, unless the default
    branch's protection requires both checks;
  - keyturn's conditions check (gates/conditions.sh, next to this script's keyturn copy) passes on that head.
It waits for the checks up to N minutes (default 9), since a push starts them and the merge step comes right after one
(ADR 0044). Then it squash-merges the pull request naming that head, so that GitHub refuses the merge if the head moved
meanwhile. A merge GitHub refused is never tried again. After merging, it checks that the merge commit's only parent is
the tip it checked and that its tree is the head's, since the default branch can move between the check and the merge.

Exit codes: 0 merged (also when the merge call failed but GitHub shows the pull request merged); 1 refused (the
message says why; the pull request is not merged); 2 it could not run (a wrong branch, no origin, no gh);
3 the checks have not finished yet (nothing else was wrong so far): run it again later; 4 merged, but the merge commit
is not the checked head on the checked tip, or could not be checked: the maintainer looks at it, and "keyturn watch"
fails on it too.
Needs Python 3.9 or later, Git, and the GitHub CLI (`gh`). Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_branch  # the same checks of the branch, origin, and pull request as the push
from task_branch import EXIT_DONE, EXIT_REFUSED, EXIT_SETUP, Refused, SetupError, git, run

KEYTURN_ROOT = Path(__file__).resolve().parent.parent.parent
CONDITIONS = KEYTURN_ROOT / "gates" / "conditions.sh"
# The required checks, by the names of the jobs in github/workflows/keyturn-gate.yml, and the app that must have run them.
CHECKS = ("keyturn gate", "keyturn conditions")
CHECKS_APP = "github-actions"
# The detecting check on the default branch's tip, and the file of its workflow in the project (ADR 0048).
WATCH = "keyturn watch"
WATCH_WORKFLOW = ".github/workflows/keyturn-watch.yml"
POLL_SECONDS = 30
# GitHub may not show a push on the pull request at once: how long to wait for its head to be the local one.
HEAD_WAIT_SECONDS = 30
EXIT_PENDING = 3
EXIT_MERGED_UNCHECKED = 4


class Pending(Exception):
    """The checks have not finished: not a refusal, the merge step runs again later."""


class MergedUnchecked(Exception):
    """Merged, but the merge commit is not what was checked: the maintainer looks at it."""


def remote_head(root: Path, branch: str) -> str:
    """The branch's commit on origin, read from origin itself (a fetch could be stale)."""
    output = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    heads = [line.split()[0] for line in output.splitlines() if line.endswith(f"\trefs/heads/{branch}")]
    if not heads:
        raise Refused(f"{branch} is not on origin: push it first (task_branch.py push)")
    return heads[0]


def check_runs(root: Path, sha: str, names: tuple[str, ...]) -> dict[str, list[dict]]:
    """Every run of each named check on the commit, from GitHub Actions only, newest first."""
    runs: dict[str, list[dict]] = {name: [] for name in names}
    page = 1
    while True:
        data = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/commits/{sha}/check-runs?per_page=100&page={page}"))
        for check in data.get("check_runs", []):
            name = check.get("name")
            if name in runs and (check.get("app") or {}).get("slug") == CHECKS_APP:
                runs[name].append(check)
        if len(data.get("check_runs", [])) < 100:
            break
        page += 1
    for found in runs.values():
        found.sort(key=lambda check: check.get("id", 0), reverse=True)
    return runs


def when(text: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def last_push(root: Path, default: str, tip: str) -> datetime | None:
    """When the default branch last changed to the tip, from the repository's activity; None when the activity does
    not show the tip yet (it may lag a push). An activity that lists nothing is a refusal: without it, an old success
    on a commit the branch was reset to cannot be told from a new one (ADR 0048)."""
    try:
        data = json.loads(task_branch.gh_api(
            root, f"repos/{{repo}}/activity?ref=refs/heads/{default}&direction=desc&per_page=1"))
    except ValueError:
        raise Refused(f"the repository's activity for {default} is not JSON") from None
    if not isinstance(data, list) or not data:
        raise Refused(f"the repository's activity lists no push to {default}, so a run of {WATCH} after the last push "
                      f"cannot be told from an old one; the maintainer looks at it (ADR 0048)")
    activity = data[0]
    if activity.get("after") != tip:
        return None
    pushed = when(activity.get("timestamp"))
    if pushed is None:
        raise Refused(f"the repository's activity gives no time for the last push to {default}")
    return pushed


def watch_state(root: Path, default: str, tip: str) -> tuple[str, str]:
    """('passed' | 'pending' | 'failed', why) for keyturn watch on the tip, counting only runs after the last push."""
    pushed = last_push(root, default, tip)
    if pushed is None:
        return "pending", f"the repository's activity does not show {default} at {tip[:12]} yet"
    runs = [check for check in check_runs(root, tip, (WATCH,))[WATCH]
            if (started := when(check.get("started_at"))) is not None and started >= pushed]
    since = f" since the last push to {default} ({pushed.isoformat()})"
    if not runs:
        return "pending", (f"no run of {WATCH} on {default}'s tip {tip[:12]}{since}; a commit that skipped the workflow "
                           f"gets one at its next scheduled run, or when the maintainer starts it by hand")
    newest = runs[0]
    if newest.get("status") != "completed":
        return "pending", f"{WATCH} on {default}'s tip {tip[:12]} has not finished"
    if newest.get("conclusion") != "success":
        return "failed", (f"{WATCH} on {default}'s tip {tip[:12]} did not pass ({newest.get('conclusion')}, "
                          f"{newest.get('html_url', '')}): a commit on {default} did not come from a task's pull request "
                          f"merged with the conditions met, and the maintainer puts it right first (ADR 0048)")
    return "passed", ""


def protected(root: Path, default: str) -> bool:
    """Whether the default branch's protection (an active ruleset, or a classic rule) requires both checks."""
    contexts: set[str] = set()
    try:
        for rule in json.loads(task_branch.gh_api(root, f"repos/{{repo}}/rules/branches/{default}")):
            if rule.get("type") == "required_status_checks":
                contexts |= {check.get("context") for check in
                             (rule.get("parameters") or {}).get("required_status_checks", [])}
    except (Refused, ValueError, AttributeError):
        pass
    try:
        branch = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/branches/{default}"))
        required = ((branch.get("protection") or {}).get("required_status_checks") or {})
        if branch.get("protected"):
            contexts |= set(required.get("contexts") or [])
            contexts |= {check.get("context") for check in required.get("checks") or []}
    except (Refused, ValueError, AttributeError):
        pass
    return set(CHECKS) <= contexts


def fetch_default(root: Path, default: str) -> str:
    git(root, "fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{default}:refs/remotes/origin/{default}")
    return git(root, "rev-parse", f"refs/remotes/origin/{default}")


def wait_for_checks(root: Path, head: str, default: str, tip: str, watch: bool, wait_seconds: float) -> None:
    deadline = time.monotonic() + wait_seconds
    while True:
        runs = check_runs(root, head, CHECKS)
        pending = [name for name in CHECKS if not runs[name] or runs[name][0].get("status") != "completed"]
        failed = [f"{name} ({runs[name][0].get('conclusion')}, {runs[name][0].get('html_url', '')})"
                  for name in CHECKS if name not in pending and runs[name][0].get("conclusion") != "success"]
        if failed:
            raise Refused(f"the checks on {head[:12]} did not pass: {'; '.join(failed)}")
        state, why = watch_state(root, default, tip) if watch else ("passed", "")
        if state == "failed":
            raise Refused(why)
        if not pending and state == "passed":
            return
        if time.monotonic() >= deadline:
            waiting = [f"the checks {', '.join(pending)} on {head[:12]} have not finished (or not started)"] if pending else []
            waiting += [why] if state == "pending" else []
            raise Pending(f"{'; '.join(waiting)}, in {wait_seconds / 60:g} minutes; run merge.py again later")
        time.sleep(POLL_SECONDS)


def run_conditions(root: Path, task: str, default: str, sha: str) -> None:
    result = run([str(CONDITIONS), "--task", task, "--default-branch", f"origin/{default}", "--head", sha], root)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise Refused(f"the merge conditions do not hold on {sha[:12]} (conditions.sh exit {result.returncode}):\n{output}")


def check_merge_commit(root: Path, default: str, merge_sha: str | None, head: str, tip: str) -> None:
    """The merge commit's only parent is the checked tip, and its tree is the head's (ADR 0048)."""
    if not merge_sha:
        raise MergedUnchecked("GitHub gave no merge commit to check")
    run(["git", "fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{default}:refs/remotes/origin/{default}"], root)
    if run(["git", "cat-file", "-e", f"{merge_sha}^{{commit}}"], root).returncode != 0:
        run(["git", "fetch", "--quiet", "--no-tags", "origin", merge_sha], root)
    try:
        parents = git(root, "rev-list", "--parents", "-n", "1", merge_sha).split()[1:]
        same_tree = git(root, "rev-parse", f"{merge_sha}^{{tree}}") == git(root, "rev-parse", f"{head}^{{tree}}")
    except SetupError as error:
        raise MergedUnchecked(f"the merge commit {merge_sha[:12]} could not be read: {error}") from None
    if parents != [tip]:
        raise MergedUnchecked(f"the merge commit {merge_sha[:12]} has the parents {', '.join(p[:12] for p in parents) or 'none'}, "
                              f"not the checked tip {tip[:12]} of {default} alone: {default} moved between the check and "
                              f"the merge")
    if not same_tree:
        raise MergedUnchecked(f"the merge commit {merge_sha[:12]} does not have the tree of the checked head {head[:12]}")


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
        if remote_head(root, branch) == head:  # pushed: GitHub has not shown it on the pull request yet
            raise Pending(f"{branch} on origin is at {head[:12]}, but {pr['url']} still shows "
                          f"{str(pr.get('headRefOid'))[:12]}; run merge.py again later")
        raise Refused(f"{pr['url']} is at {str(pr.get('headRefOid'))[:12]}, not at the local HEAD {head[:12]}; push first")
    if remote_head(root, branch) != head:
        raise Refused(f"{branch} on origin is not at the local HEAD {head[:12]}; push first")
    tip = fetch_default(root, default)
    if run(["git", "merge-base", "--is-ancestor", tip, head], root).returncode != 0:
        raise Refused(f"{branch} at {head[:12]} does not contain the tip {tip[:12]} of {default}: {default} moved after "
                      f"the task started, and a task branch is never updated from it (ADR 0031); the maintainer decides")
    watch = run(["git", "cat-file", "-e", f"{tip}:{WATCH_WORKFLOW}"], root).returncode == 0
    if not watch:
        if not protected(root, default):
            raise Refused(f"{WATCH_WORKFLOW} is not on {default}, and {default} has no branch protection that requires "
                          f"{' and '.join(CHECKS)}: add the {WATCH} workflow as the one-time setup says (ADR 0048)")
        print(f"note: {WATCH_WORKFLOW} is not on {default}; its branch protection requires the checks", file=sys.stderr)
    wait_for_checks(root, head, default, tip, watch, wait_seconds)
    run_conditions(root, task, default, head)
    # The sha makes GitHub refuse the merge if the head moved after the checks above.
    try:
        answer = task_branch.gh_api(root, f"repos/{{repo}}/pulls/{pr['number']}/merge", "-X", "PUT",
                                    "-f", "merge_method=squash", "-f", f"sha={head}",
                                    "-f", f"commit_title=keyturn: {task} (#{pr['number']})")
        try:
            merge_sha = json.loads(answer).get("sha")
        except (ValueError, AttributeError):
            merge_sha = None
    except (Refused, SetupError) as error:
        # A failed answer (or none, on a timeout) does not prove that nothing was merged: look before saying so, so
        # that a merged task is never recorded as stopped (a later state commit would be work not merged).
        state = pull_request(root, pr["number"])
        if not state.get("merged"):
            raise
        print(f"note: the merge call failed ({error}), but the pull request is merged", file=sys.stderr)
        merge_sha = state.get("merge_commit_sha")
    if not merge_sha:
        merge_sha = pull_request(root, pr["number"]).get("merge_commit_sha")
    try:
        # Also brings the local default branch up to the merge, so that `task_state.py unmerged` sees it at once.
        check_merge_commit(root, default, merge_sha, head, tip)
    except MergedUnchecked as error:
        raise MergedUnchecked(f"{pr['url']} is merged, but {error}; the maintainer looks at it, and {WATCH} fails on "
                              f"it too (ADR 0048)") from None
    print(f"merged {pr['url']} at {head[:12]}")


def pull_request(root: Path, number: int) -> dict:
    """The pull request as GitHub shows it now; a failed look is an empty one (not merged)."""
    try:
        data = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/pulls/{number}"))
    except (Refused, SetupError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge a task's pull request when its conditions hold (ADR 0046).")
    parser.add_argument("task", help="the task's name; its branch is task/<task>")
    parser.add_argument("--wait-minutes", type=float, default=9, help="how long to wait for the checks (default: 9)")
    parser.add_argument("--protection", action="store_true",
                        help="print whether the default branch's protection requires both checks, and merge nothing")
    args = parser.parse_args()
    try:
        root = task_branch.repo_root()
        if args.protection:
            task_branch.check_task(root, args.task)
            print("protected" if protected(root, task_branch.default_branch(root)) else "not protected")
            return EXIT_DONE
        cmd_merge(root, args.task, max(args.wait_minutes, 0) * 60)
    except SetupError as error:
        print(f"setup error: {error}", file=sys.stderr)
        return EXIT_SETUP
    except Pending as error:
        print(f"not yet: {error}", file=sys.stderr)
        return EXIT_PENDING
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except MergedUnchecked as error:
        print(f"merged, not as checked: {error}", file=sys.stderr)
        return EXIT_MERGED_UNCHECKED
    return EXIT_DONE


if __name__ == "__main__":
    sys.exit(main())
