"""Tests for merge.py. Run from the repository root: python3 -m unittest discover -s github/scripts"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUSHED = "2026-01-01T00:00:00Z"  # when the default branch's tip was pushed, in the fake activity

# A stand-in for the GitHub CLI: it records each call, answers `pr list` from FAKE_GH_PRS, a workflow's runs for a
# commit, and a run's jobs, from FAKE_GH_CHECKS (each run names its path, its head_sha, and its jobs), the repository's activity from FAKE_GH_ACTIVITY, the branch's rules
# and its classic protection from FAKE_GH_RULES and FAKE_GH_BRANCH, and merges as GitHub would: a squash commit with the
# head's tree on the default branch's tip in the bare origin (FAKE_ORIGIN), or on FAKE_GH_MERGE_PARENT instead. It
# refuses the merge when FAKE_GH_MERGE_FAILS is set.
FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, subprocess, sys
    with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(sys.argv[1:]) + "\\n")
    def read(name):
        return open(os.environ[name], encoding="utf-8").read()
    def origin(*args):
        return subprocess.run(["git", "--git-dir", os.environ["FAKE_ORIGIN"], *args], check=True,
                              capture_output=True, text=True).stdout.strip()
    endpoint = sys.argv[2] if len(sys.argv) > 2 else ""
    if sys.argv[1:3] == ["pr", "list"]:
        print(read("FAKE_GH_PRS"))
    elif sys.argv[1] == "api" and "/actions/workflows/" in endpoint:
        workflow = endpoint.split("/actions/workflows/")[1].split("/")[0]
        sha = endpoint.split("head_sha=")[1].split("&")[0]
        runs = [run for run in json.loads(read("FAKE_GH_CHECKS"))
                if run["head_sha"] == sha and run["path"].split("@")[0].endswith("/" + workflow)]
        print(json.dumps({"total_count": len(runs), "workflow_runs": runs}))
    elif sys.argv[1] == "api" and "/actions/runs/" in endpoint and endpoint.split("?")[0].endswith("/jobs"):
        number = int(endpoint.split("/actions/runs/")[1].split("/")[0])
        run = [run for run in json.loads(read("FAKE_GH_CHECKS")) if run["id"] == number][0]
        print(json.dumps({"total_count": len(run["jobs"]), "jobs": run["jobs"]}))
    elif sys.argv[1] == "api" and "/activity" in endpoint:
        print(read("FAKE_GH_ACTIVITY"))
    elif sys.argv[1] == "api" and "/rules/branches/" in endpoint:
        if os.environ.get("FAKE_GH_RULES_FAIL"):
            print("gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)",
                  file=sys.stderr)
            sys.exit(1)
        print(read("FAKE_GH_RULES"))
    elif sys.argv[1] == "api" and "/branches/" in endpoint:
        print(read("FAKE_GH_BRANCH"))
    elif sys.argv[1] == "api" and endpoint.endswith("/merge"):
        if os.environ.get("FAKE_GH_MERGE_FAILS") and not os.environ.get("FAKE_GH_MERGED_ANYWAY"):
            print("Head branch was modified. Review and try the merge again.", file=sys.stderr)
            sys.exit(1)
        head = [arg[4:] for arg in sys.argv if arg.startswith("sha=")][0]
        parent = os.environ.get("FAKE_GH_MERGE_PARENT") or origin("rev-parse", "refs/heads/main")
        tree = os.environ.get("FAKE_GH_MERGE_TREE") or origin("rev-parse", head + "^{tree}")
        merge = origin("commit-tree", tree, "-p", parent, "-m", "squash")
        origin("update-ref", "refs/heads/main", merge)
        with open(os.environ["FAKE_GH_LOG"] + ".merged", "w", encoding="utf-8") as f:
            f.write(merge)
        if os.environ.get("FAKE_GH_MERGE_FAILS"):  # merged, but the answer did not say so
            print("HTTP 502: Bad Gateway", file=sys.stderr)
            sys.exit(1)
        print(json.dumps({"sha": merge, "merged": True, "message": "Pull Request successfully merged"}))
    elif sys.argv[1] == "api" and "/pulls/" in endpoint:
        merged = os.environ["FAKE_GH_LOG"] + ".merged"
        sha = open(merged, encoding="utf-8").read() if os.path.exists(merged) else None
        print(json.dumps({"merged": bool(sha), "merge_commit_sha": sha}))
""")

