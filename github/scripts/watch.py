#!/usr/bin/env python3
"""Detect commits on the default branch that did not come from a task's pull request merged with its conditions met,
and pushes that rewrote what keyturn trusts (ADR 0048, layer 2).

Usage (in the project's workflow keyturn-watch.yml, from the root of a full clone of the project; github/README.md):
  watch.py --start SHA [--wait-minutes N]

It reads these from the environment, which GitHub Actions sets: GITHUB_REPOSITORY, GITHUB_EVENT_NAME,
GITHUB_EVENT_PATH, GITHUB_RUN_ID, GITHUB_SERVER_URL, GH_TOKEN (the workflow's GITHUB_TOKEN), and the repository
variables the workflow passes on, which the agents' token cannot change: KEYTURN_VOUCHED (the full SHAs of the
maintainer's own commits on the default branch, separated by spaces, commas, or new lines), KEYTURN_CHECKED_UNTIL (an
ISO 8601 time; the activity up to it was looked at by the maintainer), and KEYTURN_MAINTAINER (the GitHub account the
issue mentions; a run without it fails, since what it found would reach nobody).

Each run checks, and fails on any of these:
  - every commit on the default branch's first-parent history after SHA, up to the tip: each passes only when it is
    listed in KEYTURN_VOUCHED, changes only files under .github/workflows/, or is the merge commit of a merged pull
    request from a task/<task> branch of this repository to the default branch, with one parent, the tree of that pull
    request's head, a head that contains its parent and changes nothing under .github/workflows/ (so the gate ran as the
    default branch's workflow, ADR 0049), the newest run of .github/workflows/keyturn-gate.yml for that head, from a
    pull_request event in this repository, among those with a job named "keyturn gate" or "keyturn conditions" (a
    draft's run names its jobs "... (draft, not checked)", ADR 0051), passed with its jobs "keyturn gate" and "keyturn
    conditions" (GitHub Actions' API, ADR 0049), and keyturn's conditions check (gates/conditions.sh, next to this script's keyturn copy) passing on it
    again;
  - SHA is not an ancestor of the tip, and the default branch's tip of the newest earlier passing run is not either;
  - the repository's activity after the checkpoint (the later of KEYTURN_CHECKED_UNTIL and the start of the newest
    earlier passing run, less an hour, since the activity can lag): a force push or a deletion of the default branch, a
    push to it whose commit is no longer on it, a force push to a task/** branch, and the deletion of one. A run started
    by a push or a deletion first waits up to N minutes (default 5) for the activity to list it.
When a run fails, it opens an issue that mentions the maintainer, or comments on the open one when what it found
changed. Nothing it prints or posts mentions anyone else: an "@" from a commit, a branch, or a report is broken.

Exit codes: 0 everything passed; 1 something did not (the message says what, and the issue lists it); 2 it could not
run (no full clone, no gh, a variable that is not valid): an issue is opened then too, when it can be.
Needs Python 3.9 or later, Git, and the GitHub CLI (`gh`). Uses only the standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_branch import TASK_RE, SetupError, run  # the same task names, and the same way to run git and gh

KEYTURN_ROOT = Path(__file__).resolve().parent.parent.parent
CONDITIONS = KEYTURN_ROOT / "gates" / "conditions.sh"
WORKFLOW = "keyturn-watch.yml"
WORKFLOWS_DIR = ".github/workflows/"
GATE_WORKFLOW = ".github/workflows/keyturn-gate.yml"
CHECKS = ("keyturn gate", "keyturn conditions")
ZERO = "0" * 40
SHA_RE = re.compile(r"[0-9a-f]{40}")
LOGIN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
# The activity can lag a push: a checkpoint taken from a passing run reads this much before it again.
ACTIVITY_OVERLAP = timedelta(hours=1)
POLL_SECONDS = 20
MARKER = "keyturn-watch"
MARKER_RE = re.compile(r"<!-- keyturn-watch: ([0-9a-f]{64}) -->")
BOT = "github-actions[bot]"
EXIT_PASS, EXIT_FAIL, EXIT_SETUP = 0, 1, 2


@dataclass(frozen=True)
class Finding:
    where: str  # a commit, a push, or a branch
    why: str

    def line(self) -> str:
        return f"{self.where}: {self.why}"


@dataclass
class Settings:
    repository: str
    start: str
    vouched: set[str] = field(default_factory=set)
    checked_until: datetime | None = None
    maintainer: str | None = None
    event_name: str = ""
    event: dict = field(default_factory=dict)
    run_id: int | None = None
    run_url: str = ""
    wait_seconds: float = 300
    conditions: Path = CONDITIONS


def when(text) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def quiet(text: str) -> str:
    """Text from commits, branches, and reports, with each "@" broken so that it mentions nobody."""
    return text.replace("@", "@​")


class GitHub:
    """The few GitHub REST calls the watch makes, through gh, with the workflow's GITHUB_TOKEN."""

    def __init__(self, repository: str):
        self.repository = repository

    def call(self, endpoint: str, *args: str) -> str:
        try:
            result = run(["gh", "api", endpoint.replace("{repo}", self.repository), *args])
        except FileNotFoundError:
            raise SetupError("the GitHub CLI (gh) is not installed") from None
        if result.returncode != 0:
            raise SetupError(f"gh api {endpoint}: {(result.stderr or result.stdout).strip() or 'failed'}")
        return result.stdout

    def get(self, endpoint: str):
        try:
            return json.loads(self.call(endpoint))
        except ValueError:
            raise SetupError(f"gh api {endpoint}: the answer is not JSON") from None

    def default_branch(self) -> str:
        return str(self.get("repos/{repo}").get("default_branch") or "")

    def on_branch(self, sha: str, branch: str) -> bool:
        """Whether the commit is on the branch as GitHub has it now (the branch may have moved after the clone)."""
        try:
            status = self.get(f"repos/{{repo}}/compare/{sha}...{branch}?per_page=1").get("status")
        except SetupError:
            return False
        return status in ("identical", "ahead")

    def pulls_of(self, sha: str) -> list[dict]:
        return self.get(f"repos/{{repo}}/commits/{sha}/pulls?per_page=100")

    def workflow_runs(self, workflow: str, sha: str) -> list[dict]:
        """The runs of the workflow in that file (its path in the repository) for the commit."""
        runs, page = [], 1
        while True:
            data = self.get(f"repos/{{repo}}/actions/workflows/{Path(workflow).name}/runs?head_sha={sha}"
                            f"&per_page=100&page={page}")
            runs += data.get("workflow_runs", [])
            if len(data.get("workflow_runs", [])) < 100:
                return runs
            page += 1

    def jobs(self, run_id: int) -> list[dict]:
        return self.get(f"repos/{{repo}}/actions/runs/{run_id}/jobs?per_page=100").get("jobs", [])

    def activity(self, since: datetime) -> list[dict]:
        """The repository's activity after `since`, newest first (the activity pages by a cursor, in the Link header)."""
        found, endpoint = [], "repos/{repo}/activity?direction=desc&per_page=100"
        while endpoint:
            raw = self.call(endpoint, "--include")
            head, _, body = raw.replace("\r\n", "\n").partition("\n\n")
            try:
                page = json.loads(body)
            except ValueError:
                raise SetupError("the repository's activity is not JSON") from None
            found += page
            older = [item for item in page if (moment := when(item.get("timestamp"))) and moment <= since]
            # GitHub names the next page by the repository's ID (https://api.github.com/repositories/<id>/activity?...).
            link = re.search(r'<https://[^/>]+/([^>]+)>;\s*rel="next"', head)
            endpoint = link.group(1) if link and page and not older else ""
        return found

    def passing_runs(self) -> list[dict]:
        return self.get(f"repos/{{repo}}/actions/workflows/{WORKFLOW}/runs?status=success&exclude_pull_requests=true"
                        f"&per_page=100").get("workflow_runs", [])

    def open_issues(self) -> list[dict]:
        return self.get(f"repos/{{repo}}/issues?state=open&creator={BOT}&per_page=100")

    def create_issue(self, title: str, body: str) -> str:
        return str(json.loads(self.call("repos/{repo}/issues", "-X", "POST", "-f", f"title={title}",
                                        "-f", f"body={body}")).get("html_url", ""))

    def comments(self, number: int) -> list[dict]:
        return self.get(f"repos/{{repo}}/issues/{number}/comments?per_page=100")

    def comment(self, number: int, body: str) -> None:
        self.call(f"repos/{{repo}}/issues/{number}/comments", "-X", "POST", "-f", f"body={body}")


