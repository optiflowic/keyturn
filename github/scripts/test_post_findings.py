"""Tests for post_findings.py. Run from the repository root: python3 -m unittest discover -s github/scripts"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("post_findings.py")

# A stand-in for the GitHub CLI: `pr list` answers from FAKE_GH_PRS; `api user` is FAKE_GH_LOGIN; the reviews are kept
# in FAKE_GH_REVIEWS (a JSON list), listed one per line as the script's --jq asks, and a POST adds to them. With
# FAKE_GH_REFUSE_COMMENTS set, a POST with line comments is refused, as GitHub refuses a line outside its diff.
FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    args = sys.argv[1:]
    with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(args) + "\\n")
    reviews_file = os.environ["FAKE_GH_REVIEWS"]
    reviews = json.load(open(reviews_file, encoding="utf-8"))
    if args[:2] == ["pr", "list"]:
        print(open(os.environ["FAKE_GH_PRS"], encoding="utf-8").read())
    elif args[:2] == ["api", "user"]:
        print(os.environ["FAKE_GH_LOGIN"])
    elif args[0] == "api" and "--method" in args:
        payload = json.load(open(args[args.index("--input") + 1], encoding="utf-8"))
        if payload.get("comments") and os.environ.get("FAKE_GH_REFUSE_COMMENTS"):
            reason = os.environ["FAKE_GH_REFUSE_COMMENTS"]
            print(reason if reason != "1" else "Unprocessable Entity: Line could not be resolved", file=sys.stderr)
            sys.exit(1)
        reviews.append({"user": {"login": os.environ["FAKE_GH_LOGIN"]}, "body": payload["body"], "payload": payload})
        json.dump(reviews, open(reviews_file, "w", encoding="utf-8"))
        print(json.dumps({"id": len(reviews)}))
    elif args[0] == "api":
        for review in reviews:
            print(json.dumps({"login": review["user"]["login"], "body": review["body"]}))
""")

REPORT = """\
# Review: delivery-1

- Reviewed by: reviewer
- Reviewed change: `{base}`..`{head}`
- Compared against: design.md

## Summary

Three findings. Nothing for @someone to do.

## Findings

### F-1: Unclear name

- Location: `app/main.py:2`
- Severity: low
- Category: readability
- Based on: C-1
- Status: {status}

The name `cnt` does not say what it counts.

### F-2: Outside the diff

- Location: `app/main.py:90`
- Severity: medium
- Category: design fit
- Based on: design, "Parts"
- Status: open

Not on a line of the change.

### F-3: About the design

- Location: design, "Data model"
- Severity: low
- Category: design fit
- Based on: design
- Status: open

A table the design does not have.
"""


class PostFindingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", KEYTURN_PUSH_WAIT_SECONDS="0")
        origin = tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env=self.env)
        self.root = tmp / "project"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.put("app/main.py", "".join(f"line {n}\n" for n in range(1, 101)))
        self.base = self.commit("first")
        self.git("remote", "add", "origin", "https://github.com/owner/project.git")
        self.git("config", f"url.{origin}.insteadOf", "https://github.com/owner/project.git")
        self.git("push", "-q", "origin", "main")
        self.git("remote", "set-head", "origin", "main")
        self.git("fetch", "-q", "origin")
        self.git("switch", "-q", "-c", "task/delivery-1")
        self.put("app/main.py", "line 1\ncnt = 0\ncnt += 1\n" + "".join(f"line {n}\n" for n in range(4, 101)))
        self.developer = self.commit("feat: count")
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH, encoding="utf-8")
        (bin_dir / "gh").chmod(0o755)
        self.log = tmp / "gh.log"
        self.prs = tmp / "prs.json"
        self.reviews = tmp / "reviews.json"
        self.reviews.write_text("[]", encoding="utf-8")
        self.env.update(PATH=f"{bin_dir}{os.pathsep}{self.env['PATH']}", FAKE_GH_LOG=str(self.log),
                        FAKE_GH_PRS=str(self.prs), FAKE_GH_REVIEWS=str(self.reviews), FAKE_GH_LOGIN="agent")

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

    def report(self, status: str = "open", extra: str = "", path: str = "keyturn/internal/review.md") -> str:
        self.put(path, REPORT.format(base=self.base, head=self.developer, status=status) + extra)
        commit = self.commit("docs(review): review delivery-1")
        self.pushed()
        return commit

    def pushed(self, head: str | None = None, state: str = "OPEN") -> None:
        self.prs.write_text(json.dumps([{"number": 7, "url": "https://github.com/owner/project/pull/7", "state": state,
                                         "isDraft": True, "isCrossRepository": False, "baseRefName": "main",
                                         "headRefOid": head or self.git("rev-parse", "HEAD")}]), encoding="utf-8")

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root, env=self.env, capture_output=True,
                              text=True)

    def posts(self) -> list[dict]:
        return [review["payload"] for review in json.loads(self.reviews.read_text(encoding="utf-8")) if "payload" in review]

    def test_first_post_puts_a_finding_at_its_line_and_the_others_in_the_text(self):
        commit = self.report()
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 0, result.stderr)
        [post] = self.posts()
        self.assertEqual(post["event"], "COMMENT")
        self.assertEqual(post["commit_id"], self.developer)
        self.assertEqual([(c["path"], c["line"]) for c in post["comments"]], [("app/main.py", 2)])
        self.assertIn("F-1: Unclear name", post["comments"][0]["body"])
        self.assertIn("#### F-2: Outside the diff", post["body"])
        self.assertIn("#### F-3: About the design", post["body"])
        self.assertNotIn("F-1", post["body"])
        blob = self.git("rev-parse", f"{commit}:keyturn/internal/review.md")
        self.assertIn(f"<!-- keyturn-findings: review {blob} {commit} -->", post["body"])
        self.assertIn(f"https://github.com/owner/project/blob/{commit}/keyturn/internal/review.md", post["body"])

    def test_a_mention_in_the_report_notifies_nobody(self):
        commit = self.report()
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 0)
        self.assertNotIn("@someone", self.posts()[0]["body"])

    def test_a_rerun_with_the_same_report_posts_nothing(self):
        commit = self.report()
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 0)
        self.git("commit", "-q", "--allow-empty", "-m", "chore(state): record review of delivery-1")
        self.pushed()
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing new", result.stdout)
        self.assertEqual(len(self.posts()), 1)

    def test_a_rerun_posts_only_what_changed(self):
        self.assertEqual(self.run_script("delivery-1", "review", self.report()).returncode, 0)
        new = "\n### F-4: New problem\n\n- Location: `app/main.py:3`\n- Severity: medium\n- Category: conventions\n" \
              "- Based on: C-2\n- Status: open\n\nAnother one.\n"
        commit = self.report(status="fixed", extra=new)
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 0, result.stderr)
        second = self.posts()[1]
        self.assertEqual([(c["path"], c["line"]) for c in second["comments"]], [("app/main.py", 3)])
        self.assertIn("Fixed: F-1 (Unclear name)", second["body"])
        self.assertNotIn("F-2", second["body"])
        self.assertNotIn("F-3", second["body"])

    def test_a_rerun_where_no_finding_changed_posts_nothing(self):
        self.assertEqual(self.run_script("delivery-1", "review", self.report()).returncode, 0)
        text = (self.root / "keyturn/internal/review.md").read_text(encoding="utf-8")
        self.put("keyturn/internal/review.md", text.replace("Three findings.", "Three findings, checked again."))
        commit = self.commit("docs(review): rerun")
        self.pushed()
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing new", result.stdout)
        self.assertEqual(len(self.posts()), 1)

    def test_a_failure_other_than_a_line_is_not_posted_again_in_the_text(self):
        commit = self.report()
        self.env["FAKE_GH_REFUSE_COMMENTS"] = "Bad Gateway"
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 1)
        self.assertEqual(self.posts(), [])

    def test_a_finding_gone_from_the_report_is_said(self):
        self.assertEqual(self.run_script("delivery-1", "review", self.report()).returncode, 0)
        text = (self.root / "keyturn/internal/review.md").read_text(encoding="utf-8")
        self.put("keyturn/internal/review.md", text[:text.index("### F-3")])
        commit = self.commit("docs(review): rerun")
        self.pushed()
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 0)
        self.assertIn("No longer in the report: F-3 (About the design)", self.posts()[1]["body"])

    def test_another_accounts_marker_does_not_count(self):
        commit = self.report()
        blob = self.git("rev-parse", f"{commit}:keyturn/internal/review.md")
        self.reviews.write_text(json.dumps([{"user": {"login": "someone-else"},
                                             "body": f"<!-- keyturn-findings: review {blob} {commit} -->"}]), encoding="utf-8")
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 0)
        self.assertEqual(len(self.posts()), 1)

    def test_a_marker_quoted_in_a_report_does_not_count(self):
        commit = self.report()
        blob = self.git("rev-parse", f"{commit}:keyturn/internal/review.md")
        self.reviews.write_text(json.dumps([{"user": {"login": "agent"},
                                             "body": f"quoted <!-- keyturn-findings: review {blob} {commit} --> in code\n\nend"}]),
                                encoding="utf-8")
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 0)
        self.assertEqual(len(self.posts()), 1)

    def test_the_two_roles_have_markers_of_their_own(self):
        self.assertEqual(self.run_script("delivery-1", "review", self.report()).returncode, 0)
        commit = self.report(path="keyturn/internal/security-review.md")
        result = self.run_script("delivery-1", "security-review", commit)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("keyturn-findings: security-review", self.posts()[1]["body"])
        self.assertIn("#### F-2", self.posts()[1]["body"])

    def test_a_refused_line_comment_posts_every_finding_in_the_text(self):
        commit = self.report()
        self.env["FAKE_GH_REFUSE_COMMENTS"] = "1"
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 0, result.stderr)
        [post] = self.posts()
        self.assertEqual(post["comments"], [])
        self.assertIn("#### F-1: Unclear name", post["body"])

    def test_a_range_shown_whole_is_one_comment_over_its_lines(self):
        self.report()
        text = (self.root / "keyturn/internal/review.md").read_text(encoding="utf-8")
        self.put("keyturn/internal/review.md", text.replace("`app/main.py:2`", "`app/main.py:2-3`"))
        commit = self.commit("docs(review): range")
        self.pushed()
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 0)
        [comment] = self.posts()[0]["comments"]
        self.assertEqual((comment["start_line"], comment["line"]), (2, 3))

    def test_a_pull_request_not_at_the_head_is_refused(self):
        commit = self.report()
        self.pushed(head=self.developer)
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 1)
        self.assertIn("push task/delivery-1 first", result.stderr)
        self.assertEqual(self.posts(), [])

    def test_no_open_pull_request_is_refused(self):
        commit = self.report()
        self.prs.write_text("[]", encoding="utf-8")
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 1)
        self.pushed(state="MERGED")
        self.assertEqual(self.run_script("delivery-1", "review", commit).returncode, 1)
        self.assertEqual(self.posts(), [])

    def test_it_runs_only_on_the_task_branch(self):
        commit = self.report()
        self.git("switch", "-q", "main")
        result = self.run_script("delivery-1", "review", commit)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not task/delivery-1", result.stderr)

    def test_a_commit_without_the_report_or_off_the_branch_cannot_run(self):
        self.report()
        self.assertEqual(self.run_script("delivery-1", "review", self.developer).returncode, 2)
        self.assertEqual(self.run_script("delivery-1", "security-review", "HEAD").returncode, 2)
        self.git("switch", "-q", "-c", "other", "main")
        self.put("keyturn/internal/review.md", "# Review: other\n")
        other = self.commit("other")
        self.git("switch", "-q", "task/delivery-1")
        self.assertEqual(self.run_script("delivery-1", "review", other).returncode, 2)
        self.assertEqual(self.posts(), [])


if __name__ == "__main__":
    unittest.main()
