"""Tests for watch.py. Run from the repository root: python3 -m unittest discover -s github/scripts"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import task_branch  # noqa: E402
import watch  # noqa: E402

REPO = "owner/project"
NOW = datetime.now(timezone.utc)


def stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


# A stand-in for keyturn's conditions check: it records its arguments, and fails when FAKE_CONDITIONS_FAIL is set.
FAKE_CONDITIONS = textwrap.dedent("""\
    #!/bin/sh
    echo "$@" >> "$FAKE_CONDITIONS_LOG"
    if [ -n "$FAKE_CONDITIONS_FAIL" ]; then echo "FAIL acceptance: no acceptance row for delivery-1"; exit 1; fi
    echo "conditions: hold"
""")


class FakeGitHub(watch.GitHub):
    """GitHub as the tests set it up: pull requests by merge commit, gate runs by head, activity, runs, issues."""

    def __init__(self):
        super().__init__(REPO)
        self.pulls: dict[str, list[dict]] = {}
        self.checks: dict[str, list[dict]] = {}
        self.items: list[dict] = []
        self.runs: list[dict] = []
        self.issues: list[dict] = []
        self.issue_comments: dict[int, list[dict]] = {}
        self.created: list[tuple[str, str]] = []
        self.commented: list[tuple[int, str]] = []
        self.on_main: set[str] = set()  # commits on main as GitHub has it now, beyond the clone

    def default_branch(self) -> str:
        return "main"

    def on_branch(self, sha, branch):
        return sha in self.on_main

    def pulls_of(self, sha):
        return self.pulls.get(sha, [])

    def workflow_runs(self, workflow, sha):
        return [item for item in self.checks.get(sha, []) if item["path"].split("@")[0].endswith("/" + Path(workflow).name)]

    def jobs(self, run_id):
        return next(item["jobs"] for runs in self.checks.values() for item in runs if item["id"] == run_id)

    def activity(self, since):
        return sorted(self.items, key=lambda item: item["timestamp"], reverse=True)

    def passing_runs(self):
        return self.runs

    def open_issues(self):
        return self.issues

    def comments(self, number):
        return self.issue_comments.get(number, [])

    def create_issue(self, title, body):
        self.created.append((title, body))
        return "https://github.com/owner/project/issues/1"

    def comment(self, number, body):
        self.commented.append((number, body))


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Test",
                        GIT_AUTHOR_EMAIL="test@example.com", GIT_COMMITTER_NAME="Test",
                        GIT_COMMITTER_EMAIL="test@example.com")
        self.root = tmp / "project"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.root / "README.md").write_text("project\n", encoding="utf-8")
        self.git("add", ".")
        self.start = self.commit("first")
        self.conditions = tmp / "conditions.sh"
        self.conditions.write_text(FAKE_CONDITIONS, encoding="utf-8")
        self.conditions.chmod(0o755)
        self.conditions_log = tmp / "conditions.log"
        self.github = FakeGitHub()
        self.number = 0
        self.vouched: set[str] = set()
        self.checked_until: datetime | None = NOW - timedelta(days=1)
        self.event_name, self.event = "schedule", {}
        self.publish()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message: str, path: str = "README.md", text: str | None = None) -> str:
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text((text if text is not None else file.read_text(encoding="utf-8") if file.exists() else "")
                        + message + "\n", encoding="utf-8")
        self.git("add", path)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def publish(self) -> str:
        """The default branch on origin, as a full clone has it: main as it is now."""
        tip = self.git("rev-parse", "main")
        self.git("update-ref", "refs/remotes/origin/main", tip)
        return tip

    def task_merge(self, task: str = "delivery-1", *, tree_of: str | None = None, parent: str | None = None,
                   checks=("success", "success"), branch: str | None = None, repo: str = REPO,
                   up_to_date: bool = True) -> tuple[str, str]:
        """A task's pull request squash-merged on main: (merge commit, head)."""
        base = self.git("rev-parse", "main") if up_to_date else self.git("rev-parse", "main~1")
        self.git("switch", "-q", "-c", f"task/{task}", base)
        self.commit(f"feat: {task}", path=f"src/{task}.txt", text="")
        head = self.commit(f"chore(state): {task} done", path=f"keyturn/internal/state/{task}.md", text="")
        self.git("switch", "-q", "main")
        tree = self.git("rev-parse", f"{tree_of or head}^{{tree}}")
        merge = self.git("commit-tree", tree, "-p", parent or self.git("rev-parse", "main"), "-m", f"keyturn: {task}")
        self.git("update-ref", "refs/heads/main", merge)
        self.git("reset", "-q", "--hard", "main")
        self.number += 1
        self.github.pulls[merge] = [{"number": self.number, "merged_at": stamp(NOW), "merge_commit_sha": merge,
                                     "base": {"ref": "main"},
                                     "head": {"ref": branch or f"task/{task}", "sha": head, "repo": {"full_name": repo}}}]
        self.github.checks[head] = [self.gate_run(head, checks)]
        self.publish()
        return merge, head

    def gate_run(self, head: str, checks=("success", "success"), conclusion: str = "success", **changes) -> dict:
        """A run of the gate's workflow on the head, from its pull request, with the jobs concluding as `checks` says."""
        item = {"id": 1000 + self.number * 10 + len(self.github.checks.get(head, [])), "path": watch.GATE_WORKFLOW,
                "head_sha": head, "event": "pull_request", "head_repository": {"full_name": REPO},
                "status": "completed", "conclusion": conclusion if all(c == "success" for c in checks) else "failure",
                "jobs": [{"name": name, "conclusion": job} for name, job in zip(watch.CHECKS, checks)]}
        item.update(changes)
        return item

    def push(self, ref: str, after: str, kind: str = "push", minutes_ago: float = 10, login: str = "agent") -> None:
        self.github.items.append({"id": len(self.github.items) + 1, "ref": ref, "before": "1" * 40, "after": after,
                                  "activity_type": kind, "actor": {"login": login},
                                  "timestamp": stamp(NOW - timedelta(minutes=minutes_ago))})

    def settings(self, **changes) -> watch.Settings:
        values = dict(repository=REPO, start=self.start, vouched=self.vouched, checked_until=self.checked_until,
                      maintainer="maintainer", event_name=self.event_name, event=self.event, run_id=99,
                      run_url="https://github.com/owner/project/actions/runs/99", wait_seconds=0,
                      conditions=self.conditions)
        values.update(changes)
        return watch.Settings(**values)

    def watch(self, **changes) -> list[str]:
        # The scripts run commands with task_branch.ENV, a copy of the environment taken when it was imported.
        with mock.patch.dict(task_branch.ENV, {"FAKE_CONDITIONS_LOG": str(self.conditions_log)}), \
                mock.patch.object(watch, "POLL_SECONDS", 0):
            findings = watch.Watch(self.root, self.github, self.settings(**changes)).run()
        return [finding.line() for finding in findings]

    def assert_found(self, lines: list[str], text: str) -> None:
        self.assertTrue(any(text in line for line in lines), f"{text!r} not in {lines}")

    # The commits on the default branch.

    def test_a_task_merged_through_merge_py_passes(self):
        merge, head = self.task_merge()
        self.push("refs/heads/main", merge, "pr_merge")
        self.assertEqual(self.watch(), [])
        self.assertIn(f"--task delivery-1 --default-branch {self.start} --head {head}",
                      self.conditions_log.read_text(encoding="utf-8"))

    def test_a_direct_push_fails(self):
        direct = self.commit("fix: straight to main")
        self.publish()
        self.assert_found(self.watch(), f"the commit {direct[:12]} on main: is not the merge commit")

    def test_a_commit_that_skipped_ci_is_found_by_the_scheduled_run(self):
        direct = self.commit("fix: quick one [skip ci]")
        self.publish()
        self.event_name = "schedule"
        self.assert_found(self.watch(), f"the commit {direct[:12]} on main")

    def test_a_vouched_maintainer_commit_passes(self):
        self.vouched = {self.commit("docs: the maintainer's own")}
        self.publish()
        self.assertEqual(self.watch(), [])

    def test_a_commit_that_changes_only_workflows_passes(self):
        self.commit("ci: add keyturn", path=".github/workflows/keyturn-watch.yml", text="")
        self.publish()
        self.assertEqual(self.watch(), [])

    def test_a_commit_that_changes_workflows_and_more_fails(self):
        (self.root / "other.txt").write_text("x\n", encoding="utf-8")
        self.git("add", "other.txt")
        self.commit("ci: add keyturn", path=".github/workflows/keyturn-watch.yml", text="")
        self.publish()
        self.assert_found(self.watch(), "is not the merge commit")

    def test_a_merge_without_the_checks_fails(self):
        self.task_merge(checks=("success", "failure"))
        self.assert_found(self.watch(), "keyturn-gate.yml on #1's head")

    def test_a_merge_with_a_job_missing_or_skipped_fails(self):
        merge, head = self.task_merge()
        self.github.checks[head][0]["jobs"].pop()
        self.assert_found(self.watch(), "keyturn conditions on #1's head")
        self.github.checks[head] = [self.gate_run(head, ("skipped", "skipped"))]
        self.github.checks[head][0]["conclusion"] = "success"
        self.assert_found(self.watch(), "keyturn gate on #1's head")

    def test_a_run_of_another_workflow_event_or_repository_does_not_count(self):
        merge, head = self.task_merge()
        for changes in ({"path": ".github/workflows/other.yml"}, {"event": "push"},
                        {"head_repository": {"full_name": "someone/project"}}):
            with self.subTest(changes=changes):
                self.github.checks[head] = [self.gate_run(head, **changes)]
                self.assert_found(self.watch(), "has no run from its pull request")

    def test_the_newest_gate_run_counts(self):
        merge, head = self.task_merge()
        self.github.checks[head] = [self.gate_run(head, ("success", "failure"), id=1),
                                    self.gate_run(head, id=2, path=watch.GATE_WORKFLOW + "@refs/pull/1/merge")]
        self.assertEqual(self.watch(), [])
        self.github.checks[head][0]["id"], self.github.checks[head][1]["id"] = 3, 2
        self.assert_found(self.watch(), "did not pass")

    def test_a_draft_s_gate_run_is_passed_over(self):
        # A draft's run names its jobs "... (draft, not checked)" (ADR 0051): newer or older, it does not count.
        merge, head = self.task_merge()
        draft = self.gate_run(head, ("failure", "failure"), id=9)
        draft["jobs"] = [{"name": f"{name} (draft, not checked)", "conclusion": "failure"} for name in watch.CHECKS]
        self.github.checks[head] = [self.gate_run(head, id=5), draft]
        self.assertEqual(self.watch(), [])
        self.github.checks[head] = [self.gate_run(head, ("success", "failure"), id=5), draft]
        self.assert_found(self.watch(), "did not pass (failure)")
        self.github.checks[head] = [draft]
        self.assert_found(self.watch(), "has no run from its pull request on #1's head")
        self.assert_found(self.watch(), "that is not a draft's")

    def test_a_gate_run_with_no_jobs_is_not_passed_over(self):
        merge, head = self.task_merge()
        empty = self.gate_run(head, id=9, conclusion="failure")
        empty["conclusion"], empty["jobs"] = "startup_failure", []
        self.github.checks[head] = [self.gate_run(head, id=5), empty]
        self.assert_found(self.watch(), "did not pass (startup_failure)")

    def test_a_head_that_changes_a_workflow_fails(self):
        self.git("switch", "-q", "-c", "task/delivery-1")
        self.commit("feat: x", path="src/x.txt", text="")
        head = self.commit("ci: change it", path=".github/workflows/keyturn-gate.yml", text="")
        self.git("switch", "-q", "main")
        merge = self.git("commit-tree", self.git("rev-parse", f"{head}^{{tree}}"), "-p", "main", "-m", "keyturn")
        self.git("update-ref", "refs/heads/main", merge)
        self.git("reset", "-q", "--hard", "main")
        self.github.pulls[merge] = [{"number": 1, "merged_at": stamp(NOW), "merge_commit_sha": merge, "base": {"ref": "main"},
                                     "head": {"ref": "task/delivery-1", "sha": head, "repo": {"full_name": REPO}}}]
        self.github.checks[head] = [self.gate_run(head)]
        self.publish()
        self.assert_found(self.watch(), "changes files under .github/workflows/")

    def test_a_merge_whose_conditions_do_not_hold_again_fails(self):
        self.task_merge()
        with mock.patch.dict(task_branch.ENV, {"FAKE_CONDITIONS_FAIL": "1"}):
            self.assert_found(self.watch(), "FAIL acceptance: no acceptance row")

    def test_a_squash_commit_whose_tree_is_not_the_head_fails(self):
        self.task_merge(tree_of="main")
        self.assert_found(self.watch(), "does not have the tree of #1's head")

    def test_a_head_that_was_not_up_to_date_fails(self):
        self.commit("docs: the maintainer's own")
        self.vouched = {self.publish()}
        self.task_merge(up_to_date=False)
        self.assert_found(self.watch(), "does not contain its parent")

    def test_a_merge_from_a_branch_that_is_not_a_task_fails(self):
        self.task_merge(branch="feature/x")
        self.assert_found(self.watch(), "is not a task's")

    def test_a_merge_from_a_fork_fails(self):
        self.task_merge(repo="someone/project")
        self.assert_found(self.watch(), "not in this repository")

    def test_a_merge_commit_with_two_parents_fails(self):
        side = self.git("rev-parse", "main")
        merge, head = self.task_merge()
        two = self.git("commit-tree", self.git("rev-parse", f"{head}^{{tree}}"), "-p", self.start, "-p", head, "-m", "m")
        self.git("update-ref", "refs/heads/main", two)
        self.github.pulls[two] = [dict(self.github.pulls.pop(merge)[0], merge_commit_sha=two)]
        self.publish()
        self.assertNotEqual(side, two)
        self.assert_found(self.watch(), "has 2 parents")

    def test_a_starting_commit_no_longer_on_the_branch_fails(self):
        other = self.git("commit-tree", self.git("rev-parse", "main^{tree}"), "-m", "elsewhere")
        self.assert_found(self.watch(start=other), "is no longer an ancestor")

    # The repository's activity.

    def test_a_force_push_to_a_task_branch_fails(self):
        self.push("refs/heads/task/delivery-1", "2" * 40, "force_push")
        self.assert_found(self.watch(), "a force push to a task branch")

    def test_the_deletion_of_a_task_branch_fails(self):
        self.push("refs/heads/task/delivery-1", watch.ZERO, "branch_deletion")
        self.assert_found(self.watch(), "the deletion of a task branch")

    def test_other_branches_are_not_watched(self):
        self.push("refs/heads/feature/x", "2" * 40, "force_push")
        self.push("refs/heads/feature/x", watch.ZERO, "branch_deletion")
        self.assertEqual(self.watch(), [])

    def test_a_force_push_to_the_default_branch_fails(self):
        self.push("refs/heads/main", self.start, "force_push")
        self.assert_found(self.watch(), "a force push of the default branch")

    def test_a_commit_pushed_and_removed_again_fails(self):
        self.push("refs/heads/main", "3" * 40, "push")
        self.assert_found(self.watch(), "which is no longer on main")

    def test_a_push_after_the_clone_that_is_still_on_the_branch_passes(self):
        # A task's merge pushed between the clone and the activity read: GitHub has it on main, the clone does not.
        self.push("refs/heads/main", "3" * 40, "pr_merge", minutes_ago=1)
        self.github.on_main = {"3" * 40}
        self.assertEqual(self.watch(), [])

    def test_a_reset_to_an_older_commit_fails(self):
        merge, _ = self.task_merge()
        self.github.runs = [{"id": 5, "head_branch": "main", "head_sha": merge, "run_started_at": stamp(NOW - timedelta(days=2))}]
        self.git("update-ref", "refs/remotes/origin/main", self.start)
        self.assert_found(self.watch(), f"main's tip {merge[:12]} that the last passing run checked")

    def test_the_activity_before_the_checkpoint_is_not_read_again(self):
        self.push("refs/heads/task/delivery-1", "2" * 40, "force_push", minutes_ago=60 * 30)
        self.assertEqual(self.watch(), [])

    def test_recovery_with_checked_until_passes_again(self):
        self.push("refs/heads/task/delivery-1", "2" * 40, "force_push", minutes_ago=30)
        self.assert_found(self.watch(), "a force push to a task branch")
        self.checked_until = NOW - timedelta(minutes=20)
        self.assertEqual(self.watch(), [])

    def test_a_passing_run_moves_the_checkpoint_but_reads_an_hour_before_it(self):
        self.checked_until = NOW - timedelta(days=10)
        self.push("refs/heads/task/a", "2" * 40, "force_push", minutes_ago=60 * 24 * 5)
        self.push("refs/heads/task/b", "2" * 40, "force_push", minutes_ago=50)
        self.github.runs = [{"id": 5, "head_branch": "main", "head_sha": self.start, "run_started_at": stamp(NOW - timedelta(minutes=30))}]
        lines = self.watch()
        self.assert_found(lines, "refs/heads/task/b")
        self.assertFalse(any("refs/heads/task/a" in line for line in lines), lines)

    def test_its_own_run_is_not_a_checkpoint(self):
        self.push("refs/heads/task/a", "2" * 40, "force_push", minutes_ago=60 * 5)
        self.github.runs = [{"id": 99, "head_branch": "main", "head_sha": self.start, "run_started_at": stamp(NOW)}]
        self.assert_found(self.watch(), "refs/heads/task/a")

    def test_no_checkpoint_at_all_fails(self):
        self.checked_until = None
        self.assert_found(self.watch(), "KEYTURN_CHECKED_UNTIL is not set")

    def test_a_push_waits_for_the_activity_to_list_it(self):
        self.event_name, self.event = "push", {"ref": "refs/heads/task/delivery-1", "after": "4" * 40, "forced": True}
        self.assert_found(self.watch(), "the push of `refs/heads/task/delivery-1` that started this run (a force push")
        self.push("refs/heads/task/delivery-1", "4" * 40, "push")
        self.assertEqual(self.watch(), [])

    def test_a_deletion_waits_for_the_activity_to_list_it(self):
        self.event_name, self.event = "delete", {"ref": "task/delivery-1", "ref_type": "branch"}
        self.assert_found(self.watch(), "the deletion of `refs/heads/task/delivery-1` that started this run")
        self.push("refs/heads/task/delivery-1", watch.ZERO, "branch_deletion")
        self.assert_found(self.watch(), "the deletion of a task branch")

    def test_an_at_sign_mentions_nobody(self):
        self.push("refs/heads/task/x", "2" * 40, "force_push", login="someone")
        self.github.items[-1]["ref"] = "refs/heads/task/@someone"
        lines = self.watch()
        self.assertTrue(lines)
        self.assertFalse(any("@someone" in line for line in lines), lines)