def git(root: Path, *args: str) -> str:
    result = run(["git", *args], root)
    if result.returncode != 0:
        raise SetupError(f"git {' '.join(args)}: {result.stderr.strip() or 'failed'}")
    return result.stdout.strip()


def has_commit(root: Path, sha: str) -> bool:
    return run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], root).returncode == 0


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return run(["git", "merge-base", "--is-ancestor", older, newer], root).returncode == 0


def short(sha: str) -> str:
    return sha[:12]


class Watch:
    def __init__(self, root: Path, github: GitHub, settings: Settings):
        self.root, self.github, self.settings = root, github, settings
        self.findings: list[Finding] = []

    def find(self, where: str, why: str) -> None:
        finding = Finding(quiet(where), quiet(why))
        if finding not in self.findings:
            self.findings.append(finding)

    def run(self) -> list[Finding]:
        default = self.github.default_branch()
        if not default:
            raise SetupError("GitHub gives no default branch for the repository")
        self.default = default
        tip_ref = f"refs/remotes/origin/{default}"
        if run(["git", "rev-parse", "--verify", "--quiet", tip_ref], self.root).returncode != 0:
            raise SetupError(f"{tip_ref} is not in the clone: check out the project with fetch-depth: 0")
        self.tip = git(self.root, "rev-parse", tip_ref)
        self.check_history()
        self.wait_for_event()
        self.check_activity()
        return self.findings

    # The commits on the default branch.

    def check_history(self) -> None:
        start, tip = self.settings.start, self.tip
        if not has_commit(self.root, start) or not is_ancestor(self.root, start, tip):
            self.find(f"the starting commit {short(start)}",
                      f"is no longer an ancestor of {self.default}'s tip {short(tip)}: {self.default} was rewritten")
            return
        for sha in git(self.root, "rev-list", "--first-parent", "--reverse", f"{start}..{tip}").split():
            self.check_commit(sha)

    def check_commit(self, sha: str) -> None:
        where = f"the commit {short(sha)} on {self.default}"
        if sha in self.settings.vouched:
            return
        parents = git(self.root, "rev-list", "--parents", "-n", "1", sha).split()[1:]
        changed = git(self.root, "diff", "--name-only", "--no-renames", parents[0], sha).splitlines() if parents else []
        if changed and all(path.startswith(WORKFLOWS_DIR) for path in changed):
            return
        try:
            pulls = self.github.pulls_of(sha)
        except SetupError as error:
            self.find(where, f"its pull request could not be read: {error}")
            return
        merged = [pr for pr in pulls if isinstance(pr, dict) and pr.get("merged_at") and pr.get("merge_commit_sha") == sha
                  and (pr.get("base") or {}).get("ref") == self.default]
        if not merged:
            self.find(where, "is not the merge commit of a merged pull request to it, and nobody vouched for it "
                             "(KEYTURN_VOUCHED)")
            return
        pr = merged[0]
        number = f"#{pr.get('number')}"
        head = pr.get("head") or {}
        branch, head_sha = str(head.get("ref") or ""), str(head.get("sha") or "")
        if (head.get("repo") or {}).get("full_name") != self.settings.repository:
            self.find(where, f"came from {number}, whose branch is not in this repository")
            return
        if not branch.startswith("task/") or TASK_RE.fullmatch(branch[len("task/"):]) is None:
            self.find(where, f"came from {number}, whose branch `{branch}` is not a task's (task/<task>)")
            return
        task = branch[len("task/"):]
        if len(parents) != 1:
            self.find(where, f"came from {number}, but has {len(parents)} parents, not one (a squash merge has one)")
            return
        if not SHA_RE.fullmatch(head_sha) or not has_commit(self.root, head_sha):
            self.find(where, f"came from {number}, whose head {short(head_sha)} is not in the clone")
            return
        if git(self.root, "rev-parse", f"{sha}^{{tree}}") != git(self.root, "rev-parse", f"{head_sha}^{{tree}}"):
            self.find(where, f"does not have the tree of {number}'s head {short(head_sha)}: what was merged is not "
                             f"what was checked")
        if not is_ancestor(self.root, parents[0], head_sha):
            self.find(where, f"{number}'s head {short(head_sha)} does not contain its parent {short(parents[0])}: the "
                             f"head was not up to date")
        elif git(self.root, "diff", "--name-only", "--no-renames", parents[0], head_sha, "--", WORKFLOWS_DIR):
            self.find(where, f"{number}'s head {short(head_sha)} changes files under {WORKFLOWS_DIR}, so the gate's "
                             f"run on it was the branch's own workflow")
        self.check_head_checks(where, number, head_sha)
        self.check_conditions(where, number, task, parents[0], head_sha)

    def check_head_checks(self, where: str, number: str, head_sha: str) -> None:
        try:
            runs = [item for item in self.github.workflow_runs(GATE_WORKFLOW, head_sha)
                    if item.get("head_sha") == head_sha and str(item.get("path", "")).split("@")[0] == GATE_WORKFLOW
                    and item.get("event") == "pull_request"
                    and (item.get("head_repository") or {}).get("full_name") == self.settings.repository]
            # The newest run with a job named as one of the checks: a draft's run names its jobs "... (draft, not
            # checked)" and is passed over (ADR 0051). A run with no jobs at all is not.
            newest, jobs = None, {}
            for item in sorted(runs, key=lambda item: item.get("id", 0), reverse=True):
                jobs = {job.get("name"): job for job in self.github.jobs(int(item["id"]))}
                if not jobs or set(CHECKS) & set(jobs):
                    newest = item
                    break
            if newest is None:
                self.find(where, f"{GATE_WORKFLOW} has no run from its pull request on {number}'s head {short(head_sha)}"
                                 + (" that is not a draft's" if runs else ""))
                return
            if newest.get("status") != "completed" or newest.get("conclusion") != "success":
                self.find(where, f"{GATE_WORKFLOW} on {number}'s head {short(head_sha)} did not pass "
                                 f"({newest.get('conclusion') or newest.get('status')})")
                return
        except SetupError as error:
            self.find(where, f"the checks on {number}'s head could not be read: {error}")
            return
        for name in CHECKS:
            if (jobs.get(name) or {}).get("conclusion") != "success":
                self.find(where, f"{name} on {number}'s head {short(head_sha)} did not pass "
                                 f"({(jobs.get(name) or {}).get('conclusion', 'no job')})")

    def check_conditions(self, where: str, number: str, task: str, parent: str, head_sha: str) -> None:
        result = run([str(self.settings.conditions), "--task", task, "--default-branch", parent, "--head", head_sha],
                     self.root)
        if result.returncode != 0:
            failed = [line for line in (result.stdout + result.stderr).splitlines()
                      if line.startswith(("FAIL", "setup error"))]
            self.find(where, f"the merge conditions do not hold on {number}'s head {short(head_sha)} (conditions.sh "
                             f"exit {result.returncode}): {'; '.join(failed[:5]) or 'no reason given'}")

    # The repository's activity: what the history alone cannot show.

    def event_activity(self) -> tuple[str, str, str] | None:
        """(ref, after, kind) of the push or deletion that started this run, when it is one the activity must list."""
        event, name = self.settings.event, self.settings.event_name
        if name == "push" and str(event.get("ref", "")).startswith("refs/heads/"):
            return str(event["ref"]), str(event.get("after", "")), "push"
        if name == "delete" and event.get("ref_type") == "branch" and event.get("ref"):
            return f"refs/heads/{event['ref']}", ZERO, "deletion"
        return None

    def wait_for_event(self) -> None:
        expected = self.event_activity()
        if expected is None:
            return
        ref, after, kind = expected
        since = (datetime.now(timezone.utc) - ACTIVITY_OVERLAP)
        deadline = time.monotonic() + self.settings.wait_seconds
        while True:
            for item in self.github.activity(since):
                if item.get("ref") != ref:
                    continue
                if kind == "deletion" and item.get("activity_type") == "branch_deletion":
                    return
                if kind == "push" and item.get("after") == after:
                    return
            if time.monotonic() >= deadline:
                forced = " (a force push, by the event)" if self.settings.event.get("forced") else ""
                self.find(f"the {kind} of `{ref}` that started this run{forced}",
                          f"the repository's activity does not list it after {self.settings.wait_seconds / 60:g} "
                          f"minutes, so it could not be checked")
                return
            time.sleep(POLL_SECONDS)

    def checkpoint(self) -> tuple[datetime | None, dict | None]:
        """The time the activity is read after, and the newest earlier passing run on the default branch."""
        runs = [item for item in self.github.passing_runs()
                if item.get("id") != self.settings.run_id and when(item.get("run_started_at")) is not None]
        runs.sort(key=lambda item: when(item["run_started_at"]), reverse=True)
        on_default = next((item for item in runs if item.get("head_branch") == self.default), None)
        moments = [self.settings.checked_until] if self.settings.checked_until else []
        if runs:
            moments.append(when(runs[0]["run_started_at"]) - ACTIVITY_OVERLAP)
        return (max(moments) if moments else None), on_default

    def check_activity(self) -> None:
        since, last_on_default = self.checkpoint()
        if last_on_default is not None:
            checked = str(last_on_default.get("head_sha", ""))
            if not has_commit(self.root, checked) or not is_ancestor(self.root, checked, self.tip):
                self.find(f"{self.default}'s tip {short(checked)} that the last passing run checked",
                          f"is no longer an ancestor of the tip {short(self.tip)}: {self.default} was reset or rewritten")
        if since is None:
            self.find("the repository's activity", "there is no passing run to read it after, and "
                      "KEYTURN_CHECKED_UNTIL is not set: set it to the time the workflow was added (github/README.md)")
            return
        default_ref = f"refs/heads/{self.default}"
        items = [item for item in self.github.activity(since) if (moment := when(item.get("timestamp"))) and moment > since]
        for item in sorted(items, key=lambda item: when(item["timestamp"])):
            ref, kind = str(item.get("ref", "")), str(item.get("activity_type", ""))
            after = str(item.get("after", ""))
            actor = (item.get("actor") or {}).get("login", "someone")
            where = f"`{ref}` at {item.get('timestamp')} by `{actor}`"
            if ref == default_ref:
                if kind in ("force_push", "branch_deletion"):
                    self.find(where, f"a {kind.replace('_', ' ')} of the default branch")
                elif after != ZERO and not (has_commit(self.root, after) and is_ancestor(self.root, after, self.tip)) \
                        and not self.github.on_branch(after, self.default):
                    # A push after the clone is still on the branch as GitHub has it: the run it started checks it.
                    self.find(where, f"a {kind.replace('_', ' ')} of {short(after)}, which is no longer on {self.default}")
            elif ref.startswith("refs/heads/task/"):
                if kind == "force_push":
                    self.find(where, "a force push to a task branch, whose history keyturn trusts (ADR 0043)")
                elif kind == "branch_deletion":
                    self.find(where, "the deletion of a task branch, which is kept as the task's record (ADR 0047)")


