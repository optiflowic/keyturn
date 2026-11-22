"""Tests for approval.py. Run from the repository root: python3 -m unittest discover -s skills/spec/scripts"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("approval.py")

# Keep the throwaway repositories apart from the developer's Git setup: no variable that points Git at another
# repository, and no global or system configuration (signing, global ignore or attributes files).
ENV = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
ENV["GIT_CONFIG_GLOBAL"] = os.devnull
ENV["GIT_CONFIG_SYSTEM"] = os.devnull

REQUIREMENTS_V1 = """# Requirements: task manager

## Requirements

### R-1: Sign up

Priority: Must

## Changelog

| Version | Date | Change |
|---|---|---|
| 1 | 2026-11-08 | First version |
"""

REQUIREMENTS_V2 = REQUIREMENTS_V1 + "| 2 | 2026-11-20 | R-1: longer passwords |\n"


def sha(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def translation_of(source: str, text: str = "# 要件: タスク管理\n") -> str:
    """A translation as localize writes it: the first line records the source's hash."""
    return f'<!-- localize source="keyturn/client/requirements.md" lang="ja" sha256="{sha(source)}" sections="1" -->\n{text}'


def approvals_with(*rows: str) -> str:
    header = "| Document | Version | Language | Source SHA-256 | Translation SHA-256 | Date sent | Answer | Date answered |\n"
    return "# Approvals\n\n## Approvals\n\n" + header + "|---|---|---|---|---|---|---|---|\n" + "".join(rows)


def row(version: int, source_sha: str, translation_sha: str = "none", answer: str = "waiting") -> str:
    return f"| requirements.md | {version} | Japanese (translation) | {source_sha} | {translation_sha} | 2026-11-08 | {answer} | |\n"


class Repo:
    """A throwaway Git repository with the client documents checked out with LF."""

    def __init__(self, attributes: bool = True):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "core.autocrlf", "false")
        if attributes:
            self.write(".gitattributes", "keyturn/client/*.md text eol=lf\n")
        self.write(".git/info/exclude", ".keyturn/\n")  # as localize.py ignore leaves it

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True, env=ENV)

    def show(self, rel_path: str) -> bytes:
        """The committed bytes of a file."""
        return subprocess.run(
            ["git", "-C", str(self.root), "show", f"HEAD:{rel_path}"], capture_output=True, check=True, env=ENV
        ).stdout

    def write(self, rel_path: str, text: str | bytes) -> None:
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)

    def read(self, rel_path: str) -> bytes:
        return (self.root / rel_path).read_bytes()

    def commit(self, message: str = "commit") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root, capture_output=True, text=True, env=ENV)

    def close(self) -> None:
        self.temp.cleanup()