class ReportTest(unittest.TestCase):
    def setUp(self):
        quiet = mock.patch("builtins.print")  # report() says what it did; the tests check the fake instead
        quiet.start()
        self.addCleanup(quiet.stop)
        self.github = FakeGitHub()
        self.settings = watch.Settings(repository=REPO, start="a" * 40, maintainer="maintainer",
                                       run_url="https://github.com/owner/project/actions/runs/1")

    def test_it_opens_an_issue_that_mentions_the_maintainer(self):
        watch.report(self.github, self.settings, ["the commit abc on main: bad"], "main")
        title, body = self.github.created[0]
        self.assertIn("main", title)
        self.assertTrue(body.startswith("@maintainer"))
        self.assertIn("- the commit abc on main: bad", body)
        self.assertIn("KEYTURN_CHECKED_UNTIL", body)

    def test_the_same_findings_are_not_reported_twice_and_new_ones_are_commented(self):
        watch.report(self.github, self.settings, ["one"], "main")
        body = self.github.created[0][1]
        self.github.issues = [{"number": 7, "user": {"login": watch.BOT}, "body": body, "html_url": "u"}]
        watch.report(self.github, self.settings, ["one"], "main")
        self.assertEqual((len(self.github.created), self.github.commented), (1, []))
        watch.report(self.github, self.settings, ["one", "two"], "main")
        self.assertEqual(self.github.commented[0][0], 7)
        self.github.issue_comments[7] = [{"user": {"login": watch.BOT}, "body": self.github.commented[0][1]}]
        watch.report(self.github, self.settings, ["one", "two"], "main")
        self.assertEqual(len(self.github.commented), 1)

    def test_an_issue_by_someone_else_is_not_the_report(self):
        watch.report(self.github, self.settings, ["one"], "main")
        body = self.github.created[0][1]
        self.github.issues = [{"number": 7, "user": {"login": "agent"}, "body": body},
                              {"number": 8, "user": {"login": watch.BOT}, "body": body, "pull_request": {}}]
        watch.report(self.github, self.settings, ["one"], "main")
        self.assertEqual(len(self.github.created), 2)


