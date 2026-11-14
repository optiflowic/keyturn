"""Tests for pr_review.py. Run from the repository root: python3 -m unittest discover -s scripts

They run on saved sample responses in testdata/ and on a stand-in for gh, so they need no network access.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).with_name("pr_review.py")
TESTDATA = Path(__file__).with_name("testdata")
REVIEW = TESTDATA / "review.json"
RATE_LIMITED_REPLY = TESTDATA / "rate-limited-reply.json"
THREADS_PAGE_1 = TESTDATA / "threads-page-1.json"
THREADS_PAGE_2 = TESTDATA / "threads-page-2.json"

sys.path.insert(0, str(SCRIPT.parent))
import pr_review  # noqa: E402

BEFORE_THE_WAIT_ENDS = datetime(2026, 11, 12, 10, 30, tzinfo=timezone.utc)
AFTER_THE_WAIT_ENDS = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

EXPECTED = """PR #42: feat(example): add an example change (open)
Review decision: changes requested
Latest review per reviewer:
- coderabbitai: changes requested, 2026-11-12T08:30Z
- maintainer: commented, 2026-11-12T09:00Z
CodeRabbit rate limit: posted 2026-11-12T10:20Z, wait until 2026-11-12T11:04Z (34 min from now)
Failed pre-merge checks in CodeRabbit's latest review:
- Out of Scope Changes
- Docstring Coverage

Unresolved threads: 2

1. skills/example/scripts/example.py:146-147 by coderabbitai (1 reply, last by maintainer)
   Major · Functional Correctness · Quick win
   Check the exit code of `git add` before printing success.
   The script discards the return code of `git add`. If staging fails, it still prints "staged". See the docs.
   Check the return code and stop with an error when it is not zero.

2. skills/example/SKILL.md:20 by maintainer (2 replies, last by coderabbitai)
   Split the long function into steps.
   Paragraph 1 explains one more reason to split the function, with enough words to take up some room in the summary.
   Paragraph 2 explains one more reason to split the function, with enough words to take up some room in the summary.
   Paragraph 3 explains one more reason to split the function, with enough words to take up some room in the summary. …