class RepoTest(unittest.TestCase):
    attributes = True

    def setUp(self):
        self.repo = Repo(attributes=self.attributes)
        self.addCleanup(self.repo.close)

    def assertFails(self, result: subprocess.CompletedProcess, *expected: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for text in expected:
            self.assertIn(text, result.stderr)


class AttributesTest(RepoTest):
    attributes = False

    def test_reports_missing_line(self):
        result = self.repo.run("attributes")
        self.assertFails(result, "keyturn/client/requirements.md: not checked out with LF", "keyturn/client/approvals.md")

    def test_ok_with_line(self):
        self.repo.write(".gitattributes", "keyturn/client/*.md text eol=lf\n")
        result = self.repo.run("attributes")
        self.assertEqual((result.returncode, result.stdout), (0, "ok\n"), result.stderr)

    def test_line_overridden_later_is_reported(self):
        self.repo.write(".gitattributes", "keyturn/client/*.md text eol=lf\nkeyturn/client/*.md -text\n")
        self.assertFails(self.repo.run("attributes"), "not checked out with LF")

    def test_fix_adds_line_after_existing_text_and_renormalizes(self):
        self.repo.write(".gitattributes", "*.png binary")  # no final newline
        self.repo.write("keyturn/client/requirements.md", REQUIREMENTS_V1.replace("\n", "\r\n"))
        self.repo.commit()

        result = self.repo.run("attributes", "--fix")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("and staged .gitattributes and keyturn/client/: commit now", result.stdout)
        attributes = self.repo.read(".gitattributes").decode()
        self.assertTrue(attributes.startswith("*.png binary\n"))
        self.assertTrue(attributes.endswith("keyturn/client/*.md text eol=lf\n"))
        self.repo.git("commit", "-q", "-m", "renormalize")
        self.assertNotIn(b"\r", self.repo.show("keyturn/client/requirements.md"))
        self.assertEqual(self.repo.run("attributes").stdout, "ok\n")

    def test_fix_without_client_documents(self):
        result = self.repo.run("attributes", "--fix")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("staged .gitattributes: commit now", result.stdout)

    def test_fix_never_writes_through_a_link(self):
        self.repo.write("elsewhere", "")
        os.symlink("elsewhere", self.repo.root / ".gitattributes")
        self.assertFails(self.repo.run("attributes", "--fix"), "symbolic link")
        self.assertEqual(self.repo.read("elsewhere"), b"")


class SendTest(RepoTest):
    def setUp(self):
        super().setUp()
        self.repo.write("keyturn/client/requirements.md", REQUIREMENTS_V1)
        self.repo.commit()

    def test_without_translation(self):
        result = self.repo.run("send", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"source-sha256: {sha(REQUIREMENTS_V1)}\ntranslation-sha256: none\n")

    def test_with_translation_keeps_a_copy_next_to_it(self):
        translation = translation_of(REQUIREMENTS_V1)
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", translation)
        result = self.repo.run("send", "1", "--lang", "ja")
        self.assertEqual(result.returncode, 0, result.stderr)
        kept = ".keyturn/i18n/ja/keyturn/client/requirements.v1.approved.md"
        self.assertEqual(
            result.stdout,
            f"source-sha256: {sha(REQUIREMENTS_V1)}\ntranslation-sha256: {sha(translation)}\nkept: {kept}\n",
        )
        self.assertEqual(self.repo.read(kept), translation.encode())
        # Sending the same version again is safe while the translation is the same.
        self.assertEqual(self.repo.run("send", "1", "--lang", "ja").returncode, 0)

    def test_different_translation_for_a_kept_version_is_refused(self):
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", translation_of(REQUIREMENTS_V1))
        self.repo.run("send", "1", "--lang", "ja")
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", translation_of(REQUIREMENTS_V1, "# 別の訳\n"))
        self.assertFails(self.repo.run("send", "1", "--lang", "ja"), "requirements.v1.approved.md: a different translation was already kept")
        kept = self.repo.read(".keyturn/i18n/ja/keyturn/client/requirements.v1.approved.md")
        self.assertEqual(kept, translation_of(REQUIREMENTS_V1).encode())

    def test_missing_or_stale_translation(self):
        self.assertFails(self.repo.run("send", "1", "--lang", "ja"), "missing (translate keyturn/client/requirements.md with localize first)")
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", translation_of("an older version\n"))
        self.assertFails(self.repo.run("send", "1", "--lang", "ja"), "not a fresh translation")
        self.assertFalse((self.repo.root / ".keyturn/i18n/ja/keyturn/client/requirements.v1.approved.md").exists())

    def test_uncommitted_change(self):
        self.repo.write("keyturn/client/requirements.md", REQUIREMENTS_V2)
        self.assertFails(self.repo.run("send", "2"), "differs from the committed version")

    def test_not_committed(self):
        repo = Repo()
        self.addCleanup(repo.close)
        repo.write("README.md", "x\n")
        repo.commit()
        repo.write("keyturn/client/requirements.md", REQUIREMENTS_V1)
        self.assertFails(repo.run("send", "1"), "not committed")

    def test_carriage_return(self):
        repo = Repo(attributes=False)  # without the attribute, Git keeps the CRLF
        self.addCleanup(repo.close)
        repo.write("keyturn/client/requirements.md", REQUIREMENTS_V1.replace("\n", "\r\n"))
        repo.commit()
        self.assertFails(repo.run("send", "1"), "contains a carriage return", "not checked out with LF")

    def test_version_must_match_the_newest_changelog_row(self):
        self.assertFails(self.repo.run("send", "2"), "the newest changelog row is version 1; add the row for version 2")
        self.repo.write("keyturn/client/requirements.md", "# Requirements\n")
        self.repo.commit()
        self.assertFails(self.repo.run("send", "1"), "no changelog row")

    def test_every_problem_is_reported(self):
        self.repo.write("keyturn/client/requirements.md", REQUIREMENTS_V2)
        result = self.repo.run("send", "3", "--lang", "ja")
        self.assertFails(result, "differs from the committed version", "version 2; add the row for version 3", "localize first")

    def test_keyturn_folder_not_ignored(self):
        self.repo.write(".git/info/exclude", "")
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", translation_of(REQUIREMENTS_V1))
        self.assertFails(self.repo.run("send", "1", "--lang", "ja"), ".keyturn/ is not ignored by Git")
        self.assertFalse((self.repo.root / ".keyturn/i18n/ja/keyturn/client/requirements.v1.approved.md").exists())

    def test_tracked_keyturn_folder(self):
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", translation_of(REQUIREMENTS_V1))
        self.repo.git("add", "-f", ".keyturn")
        self.repo.git("commit", "-q", "-m", "tracked")
        self.assertFails(self.repo.run("send", "1", "--lang", "ja"), "Git tracks files under .keyturn/")

    def test_ignores_git_variables_pointing_elsewhere(self):
        other = Repo()
        self.addCleanup(other.close)
        other.write("README.md", "x\n")
        other.commit()
        env = dict(ENV, GIT_DIR=str(other.root / ".git"), GIT_WORK_TREE=str(other.root))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "send", "1"], cwd=self.repo.root, capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(sha(REQUIREMENTS_V1), result.stdout)

    def test_bad_arguments(self):
        self.assertEqual(self.repo.run("send", "0").returncode, 2)
        self.assertEqual(self.repo.run("send", "1", "--lang", "../x").returncode, 2)


