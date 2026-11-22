#!/usr/bin/env python3
"""Merge a task's pull request when its conditions hold, and nothing else (ADR 0042, ADR 0046, ADR 0048).

Usage (from inside the project's repository, on the branch task/TASK):
  merge.py TASK [--wait-minutes N]   (deliver passes --wait-minutes 9, so that one call fits in a tool call)
  merge.py TASK --protection         prints "protected" when the default branch has branch protection (a ruleset or a
                                     classic rule) that requires both checks, "not protected" when GitHub showed both
                                     and neither does, and "not known" when either could not be read (GitHub answers 403
                                     both when the plan has no rulesets and when the token lacks a permission); merges
                                     nothing

It refuses (exit 1), and never merges, unless all of these hold, in this order:
  - the task's pull request is open, ready for review, goes to the default branch, and its branch is in this repository
    itself (a fork's pull request runs the fork's workflow, ADR 0043);
  - its head is the local HEAD and the task branch on origin;
  - that head contains the default branch's tip on origin ("up to date"): a task branch is never updated from the
    default branch (ADR 0031), so when the default branch moved after the task started, the maintainer decides;
  - that head changes nothing under .github/workflows/, so the gate's run on its pull request is the default branch's
    workflow, not one the branch brought (ADR 0049);
  - the newest run of the workflow .github/workflows/keyturn-gate.yml for that head, from a pull_request event in this
    repository, among those with a job named "keyturn gate" or "keyturn conditions" (a draft's run names its jobs
    "... (draft, not checked)", ADR 0051), has finished and passed, and so have its jobs "keyturn gate" and "keyturn
    conditions" (read through GitHub Actions' API, which the agents' token reads with Actions: Read, ADR 0049);
  - the newest run of .github/workflows/keyturn-watch.yml for the default branch's tip, among those that started after
    the last push to the default branch in the repository's activity, passed, and so did its job "keyturn watch", so
    that an old success on a commit the branch was reset to does not count (ADR 0048). When the workflow is not on the
    default branch, it refuses, with branch protection too: protection prevents, but does not find a reset or a deleted
    task branch;
  - the newest run of .github/workflows/keyturn-watch.yml for the head itself (the push of the task branch starts one)
    passed, so that a force push to the task branch, which that run finds, stops the merge too (ADR 0050);
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
# The workflows by their files in the project, and the jobs each run must have passed (ADR 0049): the gate's on the
# pull request's head (github/workflows/keyturn-gate.yml), and the detecting one on the default branch's tip (ADR 0048).
WORKFLOWS_DIR = ".github/workflows/"
GATE_WORKFLOW = ".github/workflows/keyturn-gate.yml"
CHECKS = ("keyturn gate", "keyturn conditions")
WATCH_WORKFLOW = ".github/workflows/keyturn-watch.yml"
WATCH = "keyturn watch"
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


def workflow_runs(root: Path, workflow: str, sha: str) -> list[dict]:
    """The runs of the workflow in that file for the commit, newest first. A run's path can carry the ref after an "@"."""
    found, page = [], 1
    while True:
        data = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/actions/workflows/{Path(workflow).name}/runs"
                                                   f"?head_sha={sha}&per_page=100&page={page}"))
        batch = data.get("workflow_runs", []) if isinstance(data, dict) else []
        found += [item for item in batch
                  if item.get("head_sha") == sha and str(item.get("path", "")).split("@")[0] == workflow]
        if len(batch) < 100:
            break
        page += 1
    return sorted(found, key=lambda item: item.get("id", 0), reverse=True)


def run_jobs(root: Path, item: dict) -> dict[str, dict]:
    """A run's jobs by name."""
    data = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/actions/runs/{item['id']}/jobs?per_page=100"))
    return {job.get("name"): job for job in (data.get("jobs", []) if isinstance(data, dict) else [])}