Unresolved outdated threads: 1 (still to be resolved before merging)
- docs/DESIGN.md:30 by coderabbitai: Reword the outdated point.
"""


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summary(path: Path = REVIEW, now: datetime = BEFORE_THE_WAIT_ENDS, full: bool = False) -> str:
    return pr_review.summarize(load(path), now, full)


class SummaryTest(unittest.TestCase):
    def test_prints_the_review_state_and_the_open_threads(self):
        self.assertEqual(summary(), EXPECTED)

    def test_leaves_out_html_collapsed_sections_diffs_and_run_logs(self):
        text = summary(full=True)
        for noise in ("<", "Analysis chain", "Script executed", "Length of output", "Run ID", "rg -n",
                      "Committable suggestion", "IMPORTANT", "returncode != 0", "Prompt for AI Agents",
                      "Prompt text for AI agents", "https://", "```", "**"):
            self.assertNotIn(noise, text)

    def test_leaves_out_resolved_threads(self):
        text = summary(full=True)
        self.assertNotIn("Resolved point", text)
        self.assertNotIn("AGENTS.md", text)

    def test_lists_outdated_threads_by_their_first_line_only(self):
        text = summary(full=True)
        self.assertIn("\n- docs/DESIGN.md:30 by coderabbitai: Reword the outdated point.\n", text)
        self.assertNotIn("Minor", text)
        self.assertNotIn("Second line", text)

    def test_full_prints_every_line_of_a_point(self):
        text = summary(full=True)
        self.assertIn("Paragraph 6 explains", text)
        self.assertNotIn("…", text)

    def test_cuts_a_long_line_at_a_word(self):
        self.assertEqual(pr_review.shorten(["word " * 100], full=False), [("word " * 80).rstrip() + " …"])

    def test_says_when_the_rate_limit_wait_has_passed(self):
        self.assertIn(
            "CodeRabbit rate limit: posted 2026-11-12T10:20Z, wait until 2026-11-12T11:04Z (passed)\n",
            summary(now=AFTER_THE_WAIT_ENDS),
        )

    def test_reads_a_rate_limited_reply_without_a_wait_time(self):
        text = summary(RATE_LIMITED_REPLY)
        self.assertIn("Review decision: none\nLatest review per reviewer: none\n", text)
        self.assertIn("CodeRabbit rate limit: posted 2026-11-12T07:00Z, no wait time given\n", text)
        self.assertTrue(text.endswith("Unresolved threads: 0\n"))

    def test_reads_the_wait_from_an_earlier_comment_when_the_latest_reply_gives_none(self):
        # An `@coderabbitai review` that hits the limit: the summary comment gives the wait, and the reply after it
        # says only "Review rate limited."
        data = load(REVIEW)
        comments = data["data"]["repository"]["pullRequest"]["comments"]["nodes"]
        comments[0]["createdAt"] = comments[0]["updatedAt"] = "2026-11-12T10:21:00Z"
        self.assertIn(
            "CodeRabbit rate limit: posted 2026-11-12T10:21Z, no wait time given; the last one that gave one, "
            "posted 2026-11-12T10:20Z, said to wait until 2026-11-12T11:04Z (34 min from now)\n",
            pr_review.summarize(data, BEFORE_THE_WAIT_ENDS),
        )

    def test_ignores_rate_limit_text_from_other_authors(self):
        data = load(REVIEW)
        pr = data["data"]["repository"]["pullRequest"]
        pr["comments"]["nodes"] = [comment for comment in pr["comments"]["nodes"] if comment["author"]["login"] != "coderabbitai"]
        self.assertIn("CodeRabbit rate limit: none\n", pr_review.summarize(data, BEFORE_THE_WAIT_ENDS))

    def test_says_when_coderabbit_reviewed_after_the_rate_limit(self):
        data = load(REVIEW)
        reviews = data["data"]["repository"]["pullRequest"]["latestReviews"]["nodes"]
        reviews[1]["submittedAt"] = "2026-11-12T11:30:00Z"
        self.assertIn("(passed); CodeRabbit has reviewed since\n", pr_review.summarize(data, AFTER_THE_WAIT_ENDS))

    def test_reads_the_older_wait_format(self):
        data = load(RATE_LIMITED_REPLY)
        comment = data["data"]["repository"]["pullRequest"]["comments"]["nodes"][0]
        comment["body"] = (
            pr_review.RATE_LIMIT_MARKER
            + "\n> Please wait **1 hour, 2 minutes and 30 seconds** before requesting another review.\n"
        )
        self.assertIn(
            "CodeRabbit rate limit: posted 2026-11-12T07:00Z, wait until 2026-11-12T08:03Z (passed)\n",
            pr_review.summarize(data, AFTER_THE_WAIT_ENDS),
        )

    def test_leaves_out_the_failed_checks_line_when_none_failed(self):
        data = load(REVIEW)
        reviews = data["data"]["repository"]["pullRequest"]["latestReviews"]["nodes"]
        reviews[1]["body"] = "**Actionable comments posted: 2**\n"
        self.assertNotIn("Failed pre-merge checks", pr_review.summarize(data, BEFORE_THE_WAIT_ENDS))

    def test_reads_failed_checks_only_from_coderabbits_latest_review(self):
        # The maintainer's review in the sample lists a check too; it is not read.
        self.assertNotIn("Not CodeRabbit", summary())
        data = load(REVIEW)
        reviews = data["data"]["repository"]["pullRequest"]["latestReviews"]["nodes"]
        reviews.append({**reviews[1], "body": "Failed pre-merge checks:\n- Title check:\nShorten it.\n",
                        "submittedAt": "2026-11-12T08:00:00Z"})
        text = pr_review.summarize(data, BEFORE_THE_WAIT_ENDS)
        self.assertIn("- Out of Scope Changes\n- Docstring Coverage\n\n", text)
        self.assertNotIn("Title", text)

    def test_reads_failed_checks_separated_by_blank_lines(self):
        body = "Failed pre-merge checks:\n- Title check:\nShorten it.\n\n- Description check:\nFill it in.\n\nDone.\n- Later:\n"
        self.assertEqual(pr_review.failed_checks(body), ["Title", "Description"])

    def test_stops_reading_failed_checks_at_a_fence(self):
        body = "```\nFailed pre-merge checks:\n- Title check:\nShorten it.\n```\n- Line 3:\n"
        self.assertEqual(pr_review.failed_checks(body), ["Title"])

    def test_warns_when_not_every_thread_was_read(self):
        data = load(REVIEW)
        data["data"]["repository"]["pullRequest"]["reviewThreads"]["pageInfo"]["hasNextPage"] = True
        self.assertIn("only those it holds were read", pr_review.summarize(data, BEFORE_THE_WAIT_ENDS))

    def test_reports_errors_in_the_response(self):
        data = {"data": {"repository": {"pullRequest": None}},
                "errors": [{"message": "Could not resolve to a PullRequest with the number of 999."}]}
        with self.assertRaisesRegex(pr_review.Failure, "number of 999"):
            pr_review.summarize(data, BEFORE_THE_WAIT_ENDS)

    def test_reports_errors_even_when_the_pull_request_is_there(self):
        data = load(REVIEW)
        data["data"]["repository"]["pullRequest"]["reviewThreads"] = None
        data["errors"] = [{"message": "Something went wrong while executing your query."}]
        with self.assertRaisesRegex(pr_review.Failure, "the response has errors: Something went wrong"):
            pr_review.summarize(data, BEFORE_THE_WAIT_ENDS)

    def test_reports_a_missing_part_of_the_pull_request(self):
        data = load(REVIEW)
        data["data"]["repository"]["pullRequest"]["reviewThreads"] = None
        with self.assertRaisesRegex(pr_review.Failure, "no reviewThreads"):
            pr_review.summarize(data, BEFORE_THE_WAIT_ENDS)

    def test_shows_one_line_when_the_start_line_is_after_the_end_line(self):
        # After a push, GitHub can give a thread a startLine after its line.
        thread = {"isOutdated": False, "line": 88, "startLine": 89, "originalLine": 88, "originalStartLine": None}
        self.assertEqual(pr_review.lines_of(thread), ":88")
        self.assertEqual(pr_review.lines_of({**thread, "startLine": 86}), ":86-88")


class CleanTest(unittest.TestCase):
    def test_removes_nested_details(self):
        text = "a\n<details>\nb\n<details>\nc\n</details>\nd\n</details>\ne"
        self.assertEqual(pr_review.clean(text), ["a", "e"])

    def test_removes_an_unclosed_details_block_to_the_end(self):
        self.assertEqual(pr_review.clean("a\n<details>\nb\n"), ["a"])

    def test_removes_a_diff_closed_by_a_longer_fence(self):
        self.assertEqual(pr_review.clean("a\n```diff\n-old\n+new\n`````\nb\n"), ["a", "b"])

    def test_does_not_close_a_fence_with_a_shorter_one_or_the_other_character(self):
        text = "a\n````diff\n-old\n```\n~~~~\n+new\n````\nb\n"
        self.assertEqual(pr_review.clean(text), ["a", "b"])

    def test_keeps_code_blocks_that_are_not_diffs(self):
        self.assertEqual(pr_review.clean("Run:\n```sh\nmake test\n```\n"), ["Run:", "make test"])


class CommandTest(unittest.TestCase):
    def run_script(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False, env=env,
        )

    def fake_gh(self, directory: Path, response: Path | None, exit_code: int = 0, next_page: Path | None = None) -> dict:
        """Put a stand-in for gh first on PATH. It logs its arguments and prints the saved response.

        With next_page, it prints that response instead when asked for the page after "cursor-1".
        """
        log = directory / "gh.log"
        gh = directory / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            f'printf "%s\\n" "$*" >> "{log}"\n'
            'if [ "$1" = repo ]; then echo optiflowic/keyturn; exit 0; fi\n'
            + (f'case "$*" in *"after=cursor-1"*) cat "{next_page}"; exit 0;; esac\n' if next_page else "")
            + (f'cat "{response}"\n' if response else 'echo "HTTP 502" >&2\n')
            + f"exit {exit_code}\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        return {**os.environ, "PATH": f"{directory}{os.pathsep}{os.environ.get('PATH', '')}"}

    def test_input_prints_the_summary(self):
        result = self.run_script("--input", str(REVIEW), "--now", "2026-11-12T10:30Z")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, EXPECTED, ""))

    def test_fetches_the_pull_request_with_gh(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.fake_gh(Path(directory), REVIEW)
            result = self.run_script("42", "--now", "2026-11-12T10:30Z", env=env)
            calls = (Path(directory) / "gh.log").read_text(encoding="utf-8")
        self.assertEqual((result.returncode, result.stdout), (0, EXPECTED), result.stderr)
        self.assertTrue(calls.startswith("repo view --json nameWithOwner"))
        self.assertIn("api graphql -F owner=optiflowic -F name=keyturn -F number=42 -f query=", calls)
        self.assertIn("reviewThreads(first: 100, after: $after)", calls)
        self.assertNotIn("after=", calls)

    def test_reads_every_page_of_review_threads(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.fake_gh(Path(directory), THREADS_PAGE_1, next_page=THREADS_PAGE_2)
            result = self.run_script("300", "--repo", "optiflowic/keyturn", env=env)
            calls = (Path(directory) / "gh.log").read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unresolved threads: 1\n\n1. b.py:2 by coderabbitai\n   Open point on the second page.\n", result.stdout)
        self.assertNotIn("Resolved point", result.stdout)
        self.assertNotIn("Warning", result.stdout)
        self.assertEqual(calls.count("api graphql"), 2)
        self.assertIn("-f after=cursor-1", calls)

    def test_warns_when_a_saved_response_has_more_pages(self):
        result = self.run_script("--input", str(THREADS_PAGE_1))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Warning: the response has more review threads than it holds", result.stdout)

    def test_uses_the_given_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.fake_gh(Path(directory), REVIEW)
            result = self.run_script("42", "--repo", "someone/else", env=env)
            calls = (Path(directory) / "gh.log").read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("repo view", calls)
        self.assertIn("-F owner=someone -F name=else", calls)

    def test_reports_a_gh_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.fake_gh(Path(directory), None, exit_code=1)
            result = self.run_script("42", "--repo", "optiflowic/keyturn", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("error: gh api failed: HTTP 502", result.stderr)

    def test_needs_a_number_or_an_input_file(self):
        self.assertEqual(self.run_script().returncode, 2)
        self.assertEqual(self.run_script("42", "--input", str(REVIEW)).returncode, 2)

    def test_rejects_a_bad_time(self):
        result = self.run_script("--input", str(REVIEW), "--now", "2026-11-12 10:30")
        self.assertEqual(result.returncode, 2)
        self.assertIn("YYYY-MM-DDTHH:MMZ", result.stderr)


if __name__ == "__main__":
    unittest.main()