def report(github: GitHub, settings: Settings, lines: list[str], default: str) -> None:
    """Open an issue for the findings, or comment on the open one when they changed; never repeat the same ones."""
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    mention = f"@{settings.maintainer}" if settings.maintainer else "The maintainer (KEYTURN_MAINTAINER is not set)"
    body = "\n".join([
        f"{mention}: keyturn watch found what did not meet the merge conditions on `{default}`, or a rewrite of what "
        f"keyturn trusts (ADR 0048).",
        "",
        *[f"- {line}" for line in lines],
        "",
        f"Run: {settings.run_url}" if settings.run_url else "",
        "",
        "Until a run passes again, merge.py merges no task. Put it right as \"Recovering after a failed run\" in "
        "keyturn's github/README.md says: look at what is listed, put it right, set KEYTURN_CHECKED_UNTIL to the last "
        "activity you looked at, start keyturn watch by hand, check that it passes, and close this issue.",
        "",
        f"<!-- {MARKER}: {digest} -->",
    ])
    existing = [issue for issue in github.open_issues() if (issue.get("user") or {}).get("login") == BOT
                and "pull_request" not in issue and MARKER_RE.search(str(issue.get("body") or ""))]
    if not existing:
        url = github.create_issue(f"keyturn watch: {default} has what did not meet the merge conditions", body)
        print(f"opened {url}")
        return
    issue = existing[0]
    posted = [str(issue.get("body") or "")] + [str(comment.get("body") or "") for comment in
                                                github.comments(int(issue["number"]))
                                                if (comment.get("user") or {}).get("login") == BOT]
    if any(digest in MARKER_RE.findall(text) for text in posted):
        print(f"already reported in {issue.get('html_url', '')}")
        return
    github.comment(int(issue["number"]), body)
    print(f"commented on {issue.get('html_url', '')}")