class ActivityPagesTest(unittest.TestCase):
    """GitHub.activity on gh's --include output, with the Link header as GitHub sent it on a private repository."""

    def page(self, items: list[dict], cursor: str | None) -> str:
        link = (f'Link: <https://api.github.com/repositories/1467637921/activity?direction=desc&per_page=100&after={cursor}>;'
                f' rel="next"\r\n') if cursor else ""
        return f"HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n{link}\r\n" + json.dumps(items)

    def test_it_follows_the_next_page_until_the_checkpoint(self):
        since = NOW - timedelta(hours=1)
        newer = [{"id": n, "timestamp": stamp(NOW - timedelta(minutes=n))} for n in range(1, 3)]
        older = [{"id": 9, "timestamp": stamp(NOW - timedelta(minutes=30))},
                 {"id": 10, "timestamp": stamp(NOW - timedelta(hours=2))}]
        pages = [self.page(newer, "abc"), self.page(older, "def"), self.page([{"id": 99}], None)]
        github = watch.GitHub(REPO)
        with mock.patch.object(watch.GitHub, "call", side_effect=pages) as call:
            found = github.activity(since)
        self.assertEqual([item["id"] for item in found], [1, 2, 9, 10])
        self.assertEqual(call.call_args_list[1].args[0],
                         "repositories/1467637921/activity?direction=desc&per_page=100&after=abc")
        self.assertEqual(call.call_count, 2)  # the second page reaches the checkpoint: no third request