def run_state(root: Path, item: dict | None, jobs: tuple[str, ...],
              by_name: dict[str, dict] | None = None) -> tuple[str, str]:
    """('passed' | 'pending' | 'failed', why) for a workflow run and the jobs it must have passed."""
    if item is None:
        return "pending", "no run"
    url = item.get("html_url", "")
    if item.get("status") != "completed":
        return "pending", f"has not finished ({url})"
    if item.get("conclusion") != "success":
        return "failed", f"did not pass ({item.get('conclusion')}, {url})"
    if by_name is None:
        by_name = run_jobs(root, item)
    missing = [name for name in jobs if (by_name.get(name) or {}).get("conclusion") != "success"]
    if missing:
        return "failed", (f"the job{'s' if len(missing) > 1 else ''} {', '.join(missing)} did not pass "
                          f"({', '.join(str((by_name.get(name) or {}).get('conclusion', 'no job')) for name in missing)}, {url})")
    return "passed", ""


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
    runs = [item for item in workflow_runs(root, WATCH_WORKFLOW, tip)
            if (started := when(item.get("run_started_at"))) is not None and started >= pushed]
    since = f" since the last push to {default} ({pushed.isoformat()})"
    if not runs:
        return "pending", (f"no run of {WATCH} on {default}'s tip {tip[:12]}{since}; a commit that skipped the workflow "
                           f"gets one at its next scheduled run, or when the maintainer starts it by hand")
    state, why = run_state(root, runs[0], (WATCH,))
    if state == "pending":
        return "pending", f"{WATCH} on {default}'s tip {tip[:12]} {why}"
    if state == "failed":
        return "failed", (f"{WATCH} on {default}'s tip {tip[:12]} {why}: a commit on {default} did not come from a "
                          f"task's pull request merged with the conditions met, or a push rewrote what keyturn trusts, "
                          f"and the maintainer puts it right first (ADR 0048)")
    return "passed", ""


def protection(root: Path, default: str) -> str:
    """'protected' when an active ruleset or a classic rule requires both checks on the default branch; 'not protected'
    when GitHub showed both and neither does; 'not known' when either could not be read. A 403 does not tell a plan
    without rulesets from a token that lacks a permission, so it is never read as "not protected"."""
    contexts: set[str] = set()
    known = True
    try:
        rules = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/rules/branches/{default}"))
        for rule in rules:
            if rule.get("type") == "required_status_checks":
                contexts |= {check.get("context") for check in
                             (rule.get("parameters") or {}).get("required_status_checks", [])}
    except (Refused, SetupError, ValueError, AttributeError, TypeError):
        known = False
    try:
        branch = json.loads(task_branch.gh_api(root, f"repos/{{repo}}/branches/{default}"))
        required = ((branch.get("protection") or {}).get("required_status_checks") or {})
        if branch.get("protected"):
            contexts |= set(required.get("contexts") or [])
            contexts |= {check.get("context") for check in required.get("checks") or []}
    except (Refused, SetupError, ValueError, AttributeError, TypeError):
        known = False
    if set(CHECKS) <= contexts:
        return "protected"
    return "not protected" if known else "not known"


def fetch_default(root: Path, default: str) -> str:
    git(root, "fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{default}:refs/remotes/origin/{default}")
    return git(root, "rev-parse", f"refs/remotes/origin/{default}")


def gate_state(root: Path, head: str) -> tuple[str, str]:
    """The newest run of the gate's workflow for the head, from a pull_request event in this repository, that has a job
    named as one of the checks. A draft's run names its jobs "... (draft, not checked)" and fails them (ADR 0051): it is
    passed over, so that it neither counts as the checks nor hides the run on the ready pull request. A run that lists
    no jobs yet (queued) or none at all is not passed over."""
    repository = task_branch.origin_repository(root)
    runs = [item for item in workflow_runs(root, GATE_WORKFLOW, head)
            if item.get("event") == "pull_request" and (item.get("head_repository") or {}).get("full_name") == repository]
    for item in runs:
        by_name = run_jobs(root, item)
        if by_name and not set(CHECKS) & set(by_name):
            continue
        return run_state(root, item, CHECKS, by_name)
    return run_state(root, None, CHECKS)


