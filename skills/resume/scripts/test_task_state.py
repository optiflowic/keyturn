"""Tests for task_state.py. Run from the repository root: python3 -m unittest discover -s skills/resume/scripts"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("task_state.py")
REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "templates" / "internal" / "state.md"
WORKED_EXAMPLE = REPO / "evals" / "requests" / "task-manager" / "example" / "keyturn" / "internal" / "state" / "delivery-1.md"

sys.path.insert(0, str(SCRIPT.parent))
import task_state  # noqa: E402

# Keep the throwaway repositories apart from the developer's Git setup.
ENV = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
ENV["GIT_CONFIG_GLOBAL"] = os.devnull
ENV["GIT_CONFIG_SYSTEM"] = os.devnull

# The worked example's task, as it was when it stopped for the usage limit in implement.
STOPPED = """# Task state: delivery-1

- Task: delivery-1
- Requirements version: 1
- Branch: `task/delivery-1`
- Status: stopped
- Current step: implement
- Stopped because: usage limit
- Can continue: after 2026-11-08T15:30Z
- Rework: 1 of 3
- Updated: 2026-11-08T12:48Z

## Summary

Stopped in the middle of the programming because the plan's 5-hour usage window reached 80%. It can go on after 15:30 UTC.

## Steps

| Step | Status | Output | Commit | Notes |
|---|---|---|---|---|
| spec | done | [requirements](../../client/requirements.md) | `1f3d2b8` | approved, version 1 |
| design | done | [design](../design.md) | `a51f0c2` | decision cards 1 and 2 answered |
| conventions | done | `conventions.md` | `b7e4410` | |
| implement | in progress | | | second round |
| qa | not started | | | |
| security-review | not started | | | |
| review | not started | | | |
| deliver | not started | | | |

## Open questions

None.

## History