class SettingsTest(unittest.TestCase):
    def env(self, **values):
        base = {"GITHUB_REPOSITORY": REPO, "GITHUB_RUN_ID": "12", "GITHUB_EVENT_NAME": "schedule",
                "KEYTURN_MAINTAINER": "maintainer"}
        base.update(values)
        return mock.patch.dict(os.environ, base, clear=True)

    def test_it_reads_the_variables(self):
        sha = "b" * 40
        with self.env(KEYTURN_VOUCHED=f" {sha},\n{'c' * 40} ", KEYTURN_CHECKED_UNTIL="2026-11-22T10:00:00Z",
                      KEYTURN_MAINTAINER="@maintainer"):
            settings = watch.settings_from_env("a" * 40, 5)
        self.assertEqual(settings.vouched, {sha, "c" * 40})
        self.assertEqual(settings.checked_until, datetime(2026, 11, 22, 10, tzinfo=timezone.utc))
        self.assertEqual((settings.maintainer, settings.run_id), ("maintainer", 12))
        self.assertTrue(settings.run_url.endswith("/owner/project/actions/runs/12"))

    def test_it_refuses_what_is_not_valid(self):
        for start, values, text in (("0" * 40, {}, "--start"), ("main", {}, "--start"),
                                    ("a" * 40, {"KEYTURN_VOUCHED": "abc1234"}, "KEYTURN_VOUCHED"),
                                    ("a" * 40, {"KEYTURN_CHECKED_UNTIL": "yesterday"}, "KEYTURN_CHECKED_UNTIL"),
                                    ("a" * 40, {"KEYTURN_MAINTAINER": "a b"}, "KEYTURN_MAINTAINER"),
                                    ("a" * 40, {"KEYTURN_MAINTAINER": ""}, "KEYTURN_MAINTAINER is not set"),
                                    ("a" * 40, {"KEYTURN_MAINTAINER": " @ "}, "KEYTURN_MAINTAINER is not set"),
                                    ("a" * 40, {"GITHUB_REPOSITORY": ""}, "GITHUB_REPOSITORY")):
            with self.subTest(text=text), self.env(**values), self.assertRaises(watch.SetupError) as raised:
                watch.settings_from_env(start, 5)
            self.assertIn(text, str(raised.exception))


