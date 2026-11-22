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

# A stand-in for the GitHub CLI: it records each call, answers `pr list` from FAKE_GH_PRS, the check runs from
# FAKE_GH_CHECKS, and refuses the merge when FAKE_GH_MERGE_FAILS is set.
FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(sys.argv[1:]) + "\\n")
    if sys.argv[1:3] == ["pr", "list"]:
        print(open(os.environ["FAKE_GH_PRS"], encoding="utf-8").read())
    elif sys.argv[1] == "api" and "/check-runs" in sys.argv[2]:
        print(open(os.environ["FAKE_GH_CHECKS"], encoding="utf-8").read())
    elif sys.argv[1] == "api" and sys.argv[2].endswith("/merge"):
        if os.environ.get("FAKE_GH_MERGE_FAILS"):
            print("Head branch was modified. Review and try the merge again.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps({"merged": True}))
    elif sys.argv[1] == "api" and "/pulls/" in sys.argv[2]:
        print(json.dumps({"merged": bool(os.environ.get("FAKE_GH_MERGED_ANYWAY"))}))
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
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.origin = tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True, env=self.env)
        self.root = tmp / "project"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.commit("first")
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
        self.conditions_log = tmp / "conditions.log"
        self.set_prs([self.pr()])
        self.set_checks(("keyturn gate", "success"), ("keyturn conditions", "success"))
        self.env.update(PATH=f"{bin_dir}{os.pathsep}{self.env['PATH']}", FAKE_GH_LOG=str(self.log),
                        FAKE_GH_PRS=str(self.prs), FAKE_GH_CHECKS=str(self.checks),
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

    def set_checks(self, *checks: tuple[str, str | None], app: str = "github-actions") -> None:
        runs = [{"id": n, "name": name, "app": {"slug": app}, "status": "completed" if conclusion else "in_progress",
                 "conclusion": conclusion, "html_url": f"https://github.com/owner/project/runs/{n}"}
                for n, (name, conclusion) in enumerate(checks, 1)]
        self.checks.write_text(json.dumps({"total_count": len(runs), "check_runs": runs}), encoding="utf-8")

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
                                          "-f", f"sha={self.head}", "-f", "commit_title=keyturn: delivery-1 (#7)"]])
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
        self.set_checks(("keyturn gate", "success"), ("keyturn conditions", "failure"))
        self.assert_refused(self.merge(), "did not pass: keyturn conditions (failure")
        self.set_checks(("keyturn gate", "success"), ("keyturn conditions", None))
        self.assert_pending(self.merge(), "keyturn conditions on")
        self.set_checks(("keyturn gate", "success"))
        self.assert_pending(self.merge(), "have not finished (or not started)")

    def test_a_check_from_another_app_does_not_count(self):
        self.set_checks(("keyturn gate", "success"), ("keyturn conditions", "success"), app="someone-else")
        self.assert_pending(self.merge(), "have not finished (or not started)")

    def test_the_newest_run_of_a_check_counts(self):
        self.set_checks(("keyturn gate", "success"), ("keyturn conditions", "failure"), ("keyturn conditions", "success"))
        self.assertEqual(self.merge().returncode, 0)

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

    def test_from_another_branch_it_stops(self):
        self.git("switch", "-q", "main")
        self.assertEqual(self.merge().returncode, 2)
        self.assertEqual(self.merged(), [])


if __name__ == "__main__":
    unittest.main()
