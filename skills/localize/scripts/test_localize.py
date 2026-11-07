"""Tests for localize.py. Run with: python3 -m unittest discover skills/localize/scripts"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("localize.py")
sys.path.insert(0, str(SCRIPT.parent))
import localize  # noqa: E402

SOURCE = """# Title

Intro.

## First

One.

```sh
# not a heading
```

## Second

Two.
"""


class SplitSectionsTest(unittest.TestCase):
    def test_markdown_splits_at_headings_outside_code_fences(self):
        sections = localize.split_sections(SOURCE, is_markdown=True)
        self.assertEqual(
            [s.text.splitlines()[0] for s in sections],
            ["# Title", "## First", "## Second"],
        )
        self.assertIn("# not a heading", sections[1].text)

    def test_sections_join_back_to_the_source(self):
        sections = localize.split_sections(SOURCE, is_markdown=True)
        self.assertEqual("".join(s.text for s in sections), SOURCE)

    def test_other_files_are_one_section(self):
        self.assertEqual(len(localize.split_sections(SOURCE, is_markdown=False)), 1)

    def headings(self, text: str) -> list[str]:
        return [s.text.splitlines()[0] for s in localize.split_sections(text, is_markdown=True)]

    def test_a_shorter_fence_does_not_close_a_longer_one(self):
        text = "# A\n````md\n```\n# inside\n```\n````\n# B\n"
        self.assertEqual(self.headings(text), ["# A", "# B"])

    def test_a_tilde_line_does_not_close_a_backtick_fence(self):
        text = "# A\n```\n~~~\n# inside\n```\n# B\n"
        self.assertEqual(self.headings(text), ["# A", "# B"])

    def test_a_closer_with_trailing_text_does_not_close(self):
        text = "# A\n```\n``` not a closer\n# inside\n```\n# B\n"
        self.assertEqual(self.headings(text), ["# A", "# B"])

    def test_a_fence_indented_four_spaces_is_not_a_fence(self):
        text = "# A\n    ```\n# B\n"
        self.assertEqual(self.headings(text), ["# A", "# B"])


class CommandsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / "docs").mkdir()
        self.source = self.root / "docs" / "GUIDE.md"
        self.source.write_text(SOURCE, encoding="utf-8")
        self.work_file = self.root / ".keyturn/i18n/.work/ja/docs/GUIDE.md"
        self.target = self.root / ".keyturn/i18n/ja/docs/GUIDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def translate_work_file(self, marker: str) -> None:
        """Stand in for the AI: tag every line of the work file as translated."""
        lines = self.work_file.read_text(encoding="utf-8").splitlines(keepends=True)
        translated = [line if line.startswith("<!--") else f"{marker} {line}" for line in lines]
        self.work_file.write_text("".join(translated), encoding="utf-8")

    def first_translation(self) -> None:
        self.run_script("prepare", "ja", "docs/GUIDE.md")
        self.translate_work_file("[v1]")
        self.assertEqual(self.run_script("apply", "ja", "docs/GUIDE.md").returncode, 0)

    def test_new_file_is_missing_then_fresh(self):
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "missing docs/GUIDE.md\n")
        self.first_translation()
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "fresh docs/GUIDE.md\n")
        self.assertFalse(self.work_file.exists())
        self.assertEqual(list(self.work_file.parent.iterdir()), [])

    def test_work_file_uses_short_numbered_markers(self):
        self.run_script("prepare", "ja", "docs/GUIDE.md")
        markers = [line for line in self.work_file.read_text(encoding="utf-8").splitlines() if line.startswith("<!--")]
        self.assertEqual(markers[1:], [f"<!-- localize-section {n} -->" for n in (1, 2, 3)])

    def test_unchanged_source_is_not_retranslated(self):
        self.first_translation()
        result = self.run_script("prepare", "ja", "docs/GUIDE.md")
        self.assertIn("nothing to translate", result.stdout)
        self.assertFalse(self.work_file.exists())

    def test_only_the_changed_section_is_retranslated(self):
        self.first_translation()
        self.source.write_text(SOURCE.replace("Two.", "Two, edited."), encoding="utf-8")
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "stale docs/GUIDE.md\n")

        result = self.run_script("prepare", "ja", "docs/GUIDE.md")
        self.assertIn("sections to translate: 1 (reused: 2)", result.stdout)
        self.translate_work_file("[v2]")
        self.run_script("apply", "ja", "docs/GUIDE.md")

        translation = self.target.read_text(encoding="utf-8")
        self.assertIn("[v1] One.", translation)
        self.assertIn("[v2] Two, edited.", translation)
        self.assertNotIn("[v1] Two.", translation)
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "fresh docs/GUIDE.md\n")

    def test_apply_refuses_a_work_file_with_a_missing_section(self):
        self.run_script("prepare", "ja", "docs/GUIDE.md")
        text = self.work_file.read_text(encoding="utf-8")
        without_last_section = text.rsplit("<!-- localize-section", 1)[0]
        self.work_file.write_text(without_last_section, encoding="utf-8")
        result = self.run_script("apply", "ja", "docs/GUIDE.md")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.target.exists())

    def test_apply_refuses_when_the_source_changed_after_prepare(self):
        self.run_script("prepare", "ja", "docs/GUIDE.md")
        self.source.write_text(SOURCE + "\nMore.\n", encoding="utf-8")
        result = self.run_script("apply", "ja", "docs/GUIDE.md")
        self.assertIn("run prepare again", result.stderr)

    def test_a_line_ending_change_makes_the_translation_stale(self):
        self.first_translation()
        self.source.write_bytes(SOURCE.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "stale docs/GUIDE.md\n")

    def test_crlf_files_round_trip(self):
        self.source.write_bytes(SOURCE.replace("\n", "\r\n").encode("utf-8"))
        self.first_translation()
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "fresh docs/GUIDE.md\n")

    def test_a_translation_with_a_lost_marker_is_translated_again_in_full(self):
        self.first_translation()
        lines = self.target.read_text(encoding="utf-8").splitlines(keepends=True)
        second_marker = [i for i, line in enumerate(lines) if line.startswith("<!-- localize-section")][1]
        del lines[second_marker]
        self.target.write_text("".join(lines), encoding="utf-8")

        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "stale docs/GUIDE.md\n")
        result = self.run_script("prepare", "ja", "docs/GUIDE.md")
        self.assertIn("sections to translate: 3 (reused: 0)", result.stdout)
        self.translate_work_file("[v2]")
        self.run_script("apply", "ja", "docs/GUIDE.md")
        translation = self.target.read_text(encoding="utf-8")
        self.assertEqual(translation.count("One."), 1)
        self.assertNotIn("[v1]", translation)

    def test_a_translation_with_a_changed_marker_reuses_the_other_sections(self):
        self.first_translation()
        text = self.target.read_text(encoding="utf-8")
        marker_hash = text.split('<!-- localize-section sha256="')[2][:64]
        self.target.write_text(text.replace(marker_hash, "0" * 64), encoding="utf-8")
        result = self.run_script("prepare", "ja", "docs/GUIDE.md")
        self.assertIn("sections to translate: 1 (reused: 2)", result.stdout)

    def test_paths_are_relative_to_the_repository_root_from_any_folder(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "status", "ja", "docs/GUIDE.md"],
            cwd=self.root / "docs", capture_output=True, text=True,
        )
        self.assertEqual(result.stdout, "missing docs/GUIDE.md\n")

    def test_tracked_files_under_keyturn_stop_every_write(self):
        tracked = self.root / ".keyturn/i18n/ja/docs/GUIDE.md"
        tracked.parent.mkdir(parents=True)
        tracked.write_text("tracked\n", encoding="utf-8")
        subprocess.run(["git", "add", "-f", ".keyturn"], cwd=self.root, check=True)

        for command in (["ignore"], ["prepare", "ja", "docs/GUIDE.md"], ["apply", "ja", "docs/GUIDE.md"]):
            result = self.run_script(*command)
            self.assertEqual(result.returncode, 1, command)
            self.assertIn("Git tracks files under .keyturn/", result.stderr)
        self.assertEqual(tracked.read_text(encoding="utf-8"), "tracked\n")
        self.assertFalse(self.work_file.exists())

    def test_paths_outside_the_repository_are_refused(self):
        result = self.run_script("status", "ja", "../outside.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the repository", result.stderr)

    def test_invalid_language_is_refused(self):
        self.assertNotEqual(self.run_script("status", "../x", "docs/GUIDE.md").returncode, 0)

    def test_ignore_adds_keyturn_to_the_local_exclude_file_once(self):
        self.run_script("ignore")
        self.run_script("ignore")
        exclude = (self.root / ".git/info/exclude").read_text(encoding="utf-8")
        self.assertEqual(exclude.count(".keyturn/"), 1)

        self.first_translation()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.root, capture_output=True, text=True
        ).stdout
        self.assertNotIn(".keyturn", status)

    def test_ignore_leaves_an_existing_gitignore_rule_alone(self):
        (self.root / ".gitignore").write_text(".keyturn/\n", encoding="utf-8")
        result = self.run_script("ignore")
        self.assertIn("already git-ignored", result.stdout)
        exclude = self.root / ".git/info/exclude"
        self.assertFalse(exclude.exists() and ".keyturn/" in exclude.read_text(encoding="utf-8"))


class CleanBodyTest(unittest.TestCase):
    def test_hidden_html_comments_are_dropped_but_inline_code_is_kept(self):
        body = "Visible.\n<!-- hidden\ndata -->\nUse `<!-- x -->` here.\n"
        self.assertEqual(localize.clean_body(body), "Visible.\n\nUse `<!-- x -->` here.\n")

    def test_comments_inside_code_fences_are_kept(self):
        body = "```html\n<!-- shown -->\n```\n"
        self.assertEqual(localize.clean_body(body), body)

    def test_headings_move_below_the_comment_heading(self):
        body = "# Top\n\n## Sub\n\n```sh\n# shell comment\n```\n"
        self.assertEqual(
            localize.clean_body(body),
            "### Top\n\n#### Sub\n\n```sh\n# shell comment\n```\n",
        )

    def test_an_open_fence_is_closed(self):
        self.assertEqual(localize.clean_body("Text\n~~~\ncode\n"), "Text\n~~~\ncode\n~~~\n")

    def test_marker_lookalikes_cannot_pose_as_markers(self):
        body = "```\n<!-- localize-section 1 -->\n```\n"
        self.assertEqual(localize.clean_body(body), "```\n <!-- localize-section 1 -->\n```\n")

    def test_crlf_becomes_lf_and_empty_bodies_stay_empty(self):
        self.assertEqual(localize.clean_body("a\r\nb\r\n"), "a\nb\n")
        self.assertEqual(localize.clean_body(None), "")
        self.assertEqual(localize.clean_body("<!-- only hidden -->"), "")


FAKE_GH = """#!{python}
import json, os, sys
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if args[:2] == ["repo", "view"]:
    print("octo/demo")
    sys.exit(0)