# A stand-in for keyturn's conditions check, in the copy of keyturn the test runs merge.py from.
FAKE_CONDITIONS = textwrap.dedent("""\
    #!/bin/sh
    echo "$@" >> "$FAKE_CONDITIONS_LOG"
    if [ -n "$FAKE_CONDITIONS_FAIL" ]; then echo "FAIL acceptance: no acceptance row for delivery-1"; exit 1; fi
    echo "conditions: hold"
""")


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        # merge.py finds gates/conditions.sh from its own place, so it runs from a copy with a fake check.
        scripts = tmp / "keyturn" / "github" / "scripts"
        scripts.mkdir(parents=True)
        for name in ("merge.py", "task_branch.py"):
            shutil.copy(HERE / name, scripts / name)
        self.script = scripts / "merge.py"
        # No wait for GitHub to show a push: the fake answers at once.
        self.script.write_text(self.script.read_text(encoding="utf-8").replace("HEAD_WAIT_SECONDS = 30", "HEAD_WAIT_SECONDS = 0"),
                               encoding="utf-8")
        (tmp / "keyturn" / "gates").mkdir()
        conditions = tmp / "keyturn" / "gates" / "conditions.sh"
        conditions.write_text(FAKE_CONDITIONS, encoding="utf-8")
        conditions.chmod(0o755)

        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Test",
                        GIT_AUTHOR_EMAIL="test@example.com", GIT_COMMITTER_NAME="Test",
                        GIT_COMMITTER_EMAIL="test@example.com")
        self.origin = tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True, env=self.env)
        self.root = tmp / "project"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / ".github" / "workflows" / "keyturn-watch.yml").write_text("name: keyturn watch\n", encoding="utf-8")
        self.git("add", ".")
        self.tip = self.commit("first")
        self.git("remote", "add", "origin", "https://github.com/owner/project.git")
        self.git("config", f"url.{self.origin}.insteadOf", "https://github.com/owner/project.git")
        self.git("push", "-q", "origin", "main")
        self.git("remote", "set-head", "origin", "main")
        self.git("switch", "-q", "-c", "task/delivery-1")
        self.head = self.commit("chore(state): done")
        self.git("push", "-q", "origin", "task/delivery-1")

        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH, encoding="utf-8")
        (bin_dir / "gh").chmod(0o755)
        self.log, self.prs, self.checks = tmp / "gh.log", tmp / "prs.json", tmp / "checks.json"
        self.activity, self.rules, self.branch = tmp / "activity.json", tmp / "rules.json", tmp / "branch.json"
        self.conditions_log = tmp / "conditions.log"
        self.set_prs([self.pr()])
        self.watch_runs: list[dict] = []
        self.head_watch_runs: list[dict] = []
        self.run_ids = 0
        self.set_gate(self.gate_run())
        self.set_activity(self.tip, PUSHED)
        self.set_watch("success")
        self.set_head_watch("success")
        self.set_protection(rules=[], branch={"protected": False, "protection": {"enabled": False}})
        self.env.update(PATH=f"{bin_dir}{os.pathsep}{self.env['PATH']}", FAKE_GH_LOG=str(self.log),
                        FAKE_GH_PRS=str(self.prs), FAKE_GH_CHECKS=str(self.checks), FAKE_GH_ACTIVITY=str(self.activity),
                        FAKE_GH_RULES=str(self.rules), FAKE_GH_BRANCH=str(self.branch), FAKE_ORIGIN=str(self.origin),
                        FAKE_CONDITIONS_LOG=str(self.conditions_log))

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def pr(self, **changes) -> dict:
        pr = {"number": 7, "url": "https://github.com/owner/project/pull/7", "state": "OPEN", "isDraft": False,
              "isCrossRepository": False, "baseRefName": "main", "headRefOid": self.head}
        pr.update(changes)
        return pr

    def set_prs(self, prs: list[dict]) -> None:
        self.prs.write_text(json.dumps(prs), encoding="utf-8")

    def workflow_run(self, path: str, sha: str, conclusion: str | None, jobs: dict[str, str | None], **changes) -> dict:
        self.run_ids += 1
        item = {"id": self.run_ids, "path": path, "head_sha": sha, "event": "pull_request",
                "head_repository": {"full_name": "owner/project"},
                "status": "completed" if conclusion else "in_progress", "conclusion": conclusion,
                "run_started_at": PUSHED, "html_url": f"https://github.com/owner/project/actions/runs/{self.run_ids}",
                "jobs": [{"name": name, "status": "completed" if job else "in_progress", "conclusion": job}
                         for name, job in jobs.items()]}
        item.update(changes)
        return item

    def gate_run(self, conclusion: str | None = "success", jobs: dict[str, str | None] | None = None, **changes) -> dict:
        """A run of the gate's workflow on the head; its two jobs conclude as the run does unless `jobs` says."""
        if jobs is None:
            jobs = {"keyturn gate": conclusion, "keyturn conditions": conclusion}
        item = self.workflow_run(".github/workflows/keyturn-gate.yml", self.head, conclusion, jobs)
        item.update(changes)
        return item

    def draft_run(self, conclusion: str | None = "failure") -> dict:
        """A run of the gate's workflow on a draft: its jobs take other names and fail (ADR 0051)."""
        return self.workflow_run(".github/workflows/keyturn-gate.yml", self.head, conclusion,
                                 {"keyturn gate (draft, not checked)": conclusion,
                                  "keyturn conditions (draft, not checked)": conclusion})

    def set_gate(self, *runs: dict) -> None:
        self.head_runs = list(runs)
        self.write_checks()

    def set_watch(self, *conclusions: str | None, started: str = "2026-01-01T00:05:00Z", sha: str | None = None,
                  path: str = ".github/workflows/keyturn-watch.yml") -> None:
        """keyturn watch on the default branch's tip (or on `sha`)."""
        self.watch_runs = [self.workflow_run(path, sha or self.tip, conclusion, {"keyturn watch": conclusion},
                                             event="schedule", run_started_at=started)
                           for conclusion in conclusions]
        self.write_checks()

    def set_head_watch(self, *conclusions: str | None) -> None:
        """keyturn watch on the task's head, started by the push of the task branch (ADR 0050)."""
        self.head_watch_runs = [self.workflow_run(".github/workflows/keyturn-watch.yml", self.head, conclusion,
                                                  {"keyturn watch": conclusion}, event="push")
                                for conclusion in conclusions]
        self.write_checks()

    def write_checks(self) -> None:
        runs = self.head_runs + self.watch_runs + [dict(run, head_sha=self.head) for run in self.head_watch_runs]
        self.checks.write_text(json.dumps(runs), encoding="utf-8")

    def set_activity(self, after: str, timestamp: str, kind: str = "push") -> None:
        self.activity.write_text(json.dumps([{"id": 1, "ref": "refs/heads/main", "before": "0" * 40, "after": after,
                                              "timestamp": timestamp, "activity_type": kind}]), encoding="utf-8")

    def set_protection(self, rules: list[dict], branch: dict) -> None:
        self.rules.write_text(json.dumps(rules), encoding="utf-8")
        self.branch.write_text(json.dumps(branch), encoding="utf-8")

    def push_to_main(self, message: str, move: bool = True) -> str:
        """A commit on the default branch from somewhere else, after the task started (with move=False, only made)."""
        tree = subprocess.run(["git", "--git-dir", str(self.origin), "rev-parse", "main^{tree}"], check=True,
                              capture_output=True, text=True, env=self.env).stdout.strip()
        sha = subprocess.run(["git", "--git-dir", str(self.origin), "commit-tree", tree, "-p", "main", "-m", message],
                             check=True, capture_output=True, text=True, env=self.env).stdout.strip()
        if move:
            subprocess.run(["git", "--git-dir", str(self.origin), "update-ref", "refs/heads/main", sha], check=True,
                           env=self.env)
        return sha

    def merge(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), "delivery-1", "--wait-minutes", "0", *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def merged(self) -> list[list[str]]:
        return [call for call in self.calls() if call[0] == "api" and call[1].endswith("/merge")]

    def assert_refused(self, result: subprocess.CompletedProcess, text: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(text, result.stderr)
        self.assertEqual(self.merged(), [])

    def assert_pending(self, result: subprocess.CompletedProcess, text: str) -> None:
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn(text, result.stderr)
        self.assertEqual(self.merged(), [])

    def test_merges_with_a_squash_that_names_the_head(self):
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.merged(), [["api", "repos/owner/project/pulls/7/merge", "-X", "PUT", "-f", "merge_method=squash",
                                          "-f", f"sha={self.head}", "-f", "commit_title=keyturn: delivery-1 (#7)",
                                          "-f", "commit_message=Merged by keyturn's merge.py after its checks (task delivery-1)."]])
        self.assertEqual(self.conditions_log.read_text().split(),
                         ["--task", "delivery-1", "--default-branch", "origin/main", "--head", self.head])

    def test_without_an_open_pull_request_or_from_a_fork_it_refuses(self):
        self.set_prs([self.pr(isCrossRepository=True)])
        self.assert_refused(self.merge(), "no open pull request from task/delivery-1")

    def test_a_draft_or_another_base_is_refused(self):
        self.set_prs([self.pr(isDraft=True)])
        self.assert_refused(self.merge(), "is a draft")
        self.set_prs([self.pr(baseRefName="release")])
        self.assert_refused(self.merge(), "not to the default branch main")

    def test_a_head_that_is_not_the_local_one_or_origin_s_is_refused(self):
        self.set_prs([self.pr(headRefOid="0" * 40)])
        self.assert_pending(self.merge(), "still shows")
        self.set_prs([self.pr()])
        self.head = self.commit("not pushed")
        self.set_prs([self.pr()])
        self.assert_refused(self.merge(), "task/delivery-1 on origin is not at the local HEAD")

    def test_checks_that_failed_or_did_not_finish_are_refused(self):
        self.set_gate(self.gate_run("failure", {"keyturn gate": "success", "keyturn conditions": "failure"}))
        self.assert_refused(self.merge(), "did not pass: .github/workflows/keyturn-gate.yml did not pass (failure")
        self.set_gate(self.gate_run(None))
        self.assert_pending(self.merge(), "keyturn-gate.yml has not finished")
        self.set_gate()
        self.assert_pending(self.merge(), "have not finished (or not started)")

    def test_a_passing_run_whose_jobs_did_not_both_pass_is_refused(self):
        # A run whose jobs were skipped (a draft) or that has only one of them does not count as a pass.
        self.set_gate(self.gate_run("success", {"keyturn gate": "skipped", "keyturn conditions": "skipped"}))
        self.assert_refused(self.merge(), "the jobs keyturn gate, keyturn conditions did not pass (skipped, skipped")
        self.set_gate(self.gate_run("success", {"keyturn gate": "success"}))
        self.assert_refused(self.merge(), "the job keyturn conditions did not pass (no job")

    def test_a_run_of_another_workflow_event_or_repository_does_not_count(self):
        for changes in ({"path": ".github/workflows/other.yml"}, {"event": "push"},
                        {"head_repository": {"full_name": "someone/project"}}, {"head_sha": "0" * 40}):
            with self.subTest(changes=changes):
                self.set_gate(self.gate_run(**changes))
                self.assert_pending(self.merge(), "have not finished (or not started)")

    def test_a_run_path_with_a_ref_counts(self):
        self.set_gate(self.gate_run(path=".github/workflows/keyturn-gate.yml@refs/pull/7/merge"))
        self.assertEqual(self.merge().returncode, 0)

    def test_the_newest_run_counts(self):
        self.set_gate(self.gate_run("failure"), self.gate_run("success"))
        self.assertEqual(self.merge().returncode, 0)

    def test_a_draft_s_run_newer_than_a_passing_one_is_passed_over(self):
        # A draft's run newer than the one on the ready pull request hides nothing (ADR 0051).
        self.set_gate(self.gate_run("success"), self.draft_run())
        self.assertEqual(self.merge().returncode, 0)

    def test_a_draft_s_run_that_has_not_finished_is_passed_over(self):
        self.set_gate(self.gate_run("success"), self.draft_run(None))
        self.assertEqual(self.merge().returncode, 0)

    def test_a_draft_s_run_does_not_hide_a_failed_one(self):
        self.set_gate(self.gate_run("failure"), self.draft_run())
        self.assert_refused(self.merge(), "did not pass (failure")
        self.set_gate(self.draft_run(), self.gate_run("failure"))
        self.assert_refused(self.merge(), "did not pass (failure")

    def test_only_a_draft_s_run_is_no_run(self):
        self.set_gate(self.draft_run())
        self.assert_pending(self.merge(), "have not finished (or not started)")

    def test_a_run_with_no_jobs_yet_is_waited_for(self):
        # A queued run lists no jobs yet, so it cannot be told from a draft's: it is waited for, not passed over.
        self.set_gate(self.gate_run("success"), self.workflow_run(".github/workflows/keyturn-gate.yml", self.head, None, {}))
        self.assert_pending(self.merge(), "keyturn-gate.yml has not finished")

    def test_a_task_branch_that_changes_a_workflow_is_refused(self):
        (self.root / ".github" / "workflows" / "keyturn-gate.yml").write_text("changed\n", encoding="utf-8")
        self.git("add", ".")
        self.head = self.commit("ci: change the gate")
        self.git("push", "-q", "origin", "task/delivery-1")
        self.set_prs([self.pr()])
        self.set_gate(self.gate_run())
        self.assert_refused(self.merge(), "changes files under .github/workflows/")

    def test_conditions_that_do_not_hold_are_refused(self):
        self.env["FAKE_CONDITIONS_FAIL"] = "1"
        self.assert_refused(self.merge(), "FAIL acceptance: no acceptance row")

    def test_a_merge_github_refuses_is_not_tried_again(self):
        self.env["FAKE_GH_MERGE_FAILS"] = "1"
        result = self.merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Head branch was modified", result.stderr)
        self.assertEqual(len([call for call in self.calls() if call[1].endswith("/merge")]), 1)

    def test_a_failed_merge_call_on_a_merged_pull_request_is_a_merge(self):
        self.env["FAKE_GH_MERGE_FAILS"] = "1"
        self.env["FAKE_GH_MERGED_ANYWAY"] = "1"
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("but the pull request is merged", result.stderr)

    def test_a_head_that_does_not_contain_the_default_branch_s_tip_is_refused(self):
        self.push_to_main("pushed after the task started")
        self.assert_refused(self.merge(), "does not contain the tip")

    def test_without_a_passing_watch_on_the_tip_after_its_last_push_it_does_not_merge(self):
        self.set_watch("failure")
        self.assert_refused(self.merge(), "keyturn watch on main's tip")
        self.set_watch(None)
        self.assert_pending(self.merge(), "keyturn watch on main's tip")
        self.set_watch()
        self.assert_pending(self.merge(), "no run of keyturn watch")
        self.set_watch("success", path=".github/workflows/other.yml")
        self.assert_pending(self.merge(), "no run of keyturn watch")
        self.set_watch("success")
        self.watch_runs[0]["jobs"][0]["conclusion"] = "skipped"
        self.write_checks()
        self.assert_refused(self.merge(), "the job keyturn watch did not pass")
        self.set_watch("success", sha=self.head)  # on the task's head, not on the tip
        self.assert_pending(self.merge(), "no run of keyturn watch")

    def test_a_failed_watch_on_the_task_s_head_is_refused(self):
        # A force push to the task branch: the push's own run of keyturn watch fails on the head (ADR 0050).
        self.set_head_watch("success", "failure")
        self.assert_refused(self.merge(), "keyturn watch on the task's head")
        self.set_head_watch()
        self.assert_pending(self.merge(), "keyturn watch on the task's head")
        self.set_head_watch(None)
        self.assert_pending(self.merge(), "has not finished")

    def test_an_old_success_before_the_last_push_does_not_count(self):
        # The branch was reset to a commit with an old passing run: the reset is a push after it.
        self.set_watch("success", started="2025-12-31T23:00:00Z")
        self.assert_pending(self.merge(), "since the last push to main")
        self.set_watch("failure", "success")  # the newest run counts: the maintainer started it after recovering
        self.assertEqual(self.merge().returncode, 0)

    def test_an_activity_that_does_not_show_the_tip_yet_waits(self):
        self.set_activity("1" * 40, PUSHED)
        self.assert_pending(self.merge(), "activity does not show main")

    def test_an_activity_that_lists_no_push_is_refused(self):
        self.activity.write_text("[]", encoding="utf-8")
        self.assert_refused(self.merge(), "lists no push to main")

    def test_it_keeps_polling_until_the_activity_and_the_checks_are_there(self):
        # The activity lags the push, and the checks run: the first polls wait instead of exiting.
        self.script.write_text(self.script.read_text(encoding="utf-8").replace("POLL_SECONDS = 30", "POLL_SECONDS = 0.2"),
                               encoding="utf-8")
        self.set_activity("1" * 40, PUSHED)
        self.set_gate(self.gate_run(None))
        catch_up = textwrap.dedent(f"""\
            import json, time
            time.sleep(1)
            open({str(self.activity)!r}, "w").write(json.dumps([{{"after": {self.tip!r}, "timestamp": {PUSHED!r}}}]))
            runs = json.load(open({str(self.checks)!r}))
            for run in runs:
                run.update(status="completed", conclusion="success")
                for job in run["jobs"]:
                    job.update(status="completed", conclusion="success")
            open({str(self.checks)!r}, "w").write(json.dumps(runs))
        """)
        writer = subprocess.Popen([sys.executable, "-c", catch_up])
        try:
            result = self.merge("--wait-minutes", "1")
        finally:
            writer.wait()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.merged()), 1)

    def test_without_the_watch_workflow_it_refuses_with_branch_protection_too(self):
        self.git("switch", "-q", "main")
        self.git("rm", "-q", ".github/workflows/keyturn-watch.yml")
        self.tip = self.commit("remove the watch")
        self.git("push", "-q", "origin", "main")
        self.git("switch", "-q", "task/delivery-1")
        self.git("rebase", "-q", "main")
        self.head = self.git("rev-parse", "HEAD")
        self.git("push", "-q", "-f", "origin", "task/delivery-1")
        self.set_prs([self.pr()])
        self.set_gate(self.gate_run())
        self.set_activity(self.tip, PUSHED)
        self.assert_refused(self.merge(), "keyturn-watch.yml is not on main")
        self.set_protection(rules=[{"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": True,
            "required_status_checks": [{"context": "keyturn gate"}, {"context": "keyturn conditions"}]}}],
            branch={"protected": True, "protection": {"enabled": True}})
        self.assert_refused(self.merge(), "needed with branch protection too")

    def test_the_protection_option_reads_rulesets_and_classic_protection_and_merges_nothing(self):
        def protection() -> str:
            result = self.merge("--protection")
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()
        self.assertEqual(protection(), "not protected")
        self.set_protection(rules=[], branch={"protected": True, "protection": {"enabled": True, "required_status_checks": {
            "contexts": ["keyturn gate"], "checks": [{"context": "keyturn conditions", "app_id": 15368}]}}})
        self.assertEqual(protection(), "protected")
        self.rules.write_text("not json", encoding="utf-8")
        self.assertEqual(protection(), "protected")

    def test_the_protection_option_says_not_known_when_the_rules_cannot_be_read(self):
        # On a private repository on GitHub Free, the rules answer 403, as they do for a token without a permission.
        self.env["FAKE_GH_RULES_FAIL"] = "1"
        result = self.merge("--protection")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "not known"), result.stderr)
        self.set_protection(rules=[], branch={"protected": True, "protection": {"enabled": True, "required_status_checks": {
            "contexts": ["keyturn gate", "keyturn conditions"]}}})
        self.assertEqual(self.merge("--protection").stdout.strip(), "protected")
        self.assertEqual(self.merged(), [])

    def test_a_merge_commit_that_is_not_the_checked_head_on_the_checked_tip_stops_for_the_maintainer(self):
        moved = self.push_to_main("pushed between the check and the merge", move=False)
        self.env["FAKE_GH_MERGE_PARENT"] = moved
        result = self.merge()
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("not the checked tip", result.stderr)
        self.assertEqual(len(self.merged()), 1)

    def test_a_merge_commit_that_cannot_be_read_after_the_merge_is_exit_4_not_2(self):
        # A fetch after the merge that fails or times out: the pull request is merged all the same.
        self.script.write_text(self.script.read_text(encoding="utf-8").replace(
            "        run([\"git\", \"fetch\", \"--quiet\", \"--no-tags\", \"origin\", f\"+refs/heads/{default}:refs/remotes/origin/{default}\"], root)\n        if run(",
            "        raise SetupError(\"git fetch: no answer in 5 minutes\")\n        if run("), encoding="utf-8")
        result = self.merge()
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("could not be read", result.stderr)
        self.assertEqual(len(self.merged()), 1)

    def test_a_merge_commit_with_another_tree_stops_for_the_maintainer(self):
        self.env["FAKE_GH_MERGE_TREE"] = self.git("rev-parse", "main^{tree}")
        (self.root / "file").write_text("x", encoding="utf-8")
        self.git("add", "file")
        self.head = self.commit("a change")
        self.git("push", "-q", "origin", "task/delivery-1")
        self.set_prs([self.pr()])
        self.set_gate(self.gate_run())
        result = self.merge()
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("does not have the tree of the checked head", result.stderr)

    def test_from_another_branch_it_stops(self):
        self.git("switch", "-q", "main")
        self.assertEqual(self.merge().returncode, 2)
        self.assertEqual(self.merged(), [])