def settings_from_env(start: str, wait_minutes: float) -> Settings:
    env = os.environ
    repository = env.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise SetupError("GITHUB_REPOSITORY is not set to OWNER/NAME")
    if not SHA_RE.fullmatch(start) or start == ZERO:
        raise SetupError(f"--start must be a full commit SHA (KEYTURN_START in the workflow), not {start!r}")
    vouched = set(re.split(r"[\s,]+", env.get("KEYTURN_VOUCHED", "").strip())) - {""}
    if bad := sorted(sha for sha in vouched if not SHA_RE.fullmatch(sha)):
        raise SetupError(f"KEYTURN_VOUCHED lists what is not a full commit SHA: {', '.join(bad)}")
    checked_until = None
    if text := env.get("KEYTURN_CHECKED_UNTIL", "").strip():
        if (checked_until := when(text)) is None:
            raise SetupError(f"KEYTURN_CHECKED_UNTIL is not an ISO 8601 time (for example 2026-11-22T10:00:00Z): {text!r}")
    maintainer = env.get("KEYTURN_MAINTAINER", "").strip().lstrip("@") or None
    if maintainer is None:
        # A run that finds something must tell someone: without the maintainer's account, the issue would mention
        # nobody, so the watch fails instead, and merge.py merges nothing until it is set.
        raise SetupError("KEYTURN_MAINTAINER is not set: set it to the maintainer's GitHub account (github/README.md)")
    if not LOGIN_RE.fullmatch(maintainer):
        raise SetupError(f"KEYTURN_MAINTAINER is not a GitHub account name: {maintainer!r}")
    event: dict = {}
    if path := env.get("GITHUB_EVENT_PATH"):
        try:
            event = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SetupError(f"the event payload could not be read: {error}") from None
    run_id = int(env["GITHUB_RUN_ID"]) if env.get("GITHUB_RUN_ID", "").isdigit() else None
    run_url = f"{env.get('GITHUB_SERVER_URL', 'https://github.com')}/{repository}/actions/runs/{run_id}" if run_id else ""
    return Settings(repository=repository, start=start, vouched=vouched, checked_until=checked_until,
                    maintainer=maintainer, event_name=env.get("GITHUB_EVENT_NAME", ""), event=event, run_id=run_id,
                    run_url=run_url, wait_seconds=max(wait_minutes, 0) * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect commits on the default branch that did not meet the merge "
                                                 "conditions (ADR 0048).")
    parser.add_argument("--start", required=True, help="the full SHA after which every commit is checked")
    parser.add_argument("--wait-minutes", type=float, default=5,
                        help="how long to wait for the activity to list the push that started the run (default: 5)")
    args = parser.parse_args()
    root = Path.cwd()
    github, default, settings = None, "the default branch", None
    try:
        settings = settings_from_env(args.start, args.wait_minutes)
        github = GitHub(settings.repository)
        watch = Watch(root, github, settings)
        findings = watch.run()
        default = watch.default
        code = EXIT_FAIL if findings else EXIT_PASS
        lines = [finding.line() for finding in findings]
    except SetupError as error:
        code, lines = EXIT_SETUP, [f"keyturn watch could not run: {quiet(str(error))}"]
    except Exception as error:  # an unexpected error must never look like a pass
        code, lines = EXIT_SETUP, [f"keyturn watch could not run: unexpected: {quiet(repr(error))}"]
    for line in lines:
        print(f"FAIL {line}" if code == EXIT_FAIL else line, file=sys.stderr if code else sys.stdout)
    if code == EXIT_PASS:
        print("keyturn watch: passed")
        return code
    if github is not None and settings is not None:
        try:
            report(github, settings, lines, default)
        except SetupError as error:
            print(f"the issue could not be opened: {error}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