with open(os.environ["FAKE_GH_DATA"]) as file:
    data = json.load(file)
endpoint = args[-1].split("?")[0]
if endpoint not in data:
    print("HTTP 404: Not Found", file=sys.stderr)
    sys.exit(1)
if "--jq" in args:
    for item in data[endpoint]:
        print(json.dumps(item))
else:
    print(json.dumps(data[endpoint]))
"""


def user(login: str) -> dict:
    return {"login": login}


ISSUE = {
    "number": 7, "title": "Add a guide", "state": "open", "html_url": "https://github.com/octo/demo/issues/7",
    "user": user("alice"), "created_at": "2026-11-01T09:00:00Z", "body": "### Summary\r\n\r\nWrite it.\r\n",
}
FIRST_COMMENT = {"id": 1, "user": user("bob"), "created_at": "2026-11-02T10:00:00Z", "body": "Sounds good."}
NEW_COMMENT = {"id": 2, "user": user("alice"), "created_at": "2026-11-03T11:00:00Z", "body": "Done."}


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        bin_dir = Path(self.tmp.name) / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "gh"
        fake.write_text(FAKE_GH.format(python=sys.executable), encoding="utf-8")
        fake.chmod(0o755)
        self.data_file = Path(self.tmp.name) / "data.json"
        self.log_file = Path(self.tmp.name) / "log.jsonl"
        self.env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_DATA": str(self.data_file),
            "FAKE_GH_LOG": str(self.log_file),
        }
        self.source = ".keyturn/github/octo/demo/issues/7.md"
        self.work_file = self.root / ".keyturn/i18n/.work/ja" / self.source
        self.target = self.root / ".keyturn/i18n/ja" / self.source
        self.serve_issue([FIRST_COMMENT])

    def tearDown(self):
        self.tmp.cleanup()

    def serve(self, data: dict) -> None:
        self.data_file.write_text(json.dumps(data), encoding="utf-8")

    def serve_issue(self, comments: list[dict]) -> None:
        self.serve({"repos/octo/demo/issues/7": ISSUE, "repos/octo/demo/issues/7/comments": comments})

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root, capture_output=True, text=True, env=self.env,
        )

    def translate(self, marker: str) -> str:
        """Fetch, then translate with every line tagged; return what prepare printed."""
        self.assertEqual(self.run_script("fetch", "7").returncode, 0)
        prepared = self.run_script("prepare", "ja", self.source).stdout
        if self.work_file.exists():
            lines = self.work_file.read_text(encoding="utf-8").splitlines(keepends=True)
            self.work_file.write_text(
                "".join(line if line.startswith("<!--") else f"{marker} {line}" for line in lines),
                encoding="utf-8",
            )
            self.assertEqual(self.run_script("apply", "ja", self.source).returncode, 0)
        return prepared

    def test_an_issue_is_saved_with_its_comments_at_a_predictable_path(self):
        result = self.run_script("fetch", "7")
        self.assertEqual(result.stdout, f"source: {self.source}\n")
        text = (self.root / self.source).read_text(encoding="utf-8")
        self.assertEqual(text, (
            "# Add a guide (#7)\n\n"
            "- Issue: https://github.com/octo/demo/issues/7\n"
            "- Opened by alice on 2026-11-01 09:00 UTC\n"
            "- State: open\n\n"
            "## Description\n\n"
            "### Summary\n\nWrite it.\n\n"
            "## Comment by bob on 2026-11-02 10:00 UTC\n\n"
            "Sounds good.\n\n"
        ))
        self.assertEqual(self.run_script("status", "ja", self.source).stdout, f"missing {self.source}\n")

    def test_fetching_again_without_changes_retranslates_nothing(self):
        self.translate("[v1]")
        self.assertIn("nothing to translate", self.translate("[v2]"))
        self.assertNotIn("[v2]", self.target.read_text(encoding="utf-8"))

    def test_only_a_new_comment_is_translated(self):
        self.translate("[v1]")
        self.serve_issue([FIRST_COMMENT, NEW_COMMENT])
        self.assertIn("sections to translate: 1 (reused: 4)", self.translate("[v2]"))
        translation = self.target.read_text(encoding="utf-8")
        self.assertIn("[v1] Sounds good.", translation)
        self.assertIn("[v2] Done.", translation)

    def test_a_pull_request_includes_reviews_and_review_comments(self):
        pull = {**ISSUE, "html_url": "https://github.com/octo/demo/pull/7", "pull_request": {}}
        self.serve({
            "repos/octo/demo/issues/7": pull,
            "repos/octo/demo/issues/7/comments": [FIRST_COMMENT],
            "repos/octo/demo/pulls/7/reviews": [
                {"id": 10, "user": user("carol"), "submitted_at": "2026-11-02T12:00:00Z",
                 "state": "CHANGES_REQUESTED", "body": "Please fix."},
                {"id": 11, "user": user("carol"), "submitted_at": "2026-11-02T12:00:00Z",
                 "state": "COMMENTED", "body": ""},
                {"id": 12, "user": user("dave"), "state": "PENDING", "body": "draft"},
            ],
            "repos/octo/demo/pulls/7/comments": [
                {"id": 20, "user": user("carol"), "created_at": "2026-11-02T11:59:00Z",
                 "path": "src/app.py", "line": None, "original_line": 3, "body": "Typo."},
                {"id": 21, "user": user("alice"), "created_at": "2026-11-02T13:00:00Z",
                 "path": "src/app.py", "line": 5, "original_line": 3, "in_reply_to_id": 20, "body": "Fixed."},
                {"id": 22, "user": None, "created_at": "2026-11-02T14:00:00Z",
                 "path": "README.md", "line": 1, "original_line": None, "body": "Old account."},
            ],
        })
        self.assertEqual(self.run_script("fetch", "7").stdout, "source: .keyturn/github/octo/demo/pulls/7.md\n")
        text = (self.root / ".keyturn/github/octo/demo/pulls/7.md").read_text(encoding="utf-8")
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        self.assertEqual(headings, [
            "## Description",
            "## Comment by bob on 2026-11-02 10:00 UTC",
            "## Review comment by carol on 2026-11-02 11:59 UTC (`src/app.py` line 3)",
            "## Review by carol on 2026-11-02 12:00 UTC: changes requested",
            "## Reply by alice on 2026-11-02 13:00 UTC (`src/app.py` line 3)",
            "## Review comment by ghost on 2026-11-02 14:00 UTC (`README.md` line 1)",
        ])
        self.assertIn("- Pull request: https://github.com/octo/demo/pull/7", text)
        self.assertNotIn("draft", text)

    def test_nothing_is_written_to_github(self):
        self.run_script("fetch", "7")
        calls = [json.loads(line) for line in self.log_file.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(calls)
        for call in calls:
            self.assertTrue(call[:2] == ["repo", "view"] or call[0] == "api", call)
            self.assertFalse({"-X", "--method", "-f", "-F", "--field", "--raw-field", "--input"} & set(call), call)

    def test_a_missing_issue_is_reported(self):
        result = self.run_script("fetch", "8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 404", result.stderr)

    def test_bad_numbers_and_repositories_are_refused(self):
        self.assertNotEqual(self.run_script("fetch", "0").returncode, 0)
        self.assertNotEqual(self.run_script("fetch", "7", "--repo", "../x").returncode, 0)
        self.assertNotEqual(self.run_script("fetch", "7", "--repo", "octo/..").returncode, 0)

    def test_other_files_under_keyturn_are_still_refused(self):
        (self.root / ".keyturn/notes.md").parent.mkdir(parents=True)
        (self.root / ".keyturn/notes.md").write_text("x\n", encoding="utf-8")
        result = self.run_script("status", "ja", ".keyturn/notes.md")
        self.assertIn("is not translated", result.stderr)


if __name__ == "__main__":
    unittest.main()