def head_watch_state(root: Path, head: str) -> tuple[str, str]:
    """The newest run of keyturn watch for the task's head, which the push of the task branch started (ADR 0050)."""
    runs = workflow_runs(root, WATCH_WORKFLOW, head)
    state, why = run_state(root, runs[0] if runs else None, (WATCH,))
    if state == "failed":
        return "failed", (f"{WATCH} on the task's head {head[:12]} {why}: a push rewrote what keyturn trusts (a force "
                          f"push to a task branch, for example), and the maintainer puts it right first (ADR 0050)")
    if state == "pending":
        return "pending", (f"{WATCH} on the task's head {head[:12]}: {why}; the push of the task branch starts it, "
                           f"unless the push skipped workflows")
    return "passed", ""


def wait_for_checks(root: Path, head: str, default: str, tip: str, wait_seconds: float) -> None:
    deadline = time.monotonic() + wait_seconds
    while True:
        gate, gate_why = gate_state(root, head)
        if gate == "failed":
            raise Refused(f"the checks {', '.join(CHECKS)} on {head[:12]} did not pass: {GATE_WORKFLOW} {gate_why}")
        state, why = watch_state(root, default, tip)
        if state == "failed":
            raise Refused(why)
        on_head, head_why = head_watch_state(root, head)
        if on_head == "failed":
            raise Refused(head_why)
        if gate == "passed" and state == "passed" and on_head == "passed":
            return
        if time.monotonic() >= deadline:
            waiting = [f"the checks {', '.join(CHECKS)} on {head[:12]} have not finished (or not started): "
                       f"{GATE_WORKFLOW} {gate_why}"] if gate == "pending" else []
            waiting += [why] if state == "pending" else []
            waiting += [head_why] if on_head == "pending" else []
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
    try:
        # A fetch that times out raises SetupError too: the pull request is merged, so that is not "could not run".
        run(["git", "fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{default}:refs/remotes/origin/{default}"], root)
        if run(["git", "cat-file", "-e", f"{merge_sha}^{{commit}}"], root).returncode != 0:
            run(["git", "fetch", "--quiet", "--no-tags", "origin", merge_sha], root)
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
    if git(root, "diff", "--name-only", "--no-renames", tip, head, "--", WORKFLOWS_DIR):
        raise Refused(f"{branch} at {head[:12]} changes files under {WORKFLOWS_DIR}: the gate's run on its pull request "
                      f"would be the branch's own workflow, not the default branch's (ADR 0049); the maintainer decides")
    if run(["git", "cat-file", "-e", f"{tip}:{WATCH_WORKFLOW}"], root).returncode != 0:
        raise Refused(f"{WATCH_WORKFLOW} is not on {default}: add the {WATCH} workflow as the one-time setup says; it is "
                      f"needed with branch protection too (ADR 0048)")
    wait_for_checks(root, head, default, tip, wait_seconds)
    run_conditions(root, task, default, head)
    # The sha makes GitHub refuse the merge if the head moved after the checks above.
    try:
        answer = task_branch.gh_api(root, f"repos/{{repo}}/pulls/{pr['number']}/merge", "-X", "PUT",
                                    "-f", "merge_method=squash", "-f", f"sha={head}",
                                    "-f", f"commit_title=keyturn: {task} (#{pr['number']})",
                                    # A message of its own, not GitHub's list of the task's commit messages: one with
                                    # [skip ci] would keep keyturn watch from running on the merge (ADR 0048).
                                    "-f", f"commit_message=Merged by keyturn's merge.py after its checks (task {task}).")
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
            print(protection(root, task_branch.default_branch(root)))
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
