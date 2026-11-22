"""Tests for conditions.py. Run from the repository root: python3 -m unittest discover -s gates"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

import test_gate

CONDITIONS = Path(__file__).with_name("conditions.py")
GUIDE = "# Acceptance guide\n\n## Must check\n"
REPORT = "# Delivery report\n\n## Summary\n"
APPROVALS = "keyturn/client/approvals.md"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def report(title: str, base: str, head: str, *findings: tuple[str, str]) -> str:
    """A review report whose findings are (severity, status) pairs."""
    body = "".join(f"### F-{n}: finding {n}\n\n- Location: `app/src/main.py:1`\n- Severity: {severity}\n"
                   f"- Category: design fit\n- Based on: R-1\n- Status: {status}\n\nWhat is wrong.\n\n"
                   for n, (severity, status) in enumerate(findings, 1))
    return (f"# {title}: t1\n\n- Reviewed by: reviewer\n- Reviewed change: `{base[:7]}`..`{head[:7]}`\n\n"
            f"## Summary\n\nSome findings.\n\n## Findings\n\n<!--\n### F-9: example\n- Severity: high\n- Status: open\n-->\n\n"
            f"{body or 'None.'}\n")


CARD_ANSWERED = "# 判断: 数を表示するか\n\n- 状態: 回答済み\n\n## あなたの回答\n\n- 回答: B のままでよい\n- 日付: 2026-11-21\n"
CARD_WAITING = ("# 判断: 数を表示するか\n\n- 状態: 回答待ち\n\n## あなたの回答\n\n<!-- 2026-11-21 -->\n\n"
                "- 回答: <option, and any comment>\n- 日付: <YYYY-MM-DD>\n")


class ConditionsTest(unittest.TestCase):
    """A task run to its end: the reports, the documents, and the client's acceptance (ADR 0046)."""

    tearDown, write_profile, git, put, commit, assert_fails = (
        test_gate.GateTest.tearDown, test_gate.GateTest.write_profile, test_gate.GateTest.git, test_gate.GateTest.put,
        test_gate.GateTest.commit, test_gate.GateTest.assert_fails)
    state_text, record, roles, step = (
        test_gate.TaskRangeTest.state_text, test_gate.TaskRangeTest.record, test_gate.TaskRangeTest.roles,
        test_gate.TaskRangeTest.step)
    STEPS = test_gate.TaskRangeTest.STEPS + ("merge",)

    def setUp(self):
        test_gate.GateTest.setUp(self)
        self.git("switch", "-q", "-c", "task/t1")
        self.lines: list[str] = []
        self.done: set[str] = set()
        self.record()  # started
        self.put("keyturn/client/requirements.md", "# Requirements\n")
        self.step("spec")
        self.put("keyturn/client/decision-card-1.md", CARD_ANSWERED)
        self.put("keyturn/client/decision-card-2.md", CARD_WAITING)
        self.step("design")
        self.put("keyturn/internal/conventions.md", "# Conventions\n")
        self.step("conventions")
        self.put("app/src/main.py", "print('task')\n")
        self.developer = self.step("implement")
        self.put("app/qa/test_more.txt", "")
        self.step("qa")

    def reports(self, review: tuple = (), security: tuple = (), head: str | None = None) -> None:
        head = head or self.developer
        self.put("keyturn/internal/security-review.md", report("Security review", self.base, head, *security))
        self.step("security-review")
        self.put("keyturn/internal/review.md", report("Review", self.base, head, *review))
        self.step("review")

    def documents(self) -> str:
        self.put("keyturn/client/acceptance-guide.md", GUIDE)
        self.put("keyturn/client/delivery-report.md", REPORT)
        self.put("keyturn/internal/gate/t1.json", "{}\n")
        return self.step("deliver")

    def acceptance(self, documents: str, answer: str = "accepted", words: str = "受け入れます。",
                   guide: str = GUIDE) -> None:
        waiting = (f"| acceptance-guide.md, delivery-report.md | t1 | {documents} | Japanese (original) | {sha(guide)} | "
                   f"{sha(REPORT)} | none | none | 2026-11-22 | waiting | none | |\n")
        header = ("# 承認\n\n## 受け入れ\n\n| 文書 | タスク | 文書のコミット | 言語 | a | b | c | d | 送った日 | 回答 | あなたの言葉 | 回答日 |\n"
                  "|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        self.put(APPROVALS, header + waiting)
        self.step("merge")
        self.put(APPROVALS, header + waiting.replace("| waiting | none | |", f"| {answer} | {words} | 2026-11-23 |"))
        self.step("merge")

    def conditions(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(CONDITIONS), "--task", "t1", "--default-branch", "main"],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def finished(self, review: tuple = (), security: tuple = ()) -> subprocess.CompletedProcess:
        self.reports(review, security)
        self.acceptance(self.documents())
        return self.conditions()

    # Passing

    def test_a_task_with_its_findings_fixed_and_the_acceptance_recorded_passes(self):
        result = self.finished((("medium", "fixed"), ("low", "open")), (("high", "fixed"),))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines()[:3],
                         ["PASS findings [review]", "PASS findings [security-review]", "PASS acceptance"])

    def test_a_medium_review_finding_accepted_on_an_answered_card_passes(self):
        result = self.finished((("medium", "accepted: decision card 1"),))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # Findings

    def test_an_open_high_or_medium_finding_fails(self):
        self.assert_fails(self.finished((("medium", "open"),)), "FAIL findings [review]: keyturn/internal/review.md: F-1: a medium finding is open")

    def test_an_open_security_finding_fails(self):
        self.assert_fails(self.finished((), (("high", "open"),)), "FAIL findings [security-review]")

    def test_a_finding_accepted_on_an_unanswered_card_fails(self):
        self.assert_fails(self.finished((("medium", "accepted: decision card 2"),)), "FAIL findings [review]: keyturn/internal/review.md: F-1: accepted on keyturn/client/decision-card-2.md, which is not answered")

    def test_a_finding_accepted_on_a_missing_card_fails(self):
        self.assert_fails(self.finished((("medium", "accepted: decision card 3"),)), "FAIL findings [review]")

    def test_a_high_finding_or_a_security_finding_is_never_accepted(self):
        result = self.finished((("high", "accepted: decision card 1"),), (("medium", "accepted: decision card 1"),))
        self.assert_fails(result, "FAIL findings [review]: keyturn/internal/review.md: F-1: only a medium finding")
        self.assertIn("FAIL findings [security-review]: keyturn/internal/security-review.md: F-1: a security finding is never accepted", result.stdout)

    def test_a_security_finding_of_the_reviewer_is_never_accepted(self):
        self.reports((("medium", "accepted: decision card 1"),))
        text = (self.root / "keyturn/internal/review.md").read_text().replace("Category: design fit", "Category: security")
        self.put("keyturn/internal/review.md", text)
        self.step("review")
        self.acceptance(self.documents())
        self.assert_fails(self.conditions(), "FAIL findings [review]: keyturn/internal/review.md: F-1: a security finding is never accepted")

    def test_an_unknown_status_or_severity_fails(self):
        result = self.finished((("medium", "wontfix"), ("critical", "fixed")))
        self.assert_fails(result, "FAIL findings [review]: keyturn/internal/review.md: F-1: the status is 'wontfix'")
        self.assertIn("F-2: the severity is 'critical'", result.stdout)

    def test_a_report_that_does_not_reach_the_developer_s_last_commit_fails(self):
        self.reports()
        self.put("app/src/main.py", "print('rework')\n")
        self.step("implement")
        self.acceptance(self.documents())
        self.assert_fails(self.conditions(), "FAIL findings [security-review]: keyturn/internal/security-review.md: reviews up to")

    def test_a_missing_report_fails(self):
        self.put("keyturn/internal/review.md", report("Review", self.base, self.developer))
        self.step("review")
        self.acceptance(self.documents())
        self.assert_fails(self.conditions(), "FAIL findings [security-review]: keyturn/internal/security-review.md: missing")

    def test_a_report_whose_findings_cannot_be_read_fails(self):
        good = report("Review", self.base, self.developer, ("high", "open"))
        for broken in (good.replace("## Findings", "## Issues"), good.replace("### F-1:", "#### F-1:"),
                       good.replace("### F-1: finding 1", "### Finding 1"), good.replace("### F-1: finding 1\n", "")):
            with self.subTest(broken=broken[:0]):
                self.put("keyturn/internal/security-review.md", report("Security review", self.base, self.developer))
                self.put("keyturn/internal/review.md", broken)
                self.step("review")
                self.assert_fails(self.conditions_now(), "FAIL findings [review]: keyturn/internal/review.md: its \"Findings\" section cannot be read")

    def conditions_now(self) -> subprocess.CompletedProcess:
        return self.conditions()

    # Acceptance

    def test_no_acceptance_row_fails(self):
        self.reports()
        self.documents()
        self.assert_fails(self.conditions(), "FAIL acceptance: keyturn/client/approvals.md: no acceptance row for t1")

    def test_an_answer_other_than_accepted_fails(self):
        self.reports()
        self.acceptance(self.documents(), answer="not accepted", words="R-3 を直してください")
        self.assert_fails(self.conditions(), "FAIL acceptance: keyturn/client/approvals.md: the newest acceptance row of t1 says 'not accepted'")

    def test_accepted_without_the_client_s_words_fails(self):
        self.reports()
        self.acceptance(self.documents(), words="none")
        self.assert_fails(self.conditions(), "FAIL acceptance: keyturn/client/approvals.md: the newest acceptance row of t1 says accepted without")

    def test_an_acceptance_of_another_text_fails(self):
        self.reports()
        self.acceptance(self.documents(), guide="# another guide\n")
        self.assert_fails(self.conditions(), "FAIL acceptance: keyturn/client/approvals.md: the SHA-256 of acceptance-guide.md")

    def test_documents_changed_after_the_acceptance_fail(self):
        self.reports()
        documents = self.documents()
        self.acceptance(documents)
        self.put("keyturn/client/delivery-report.md", REPORT + "changed\n")
        self.step("deliver")
        result = self.conditions()
        self.assert_fails(result, "FAIL acceptance: keyturn/client/approvals.md: the newest acceptance row of t1 names")

    def test_a_commit_after_the_documents_that_changes_something_else_fails(self):
        self.reports()
        self.acceptance(self.documents())
        self.put("keyturn/internal/gate/t1.json", "{\"again\": true}\n")
        self.step("deliver")
        self.assert_fails(self.conditions(), "FAIL acceptance: ")

    # Setup

    def test_a_branch_without_a_developer_commit_stops(self):
        self.git("switch", "-q", "-c", "task/t2", self.base)
        result = subprocess.run([sys.executable, str(CONDITIONS), "--task", "t2", "--default-branch", "main"],
                                cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


class CardTest(unittest.TestCase):
    def test_a_card_is_answered_only_with_a_date_and_no_placeholder(self):
        import conditions
        self.assertTrue(conditions.card_answered(CARD_ANSWERED))
        self.assertFalse(conditions.card_answered(CARD_WAITING))
        self.assertFalse(conditions.card_answered("# Decision\n\n## Your answer\n\n- Answer: A\n"))


if __name__ == "__main__":
    unittest.main()