class MainTest(unittest.TestCase):
    """watch.py as the workflow runs it: a missing KEYTURN_MAINTAINER fails the run before anything is read."""

    def test_without_the_maintainer_the_run_fails_as_a_setup_error(self):
        env = {"GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_NAME": "schedule", "PATH": os.environ.get("PATH", "")}
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(HERE / "watch.py"), "--start", "a" * 40], cwd=tmp, env=env,
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, watch.EXIT_SETUP, result.stdout + result.stderr)
        self.assertIn("KEYTURN_MAINTAINER is not set", result.stderr)


class WorkflowTest(unittest.TestCase):
    """The templates in github/workflows/, read as text: the parts the scripts rely on."""

    def read(self, name: str) -> str:
        return (HERE.parent / "workflows" / name).read_text(encoding="utf-8")

    def test_watch_workflow(self):
        text = self.read("keyturn-watch.yml")
        for needed in ("name: keyturn watch", "    name: keyturn watch", "  push:", "'task/**'", "  delete:",
                       "  schedule:", "  workflow_dispatch:", "issues: write", "actions: read",
                       "pull-requests: read", "fetch-depth: 0", "github/scripts/watch.py",
                       "vars.KEYTURN_VOUCHED", "vars.KEYTURN_CHECKED_UNTIL", "vars.KEYTURN_MAINTAINER"):
            self.assertIn(needed, text)
        self.assertNotIn("concurrency:", text)
        self.assertNotIn("checks:", text)  # a fine-grained token has no Checks permission; the runs are read instead  # a pending run replaced by a later one would leave a tip unchecked

    def test_gate_workflow_fails_drafts_under_other_names(self):
        # No job-level condition, since a skipped required check counts as passed (ADR 0043, ADR 0051); on a draft,
        # each job takes another name and fails in its first step.
        text = self.read("keyturn-gate.yml")
        self.assertIn("ready_for_review", text)
        jobs = text.split("\njobs:\n", 1)[1]
        blocks = [block for block in re.split(r"\n(?=  [a-z][a-z0-9_-]*:\n)", "\n" + jobs) if block.strip()]
        self.assertEqual(len(blocks), 2)
        for block, check in zip(blocks, watch.CHECKS):
            with self.subTest(check=check):
                self.assertIsNone(re.search(r"^    if:", block, re.M))
                self.assertIn(f"    name: ${{{{ github.event.pull_request.draft && '{check} (draft, not checked)' "
                              f"|| '{check}' }}}}\n", block)
                steps = block.split("    steps:\n", 1)[1]
                first = steps.split("\n      - ", 1)[0]
                self.assertIn("- name: Refuse a draft\n        if: github.event.pull_request.draft\n", first)
                self.assertIn("exit 1", first)


if __name__ == "__main__":
    unittest.main()