- 2026-11-08T01:05Z: started
- 2026-11-08T03:20Z: stopped: waiting for the client, in design (decision cards 1 and 2)
- 2026-11-08T06:02Z: resumed: in design, from commit `7c9e011`
- 2026-11-08T12:48Z: stopped: usage limit, in implement (5-hour window at 80%, resets at 2026-11-08T15:30Z)
"""

WAITING = (
    STOPPED.replace("- Current step: implement", "- Current step: design")
    .replace("- Stopped because: usage limit", "- Stopped because: waiting for the client")
    .replace("- Can continue: after 2026-11-08T15:30Z", "- Can continue: when the client answers: decision card 2")
    .replace("| design | done | [design](../design.md) | `a51f0c2` | decision cards 1 and 2 answered |",
             "| design | in progress | | | waiting for decision card 2 |")
    .replace("| conventions | done | `conventions.md` | `b7e4410` | |", "| conventions | not started | | | |")
    .replace("| implement | in progress | | | second round |", "| implement | not started | | | |")
    .replace("None.", "- [decision card 2](../../client/decision-card-2.md): which sign-in to use. "
                      "Waiting since 2026-11-08T03:20Z. Blocks: design and every later step")
)


def check(text: str, file_name: str | None = "delivery-1.md") -> list[str]:
    return task_state.check_state(text, task_state.read_template(TEMPLATE), file_name)[1]


class TemplateTest(unittest.TestCase):
    """The script reads the real template, so a change to it that the script cannot follow fails here."""

    def test_reads_fields_steps_and_values_from_the_template(self):
        template = task_state.read_template(TEMPLATE)
        self.assertEqual(list(template.fields), [
            "Task", "Requirements version", "Branch", "Status", "Current step", "Stopped because",
            "Can continue", "Rework", "Updated",
        ])
        self.assertEqual(template.steps, ["spec", "design", "conventions", "implement", "qa", "security-review", "review", "deliver"])
        self.assertEqual(template.step_statuses, ["not started", "in progress", "done", "skipped"])
        self.assertEqual([p.text for p in template.fields["Status"]], ["running", "stopped", "done"])
        self.assertEqual(template.sections, ["Summary", "Steps", "Open questions", "History"])

    def test_worked_example_passes(self):
        self.assertEqual(check(WORKED_EXAMPLE.read_text(encoding="utf-8")), [])

    def test_template_missing_a_value_the_script_relies_on_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.md"
            path.write_text(TEMPLATE.read_text(encoding="utf-8").replace("<running | stopped | done>", "<running | done>"), encoding="utf-8")
            with self.assertRaises(task_state.Problems) as raised:
                task_state.read_template(path)
        self.assertIn('field "Status" no longer allows "stopped"', raised.exception.problems[0])

    def test_unknown_placeholder_in_template_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.md"
            path.write_text(TEMPLATE.read_text(encoding="utf-8").replace("Rework: <n> of <limit>", "Rework: <count>"), encoding="utf-8")
            with self.assertRaises(task_state.Problems) as raised:
                task_state.read_template(path)
        self.assertIn("unknown placeholder <count>", raised.exception.problems[0])


class ValidFileTest(unittest.TestCase):
    def test_stopped_file_passes(self):
        self.assertEqual(check(STOPPED), [])

    def test_waiting_file_passes(self):
        self.assertEqual(check(WAITING), [])

    def test_skipped_step_with_reason_passes(self):
        text = STOPPED.replace("| conventions | done | `conventions.md` | `b7e4410` | |", "| conventions | skipped | | | the project has conventions |")
        self.assertEqual(check(text), [])

    def test_same_file_gives_the_same_problems(self):
        broken = STOPPED.replace("- Status: stopped\n", "").replace("| qa |", "| test |")
        self.assertEqual(check(broken), check(broken))


class MissingFieldsTest(unittest.TestCase):
    def test_missing_field(self):
        self.assertIn('field "Can continue": missing', check(STOPPED.replace("- Can continue: after 2026-11-08T15:30Z\n", "")))

    def test_every_missing_field_is_reported_in_template_order(self):
        text = STOPPED.replace("- Rework: 1 of 3\n", "").replace("- Task: delivery-1\n", "")
        missing = [problem for problem in check(text) if problem.endswith(": missing")]
        self.assertEqual(missing, ['field "Task": missing', 'field "Rework": missing'])

    def test_unknown_and_duplicate_fields(self):
        text = STOPPED.replace("- Rework: 1 of 3\n", "- Rework: 1 of 3\n- Rework: 2 of 3\n- Owner: someone\n")
        problems = check(text)
        self.assertIn('line 11: field "Rework" appears more than once (first on line 10)', problems)
        self.assertIn('line 12: unknown field "Owner"', problems)

    def test_missing_section(self):
        self.assertIn('section "History": missing', check(STOPPED.split("## History")[0]))

    def test_comments_and_placeholders_left(self):
        problems = check(STOPPED.replace("None.", "<!-- nothing -->\n- <decision card <n>: link>"))
        self.assertIn("the file still has template comments (<!-- -->); delete them", problems)
        self.assertTrue(any("placeholder <n> is not filled in" in problem for problem in problems))


class UnknownValuesTest(unittest.TestCase):
    def test_unknown_status(self):
        self.assertIn(
            'line 6: field "Status": "paused" is not one of the allowed values: running | stopped | done',
            check(STOPPED.replace("- Status: stopped", "- Status: paused")),
        )

    def test_unknown_stop_reason(self):
        problems = check(STOPPED.replace("- Stopped because: usage limit", "- Stopped because: tired"))
        self.assertTrue(problems[0].startswith('line 8: field "Stopped because": "tired" is not one of the allowed values'))

    def test_current_step_not_in_table(self):
        problems = check(STOPPED.replace("- Current step: implement", "- Current step: coding"))
        self.assertIn('line 7: field "Current step": "coding" is not a step in the steps table', problems)

    def test_can_continue_with_wrong_number(self):
        problems = check(WAITING.replace("decision card 2\n", "decision card two\n", 1))
        self.assertIn('line 9: field "Can continue": "two" is not a whole number', problems)

    def test_unknown_step_status(self):
        problems = check(STOPPED.replace("| qa | not started |", "| qa | waiting |"))
        self.assertIn('line 25: step "qa": status "waiting" is not one of the allowed values: not started, in progress, done, skipped', problems)

    def test_task_name_must_match_branch_and_file(self):
        problems = check(STOPPED.replace("- Branch: `task/delivery-1`", "- Branch: `task/delivery-2`"), "other.md")
        self.assertIn('field "Branch": is not `task/delivery-1`', problems)
        self.assertIn('field "Task": "delivery-1" does not match the file name other.md', problems)


class MalformedTimesTest(unittest.TestCase):
    def test_updated_without_time_form(self):
        problems = check(STOPPED.replace("- Updated: 2026-11-08T12:48Z", "- Updated: 2026-11-08 12:48"))
        self.assertIn('line 11: field "Updated": "2026-11-08 12:48" is not a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_impossible_time(self):
        problems = check(STOPPED.replace("- Can continue: after 2026-11-08T15:30Z", "- Can continue: after 2026-13-08T15:30Z"))
        self.assertIn('line 9: field "Can continue": "2026-13-08T15:30Z" is not a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_local_time_with_offset(self):
        problems = check(STOPPED.replace("- Updated: 2026-11-08T12:48Z", "- Updated: 2026-11-08T21:48+09:00"))
        self.assertTrue(any("is not a UTC time" in problem for problem in problems))

    def test_history_time(self):
        problems = check(STOPPED.replace("- 2026-11-08T01:05Z: started", "- 8 Nov 2026: started"))
        self.assertIn('line 36: "8 Nov 2026" is not a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_history_out_of_order(self):
        problems = check(STOPPED.replace("- 2026-11-08T06:02Z: resumed", "- 2026-11-08T03:22Z: resumed"))
        self.assertNotIn("the history is not in time order", " ".join(problems))
        problems = check(STOPPED.replace("- 2026-11-08T12:48Z: stopped: usage", "- 2026-11-08T05:48Z: stopped: usage"))
        self.assertIn("line 39: the history is not in time order (newest last)", problems)

    def test_open_question_time(self):
        problems = check(WAITING.replace("Waiting since 2026-11-08T03:20Z", "Waiting since yesterday"))
        self.assertIn('line 32: "yesterday" is not a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)


class BrokenStepsTableTest(unittest.TestCase):
    def test_missing_step(self):
        self.assertIn('Steps: step "qa" is missing', check(STOPPED.replace("| qa | not started | | | |\n", "")))

    def test_steps_out_of_order(self):
        text = STOPPED.replace("| qa | not started | | | |\n| security-review | not started | | | |\n",
                               "| security-review | not started | | | |\n| qa | not started | | | |\n")
        self.assertIn("Steps: the steps are not in order; the order is spec, design, conventions, implement, qa, security-review, review, deliver", check(text))

    def test_unknown_and_duplicate_step(self):
        problems = check(STOPPED.replace("| review | not started | | | |", "| review | not started | | | |\n| review | not started | | | |\n| lint | not started | | | |"))
        self.assertIn('Steps: unknown step "lint"', problems)
        self.assertIn('Steps: step "review" appears more than once', problems)

    def test_wrong_number_of_columns(self):
        self.assertIn("line 25: has 3 columns instead of 5", check(STOPPED.replace("| qa | not started | | | |", "| qa | not started | |")))

    def test_wrong_heading(self):
        problems = check(STOPPED.replace("| Step | Status | Output | Commit | Notes |", "| Step | State | Output | Commit | Notes |"))
        self.assertEqual(problems, ["line 19: the table heading is not | Step | Status | Output | Commit | Notes |"])

    def test_no_table(self):
        text = STOPPED.split("| Step |")[0] + "## Open questions" + STOPPED.split("## Open questions")[1]
        self.assertIn("Steps: no table", check(text))

    def test_done_step_needs_a_commit_hash(self):
        problems = check(STOPPED.replace("| `b7e4410` |", "| |").replace("`1f3d2b8`", "1f3d2b8"))
        self.assertIn('step "conventions": is done but has no commit (a step is done only when its outputs are committed)', " ".join(problems))
        self.assertIn('step "spec": the commit "1f3d2b8" is not a commit hash in backticks', " ".join(problems))

    def test_skipped_step_needs_a_reason(self):
        problems = check(STOPPED.replace("| conventions | done | `conventions.md` | `b7e4410` | |", "| conventions | skipped | | | |"))
        self.assertIn('line 23: step "conventions": is skipped but its notes do not say why', problems)


class ConsistencyTest(unittest.TestCase):
    """Where to continue must follow from the file without a guess."""

    def test_current_step_must_be_the_first_unfinished_step(self):
        problems = check(STOPPED.replace("- Current step: implement", "- Current step: qa"))
        self.assertIn('field "Current step": is "qa", but the first step that is not done or skipped is "implement"', problems)

    def test_stopped_needs_a_reason(self):
        problems = check(STOPPED.replace("- Stopped because: usage limit", "- Stopped because: none"))
        self.assertIn('field "Stopped because": is none, but Status is stopped', problems)

    def test_usage_limit_needs_the_reset_time(self):
        problems = check(STOPPED.replace("- Can continue: after 2026-11-08T15:30Z", "- Can continue: now"))
        self.assertIn('field "Can continue": a usage limit stop says when the limit resets (after YYYY-MM-DDTHH:MMZ)', problems)

    def test_waited_for_card_must_be_an_open_question(self):
        problems = check(WAITING.replace("decision card 2\n", "decision card 3\n", 1))
        self.assertIn('Open questions: "decision card 3" is not listed, but the task waits for it', problems)

    def test_done_with_unfinished_step(self):
        text = WORKED_EXAMPLE.read_text(encoding="utf-8").replace("| deliver | done |", "| deliver | in progress |")
        self.assertIn('step "deliver": is not done or skipped, but Status is done', check(text))

    def test_rework_above_limit(self):
        self.assertIn('field "Rework": the count is above the limit', check(STOPPED.replace("Rework: 1 of 3", "Rework: 4 of 3")))


class Repo:
    """A throwaway Git repository with a clone as its remote, origin."""

    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.origin = Path(self.temp.name) / "origin"
        self.root = Path(self.temp.name) / "work"
        self.origin.mkdir()
        self.git(self.origin, "init", "-q", "-b", "main")
        self.commit(self.origin, "README.md", "project\n")
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.root)], check=True, capture_output=True, env=ENV)
        for folder in (self.origin, self.root):
            self.git(folder, "config", "user.email", "test@example.com")
            self.git(folder, "config", "user.name", "Test")

    def git(self, folder: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True, text=True, env=ENV).stdout

    def commit(self, folder: Path, rel_path: str, text: str) -> None:
        path = folder / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.git(folder, "add", "-A")
        self.git(folder, "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-q", "-m", "commit")

    def task_branch(self, folder: Path, task: str, text: str) -> None:
        self.git(folder, "switch", "-q", "-c", f"task/{task}", "main")
        self.commit(folder, f"keyturn/internal/state/{task}.md", text.replace("delivery-1", task))
        self.git(folder, "switch", "-q", "main")

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root, capture_output=True, text=True, env=ENV)

    def close(self) -> None:
        self.temp.cleanup()


class ListTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)

    def test_lists_local_and_remote_tasks_that_are_not_done(self):
        self.repo.task_branch(self.repo.root, "delivery-1", STOPPED)
        self.repo.task_branch(self.repo.origin, "delivery-2", WAITING)
        self.repo.task_branch(self.repo.origin, "delivery-3", WORKED_EXAMPLE.read_text(encoding="utf-8"))
        self.repo.git(self.repo.root, "fetch", "-q")

        result = self.repo.run("list", "--now", "2026-11-08T14:00Z")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, (
            "delivery-1 (task/delivery-1):\n"
            "  status: stopped\n"
            "  current step: implement (in progress)\n"
            "  stopped because: usage limit\n"
            "  can continue: after 2026-11-08T15:30Z: not yet (now 2026-11-08T14:00Z)\n"
            "delivery-2 (origin/task/delivery-2):\n"
            "  status: stopped\n"
            "  current step: design (in progress)\n"
            "  stopped because: waiting for the client\n"
            "  can continue: when the client answers: decision card 2: only once the client's answer is recorded\n"
        ))

    def test_local_branch_behind_remote_uses_the_remote(self):
        self.repo.task_branch(self.repo.origin, "delivery-1", STOPPED)
        self.repo.git(self.repo.root, "fetch", "-q")
        self.repo.git(self.repo.root, "branch", "-q", "task/delivery-1", "origin/task/delivery-1")
        self.repo.git(self.repo.origin, "switch", "-q", "task/delivery-1")
        self.repo.commit(self.repo.origin, "notes.md", "more\n")
        self.repo.git(self.repo.root, "fetch", "-q")

        result = self.repo.run("list", "--now", "2026-11-08T16:00Z")
        self.assertIn("delivery-1 (origin/task/delivery-1):", result.stdout)
        self.assertIn("can continue: after 2026-11-08T15:30Z: the time has passed", result.stdout)
        self.assertIn("note: task/delivery-1 is behind origin/task/delivery-1; fast-forward it before resuming", result.stdout)

    def test_diverged_branches_and_missing_state_file_are_problems(self):
        self.repo.task_branch(self.repo.origin, "delivery-1", STOPPED)
        self.repo.git(self.repo.root, "fetch", "-q")
        self.repo.git(self.repo.root, "switch", "-q", "-c", "task/delivery-1", "origin/task/delivery-1")
        self.repo.commit(self.repo.root, "local.md", "local\n")
        self.repo.git(self.repo.origin, "switch", "-q", "task/delivery-1")
        self.repo.commit(self.repo.origin, "remote.md", "remote\n")
        self.repo.git(self.repo.root, "fetch", "-q")
        self.repo.git(self.repo.root, "switch", "-q", "-c", "task/delivery-9", "main")

        result = self.repo.run("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("task/delivery-1, origin/task/delivery-1 have diverged", result.stdout)
        self.assertIn("keyturn/internal/state/delivery-9.md: missing on task/delivery-9", result.stdout)

    def test_no_task_branches(self):
        result = self.repo.run("list")
        self.assertEqual((result.returncode, result.stdout), (0, "no tasks to resume\n"))


class CheckCommandTest(unittest.TestCase):
    def run_check(self, text: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "delivery-1.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, str(SCRIPT), "check", str(path), "--now", "2026-11-08T16:00Z"],
                                  capture_output=True, text=True, env=ENV)

    def test_ok_says_where_the_task_stands(self):
        result = self.run_check(STOPPED)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (
            "ok\ntask: delivery-1\nstatus: stopped\ncurrent step: implement (in progress)\n"
            "stopped because: usage limit\ncan continue: after 2026-11-08T15:30Z: the time has passed\n"
        ))

    def test_problems_exit_1_and_are_the_same_every_run(self):
        broken = STOPPED.replace("- Status: stopped", "- Status: paused").replace("| qa | not started | | | |\n", "")
        first, second = self.run_check(broken), self.run_check(broken)
        self.assertEqual(first.returncode, 1)
        self.assertEqual(first.stdout, "")
        self.assertEqual(first.stderr, second.stderr)
        self.assertIn('error: line 6: field "Status": "paused"', first.stderr)


if __name__ == "__main__":
    unittest.main()