class StatusTest(RepoTest):
    def setUp(self):
        super().setUp()
        self.repo.write("keyturn/client/requirements.md", REQUIREMENTS_V1)
        self.repo.commit()
        self.translation = translation_of(REQUIREMENTS_V1)
        self.repo.write(".keyturn/i18n/ja/keyturn/client/requirements.md", self.translation)
        self.repo.run("send", "1", "--lang", "ja")
        self.kept = ".keyturn/i18n/ja/keyturn/client/requirements.v1.approved.md"

    def test_current_with_kept_copy(self):
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, sha(REQUIREMENTS_V1), sha(self.translation), "approved")))
        result = self.repo.run("status", "--lang", "ja")
        self.assertEqual((result.returncode, result.stdout), (0, f"version 1: current, answer: approved\nkept: {self.kept}\n"), result.stderr)

    def test_without_translation(self):
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, sha(REQUIREMENTS_V1))))
        result = self.repo.run("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no translation", result.stdout)

    def test_translated_headings_and_values(self):
        # In a client's language only the headings and words change; the file name, version, and hashes do not.
        text = "| 文書 | 版 | 言語 | 原文 SHA-256 | 翻訳 SHA-256 | 送付日 | 回答 | 回答日 |\n|---|---|---|---|---|---|---|---|\n"
        text += f"| requirements.md | 1 | 日本語（原文） | {sha(REQUIREMENTS_V1)} | なし | 2026-11-08 | 承認 | 2026-11-08 |\n"
        self.repo.write("keyturn/client/approvals.md", text)
        result = self.repo.run("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("version 1: current, answer: 承認", result.stdout)

    def test_newest_row_is_checked(self):
        rows = row(1, sha(REQUIREMENTS_V1), sha(self.translation), "approved") + row(2, sha(REQUIREMENTS_V2), "none")
        self.repo.write("keyturn/client/approvals.md", approvals_with(rows))
        self.assertFails(self.repo.run("status"), "version 2: stale")

    def test_stale_after_change(self):
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, sha(REQUIREMENTS_V1), sha(self.translation))))
        self.repo.write("keyturn/client/requirements.md", REQUIREMENTS_V2)
        self.assertFails(self.repo.run("status", "--lang", "ja"), "version 1: stale")

    def test_changed_or_missing_kept_copy(self):
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, sha(REQUIREMENTS_V1), sha(self.translation))))
        self.repo.write(self.kept, self.translation + "edited\n")
        self.assertFails(self.repo.run("status", "--lang", "ja"), "changed since it was sent")
        os.remove(self.repo.root / self.kept)
        self.assertFails(self.repo.run("status", "--lang", "ja"), "missing; the approved text cannot be shown again")

    def test_translation_needs_lang(self):
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, sha(REQUIREMENTS_V1), sha(self.translation))))
        self.assertFails(self.repo.run("status"), "give its language with --lang")

    def test_no_rows_or_no_file(self):
        self.assertFails(self.repo.run("status"), "keyturn/client/approvals.md: missing")
        self.repo.write("keyturn/client/approvals.md", approvals_with())
        self.assertFails(self.repo.run("status"), "no row for requirements.md")
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, "<SHA-256>")))
        self.assertFails(self.repo.run("status"), "is not a SHA-256")


