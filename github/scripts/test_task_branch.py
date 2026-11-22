"""Tests for task_branch.py. Run from the repository root: python3 -m unittest discover -s github/scripts"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("task_branch.py")

# A stand-in for the GitHub CLI: it records each call, and answers `pr list` from PRS (a JSON list in a file).
FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    log = os.environ["FAKE_GH_LOG"]
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(sys.argv[1:]) + "\\n")
    if sys.argv[1:3] == ["pr", "list"]:
        print(open(os.environ["FAKE_GH_PRS"], encoding="utf-8").read())
    elif sys.argv[1:3] in (["pr", "create"], ["pr", "edit"]):
        body = open(sys.argv[sys.argv.index("--body-file") + 1], encoding="utf-8").read()
        with open(log + ".body", "w", encoding="utf-8") as f:
            f.write(body)
        if sys.argv[2] == "create":
            print("https://github.com/owner/project/pull/7")
""")


class TaskBranchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.origin = tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True, env=self.env)
        self.root = tmp / "project"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.put("README.md", "project\n")
        self.commit("first")
        # origin looks like GitHub, and Git is sent to the bare repository instead (the test never reaches the network).
        self.git("remote", "add", "origin", "https://github.com/owner/project.git")
        self.git("config", f"url.{self.origin}.insteadOf", "https://github.com/owner/project.git")
        self.git("push", "-q", "origin", "main")
        self.git("remote", "set-head", "origin", "main")
        self.git("switch", "-q", "-c", "task/delivery-1")
        self.put("keyturn/internal/state/delivery-1.md", "# Task state: delivery-1\n")
        self.commit("chore(state): start delivery-1")
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH, encoding="utf-8")
        (bin_dir / "gh").chmod(0o755)
        self.log = tmp / "gh.log"
        self.prs = tmp / "prs.json"
        self.set_prs([])
        self.env.update(PATH=f"{bin_dir}{os.pathsep}{self.env['PATH']}", FAKE_GH_LOG=str(self.log), FAKE_GH_PRS=str(self.prs))

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def put(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def set_prs(self, prs: list[dict]) -> None:
        self.prs.write_text(json.dumps(prs), encoding="utf-8")

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root, env=self.env, capture_output=True, text=True)

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def remote(self, ref: str) -> str:
        result = subprocess.run(["git", "--git-dir", str(self.origin), "rev-parse", "--verify", "--quiet", ref],
                                env=self.env, capture_output=True, text=True)
        return result.stdout.strip()

    # push

    def test_push_sends_the_task_branch_only(self):
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.remote("refs/heads/task/delivery-1"), self.git("rev-parse", "HEAD"))
        self.assertEqual(self.remote("refs/heads/main"), self.git("rev-parse", "main"))

    def test_push_from_another_branch_is_refused(self):
        self.git("switch", "-q", "main")
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("the current branch is main, not task/delivery-1", result.stderr)
        self.assertEqual(self.remote("refs/heads/task/delivery-1"), "")

    def test_push_of_another_task_is_refused(self):
        result = self.run_script("push", "delivery-2")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.remote("refs/heads/task/delivery-2"), "")

    def test_a_push_that_would_rewrite_the_remote_branch_is_refused(self):
        self.assertEqual(self.run_script("push", "delivery-1").returncode, 0)
        pushed = self.remote("refs/heads/task/delivery-1")
        self.git("commit", "-q", "--amend", "-m", "rewritten")
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("refused", result.stderr)
        self.assertEqual(self.remote("refs/heads/task/delivery-1"), pushed)

    def test_a_task_name_that_is_not_one_is_refused(self):
        for name in ("A", "x/../main", "-f", "main"):
            result = self.run_script("push", "--", name) if name.startswith("-") else self.run_script("push", name)
            self.assertEqual(result.returncode, 2, name + result.stderr)

    def test_without_origin_it_stops(self):
        self.git("remote", "remove", "origin")
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no remote named origin", result.stderr)

    def test_a_pre_push_hook_does_not_run(self):
        hook = self.root / ".git" / "hooks" / "pre-push"
        hook.write_text("#!/bin/sh\ntouch hook-ran\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)
        self.assertEqual(self.run_script("push", "delivery-1").returncode, 0)
        self.assertFalse((self.root / "hook-ran").exists())

    # open and ready

    def test_open_creates_a_draft_to_the_default_branch_with_the_documents(self):
        self.put("keyturn/client/requirements.md", "# Requirements\n")
        self.commit("docs(spec): requirements")
        result = self.run_script("open", "delivery-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        create = [call for call in self.calls() if call[:2] == ["pr", "create"]][0]
        self.assertIn("--draft", create)
        self.assertEqual(create[create.index("--base") + 1], "main")
        self.assertEqual(create[create.index("--head") + 1], "task/delivery-1")
        body = Path(str(self.log) + ".body").read_text(encoding="utf-8")
        head = self.git("rev-parse", "HEAD")
        self.assertIn(f"- [Requirements](https://github.com/owner/project/blob/{head}/keyturn/client/requirements.md)", body)
        self.assertEqual(create[create.index("--repo") + 1], "owner/project")
        self.assertNotIn("Acceptance guide", body)

    def test_gh_is_given_origin_s_repository_whatever_the_environment_says(self):
        self.env["GH_REPO"] = "other/repo"
        self.set_prs([{"number": 7, "url": "u7", "isDraft": True, "isCrossRepository": False, "baseRefName": "main"}])
        self.assertEqual(self.run_script("ready", "delivery-1").returncode, 0)
        self.assertTrue(self.calls())
        for call in self.calls():
            self.assertEqual(call[call.index("--repo") + 1], "owner/project", call)

    def test_an_origin_that_is_not_github_stops(self):
        self.git("remote", "set-url", "origin", str(self.origin))
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a GitHub repository", result.stderr)

    def test_a_push_url_that_differs_from_origin_s_stops(self):
        self.git("remote", "set-url", "--push", "origin", "https://github.com/other/repo.git")
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("origin pushes to", result.stderr)

    def test_tags_are_never_pushed(self):
        self.git("config", "push.followTags", "true")
        self.git("tag", "-a", "v1", "-m", "a tag")
        self.assertEqual(self.run_script("push", "delivery-1").returncode, 0)
        self.assertEqual(self.remote("refs/tags/v1"), "")

    def test_open_updates_the_existing_pull_request(self):
        self.set_prs([{"number": 7, "url": "u7", "isDraft": True, "isCrossRepository": False, "baseRefName": "main"}])
        result = self.run_script("open", "delivery-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[:2] == ["pr", "create"] for call in self.calls()))
        self.assertTrue(any(call[:2] == ["pr", "edit"] and call[-3] == "7" for call in self.calls()))

    def test_a_fork_s_pull_request_is_never_the_task_s(self):
        self.set_prs([{"number": 8, "url": "u8", "isDraft": True, "isCrossRepository": True, "baseRefName": "main"}])
        self.assertEqual(self.run_script("open", "delivery-1").returncode, 0)
        self.assertTrue(any(call[:2] == ["pr", "create"] for call in self.calls()))
        self.assertFalse(any(call[:2] == ["pr", "edit"] for call in self.calls()))

    def test_a_pull_request_to_another_branch_is_refused(self):
        self.set_prs([{"number": 7, "url": "u7", "isDraft": True, "isCrossRepository": False, "baseRefName": "develop"}])
        result = self.run_script("open", "delivery-1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not to the default branch main", result.stderr)

    def test_ready_marks_the_draft_ready(self):
        self.set_prs([{"number": 7, "url": "u7", "isDraft": True, "isCrossRepository": False, "baseRefName": "main"}])
        self.assertEqual(self.run_script("ready", "delivery-1").returncode, 0)
        self.assertTrue(any(call[:2] == ["pr", "ready"] and call[-1] == "7" for call in self.calls()))

    def test_ready_without_a_pull_request_is_refused(self):
        result = self.run_script("ready", "delivery-1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("open it first", result.stderr)

    def body(self) -> str:
        return Path(str(self.log) + ".body").read_text(encoding="utf-8")

    def test_the_description_carries_the_delivery_report_s_summary_and_what_to_do(self):
        # The headings are in the client's language: the sections are found by their place, not their names.
        self.put("keyturn/client/delivery-report.md", "# 納品レポート\n\n本文。\n\n## 要約\n\n<!-- a comment -->\n\n"
                 "納品 1 ができました。\n\n## あなたがすること\n\n> [!IMPORTANT]\n> - 確かめてください。\n\n"
                 "## 納品したもの\n\n表。\n")
        self.put("keyturn/client/acceptance-guide.md", "# 受け入れガイド\n\n全文。\n")
        self.commit("docs(delivery): add the documents")
        self.assertEqual(self.run_script("open", "delivery-1").returncode, 0)
        body = self.body()
        self.assertIn("### 要約\n\n納品 1 ができました。", body)
        self.assertIn("### あなたがすること\n\n> [!IMPORTANT]\n> - 確かめてください。", body)
        self.assertNotIn("納品したもの", body)
        self.assertNotIn("a comment", body)
        self.assertNotIn("全文", body)  # the acceptance guide is linked, never copied
        self.assertIn("- [Acceptance guide](", body)

    def test_ready_writes_the_description_again_from_the_head(self):
        self.set_prs([{"number": 7, "url": "u7", "state": "OPEN", "isDraft": True, "isCrossRepository": False,
                       "baseRefName": "main"}])
        self.put("keyturn/client/delivery-report.md", "# Report\n\n## Summary\n\nDone.\n\n## What you need to do\n\nCheck.\n")
        self.commit("docs(delivery): add the documents")
        self.assertEqual(self.run_script("ready", "delivery-1").returncode, 0)
        calls = [call[:2] for call in self.calls()]
        self.assertLess(calls.index(["pr", "edit"]), calls.index(["pr", "ready"]))
        self.assertIn("### Summary\n\nDone.", self.body())

    def test_a_closed_or_merged_pull_request_is_never_replaced(self):
        for state in ("CLOSED", "MERGED"):
            self.log.unlink(missing_ok=True)
            self.set_prs([{"number": 7, "url": "u7", "state": state, "isDraft": False, "isCrossRepository": False,
                           "baseRefName": "main"}])
            for command in ("open", "ready"):
                result = self.run_script(command, "delivery-1")
                self.assertEqual(result.returncode, 1, state + command)
                self.assertIn(f"was {state.lower()} (u7)", result.stderr)
                self.assertIn("ask the maintainer", result.stderr)
            self.assertFalse(any(call[:2] in (["pr", "create"], ["pr", "edit"], ["pr", "ready"]) for call in self.calls()))

    def test_the_open_pull_request_is_used_next_to_a_closed_one(self):
        self.set_prs([{"number": 6, "url": "u6", "state": "CLOSED", "isDraft": False, "isCrossRepository": False,
                       "baseRefName": "main"},
                      {"number": 7, "url": "u7", "state": "OPEN", "isDraft": True, "isCrossRepository": False,
                       "baseRefName": "main"}])
        self.assertEqual(self.run_script("open", "delivery-1").returncode, 0)
        self.assertTrue(any(call[:2] == ["pr", "edit"] and call[-3] == "7" for call in self.calls()))

    def test_a_push_refused_because_the_remote_branch_moved_says_what_to_do(self):
        self.assertEqual(self.run_script("push", "delivery-1").returncode, 0)
        other = Path(self.tmp.name) / "other"
        subprocess.run(["git", "clone", "-q", "-b", "task/delivery-1", str(self.origin), str(other)], check=True, env=self.env)
        for args in (["config", "user.email", "o@example.com"], ["config", "user.name", "O"],
                     ["commit", "-q", "--allow-empty", "-m", "from elsewhere"], ["push", "-q", "origin", "task/delivery-1"]):
            subprocess.run(["git", *args], cwd=other, check=True, env=self.env)
        moved = self.remote("refs/heads/task/delivery-1")
        self.put("next.md", "next\n")
        self.commit("next")
        result = self.run_script("push", "delivery-1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("When the task branch on origin moved", result.stderr)
        self.assertEqual(self.remote("refs/heads/task/delivery-1"), moved)

    def test_open_from_another_branch_is_refused(self):
        self.git("switch", "-q", "main")
        self.assertEqual(self.run_script("open", "delivery-1").returncode, 2)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