class RecordedVouchTest(unittest.TestCase):
    """merge.py passes the vouch resume recorded to its local conditions check (ADR 0057)."""

    def test_the_newest_recorded_vouch_is_passed_and_none_without_one(self):
        sys.path.insert(0, str(HERE))
        import merge
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

            def git(*args: str) -> str:
                return subprocess.run(["git", *args], cwd=root, env=env, check=True, capture_output=True, text=True).stdout.strip()

            git("init", "-q", "-b", "main")
            git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "base")
            self.assertEqual(merge.recorded_vouch(root, "delivery-1", git("rev-parse", "HEAD")), [])
            state = root / "keyturn" / "internal" / "state" / "delivery-1.md"
            state.parent.mkdir(parents=True)
            first, second = "a" * 40, "b" * 40
            state.write_text(f"## History\n\n- t: resumed: in implement (documents vouched for at `{first}`, by the "
                             f"maintainer's decision)\n- t: resumed: in implement (documents vouched for at `{second}`, by "
                             "the maintainer's decision)\n", encoding="utf-8")
            git("add", "-A")
            git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "-m", "state")
            self.assertEqual(merge.recorded_vouch(root, "delivery-1", git("rev-parse", "HEAD")),
                             ["--documents-vouched", f"delivery-1:{second}"])


if __name__ == "__main__":
    unittest.main()