GUIDE = "# Acceptance guide: task manager\n\n## Must check\n"
REPORT = "# Delivery report: task manager\n\n## Summary\n"


def guide_translation(text: str = GUIDE, name: str = "acceptance-guide.md") -> str:
    return f'<!-- localize source="keyturn/client/{name}" lang="ja" sha256="{sha(text)}" sections="1" -->\n# 受け入れガイド\n'


def acceptance_row(commit: str, guide_sha: str, report_sha: str, translations: tuple[str, str] = ("none", "none"),
                   answer: str = "waiting", task: str = "delivery-1", words: str | None = None) -> str:
    if words is None:
        words = "none" if answer == "waiting" else "問題ありません。受け入れます。"
    return (f"| acceptance-guide.md, delivery-report.md | {task} | {commit} | Japanese (original) | {guide_sha} | "
            f"{report_sha} | {translations[0]} | {translations[1]} | 2026-11-22 | {answer} | {words} | |\n")


class AcceptanceTest(RepoTest):
    def setUp(self):
        super().setUp()
        self.repo.write("keyturn/client/acceptance-guide.md", GUIDE)
        self.repo.write("keyturn/client/delivery-report.md", REPORT)
        self.repo.write("keyturn/internal/gate/delivery-1.json", "{}\n")
        self.repo.commit("docs(delivery): add the acceptance guide and the delivery report of delivery-1")
        self.commit = self.repo.git("rev-parse", "HEAD").stdout.strip()

    def record(self, *rows: str) -> None:
        self.repo.write("keyturn/client/approvals.md", approvals_with(row(1, sha(REQUIREMENTS_V1))) + "\n" + "".join(rows))
        self.repo.commit("docs(approvals): record the acceptance")

    def test_send_prints_the_commit_and_the_hashes(self):
        result = self.repo.run("accept-send", "delivery-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            f"documents-commit: {self.commit}", f"acceptance-guide-sha256: {sha(GUIDE)}",
            f"delivery-report-sha256: {sha(REPORT)}", "acceptance-guide-translation-sha256: none",
            "delivery-report-translation-sha256: none"])

    def test_send_keeps_the_translations(self):
        self.repo.write(".keyturn/i18n/ja/keyturn/client/acceptance-guide.md", guide_translation())
        self.assertFails(self.repo.run("accept-send", "delivery-1", "--lang", "ja"),
                         ".keyturn/i18n/ja/keyturn/client/delivery-report.md: missing")
        self.repo.write(".keyturn/i18n/ja/keyturn/client/delivery-report.md", guide_translation(REPORT, "delivery-report.md"))
        result = self.repo.run("accept-send", "delivery-1", "--lang", "ja")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"acceptance-guide-translation-sha256: {sha(guide_translation())}", result.stdout)
        self.assertEqual(self.repo.read(f".keyturn/i18n/ja/keyturn/client/acceptance-guide.delivery-1.{self.commit[:12]}.accepted.md").decode(),
                         guide_translation())

    def test_a_second_send_after_new_documents_keeps_a_copy_of_its_own(self):
        guide_ja = ".keyturn/i18n/ja/keyturn/client/acceptance-guide.md"
        report_ja = ".keyturn/i18n/ja/keyturn/client/delivery-report.md"
        self.repo.write(guide_ja, guide_translation())
        self.repo.write(report_ja, guide_translation(REPORT, "delivery-report.md"))
        self.assertEqual(self.repo.run("accept-send", "delivery-1", "--lang", "ja").returncode, 0)
        first = self.commit
        self.repo.write("keyturn/client/acceptance-guide.md", GUIDE + "reworked\n")
        self.repo.commit("docs(delivery): add the documents again after the rework")
        second = self.repo.git("rev-parse", "HEAD").stdout.strip()
        self.repo.write(guide_ja, guide_translation(GUIDE + "reworked\n"))
        result = self.repo.run("accept-send", "delivery-1", "--lang", "ja")
        self.assertEqual(result.returncode, 0, result.stderr)
        for commit in (first, second):
            self.assertTrue((self.repo.root / f".keyturn/i18n/ja/keyturn/client/acceptance-guide.delivery-1.{commit[:12]}.accepted.md").is_file())

    def test_send_refuses_a_stale_translation_or_an_uncommitted_document(self):
        self.repo.write(".keyturn/i18n/ja/keyturn/client/acceptance-guide.md", guide_translation("# old\n"))
        self.repo.write(".keyturn/i18n/ja/keyturn/client/delivery-report.md", guide_translation(REPORT, "delivery-report.md"))
        self.assertFails(self.repo.run("accept-send", "delivery-1", "--lang", "ja"), "not a fresh translation")
        self.repo.write("keyturn/client/delivery-report.md", REPORT + "edited\n")
        self.assertFails(self.repo.run("accept-send", "delivery-1"), "differs from the committed version")

    def test_status_reads_the_answer_of_the_newest_row_of_the_task(self):
        self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT)),
                    acceptance_row(self.commit, sha(GUIDE), sha(REPORT), answer="accepted"),
                    acceptance_row("0" * 40, sha(GUIDE), sha(REPORT), task="delivery-2"))
        result = self.repo.run("accept-status", "delivery-1")
        self.assertEqual((result.returncode, result.stdout),
                         (0, "delivery-1: current, answer: accepted\nin the client's words: 問題ありません。受け入れます。\n"),
                         result.stderr)

    def test_status_keeps_an_escaped_pipe_in_the_client_s_words(self):
        self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT), answer="not accepted",
                                   words=r"一覧の「完了 \| 未完了」の切り替えを直してください"))
        result = self.repo.run("accept-status", "delivery-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("answer: not accepted\n", result.stdout)
        self.assertIn(r"完了 \| 未完了", result.stdout)

    def test_status_checks_the_client_s_words_against_the_answer(self):
        self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT), answer="accepted", words="none"))
        self.assertFails(self.repo.run("accept-status", "delivery-1"), "the client's words are missing")
        self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT), answer="waiting", words="受け入れます"))
        self.assertFails(self.repo.run("accept-status", "delivery-1"), "write none until the client answers")

    def test_status_finds_a_changed_document_or_a_later_commit_of_them_stale(self):
        self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT), answer="accepted"))
        self.repo.write("keyturn/client/delivery-report.md", REPORT + "edited\n")
        self.assertFails(self.repo.run("accept-status", "delivery-1"), "keyturn/client/delivery-report.md changed since it was sent")
        self.repo.commit("docs(delivery): change the report")
        self.assertFails(self.repo.run("accept-status", "delivery-1"), "stale (the acceptance guide or the delivery report changed after")

    def test_status_refuses_an_answer_that_is_not_one_of_the_words(self):
        for answer in ("承認", "accepted（受け入れ）", "not accepted: fix R-3"):
            self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT), answer=answer))
            self.assertFails(self.repo.run("accept-status", "delivery-1"), "use waiting, accepted, or not accepted")

    def test_status_without_a_row_or_with_a_translation_and_no_lang(self):
        self.record()
        self.assertFails(self.repo.run("accept-status", "delivery-1"), "no acceptance row for delivery-1")
        self.record(acceptance_row(self.commit, sha(GUIDE), sha(REPORT), (sha("a"), sha("b"))))
        self.assertFails(self.repo.run("accept-status", "delivery-1"), "give its language with --lang")
        self.assertFails(self.repo.run("accept-status", "delivery-1", "--lang", "ja"), f"acceptance-guide.delivery-1.{self.commit[:12]}.accepted.md: missing")

    def test_a_task_name_is_checked(self):
        result = self.repo.run("accept-status", "../x")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a task name", result.stderr)


class OutsideRepositoryTest(unittest.TestCase):
    def test_reports_it(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(SCRIPT), "status"], cwd=folder, capture_output=True, text=True, env=ENV)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not inside a Git repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
