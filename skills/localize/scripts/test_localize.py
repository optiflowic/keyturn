"""Tests for localize.py. Run with: python3 -m unittest discover skills/localize/scripts"""

from __future__ import annotations

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

    def test_a_translation_with_a_damaged_marker_is_stale(self):
        self.first_translation()
        text = self.target.read_text(encoding="utf-8")
        without_last_section = text.rsplit("<!-- localize-section", 1)[0]
        self.target.write_text(without_last_section, encoding="utf-8")
        self.assertEqual(self.run_script("status", "ja", "docs/GUIDE.md").stdout, "stale docs/GUIDE.md\n")
        self.assertIn("sections to translate: 1 (reused: 2)", self.run_script("prepare", "ja", "docs/GUIDE.md").stdout)

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


if __name__ == "__main__":
    unittest.main()
