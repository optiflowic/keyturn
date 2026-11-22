"""Tests for task_state.py. Run from the repository root: python3 -m unittest discover -s skills/resume/scripts"""

from __future__ import annotations

import os
import re
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
| merge | not started | | | |

## Commits

- `3d5e7a1`: implement, round 1

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

    def test_commits_lines_name_a_commit_a_step_and_a_round(self):
        bad = STOPPED.replace("- `3d5e7a1`: implement, round 1",
                              "- `3d5e7a1`: implement, round 1\n- `3d5e7a1`: qa, round 1\n- `zz`: testing, round 0\n- 3d5e7a1 implement")
        problems = check(bad)
        self.assertTrue(any("commit `3d5e7a1` is also listed" in p for p in problems), problems)
        self.assertTrue(any('"`zz`" should be a commit hash' in p for p in problems), problems)
        self.assertTrue(any('"testing" is not a step' in p for p in problems), problems)
        self.assertTrue(any("the round should be 1 or more" in p for p in problems), problems)
        self.assertTrue(any('should be "- `<commit>`: <step>, round <n>"' in p for p in problems), problems)

    def test_commits_may_be_none_but_not_empty(self):
        self.assertEqual(check(STOPPED.replace("- `3d5e7a1`: implement, round 1", "None.")), [])
        self.assertIn('Commits: should say "None." when no commit is listed',
                      check(STOPPED.replace("- `3d5e7a1`: implement, round 1", "")))

    def test_reads_fields_steps_and_values_from_the_template(self):
        template = task_state.read_template(TEMPLATE)
        self.assertEqual(list(template.fields), [
            "Task", "Requirements version", "Branch", "Status", "Current step", "Stopped because",
            "Can continue", "Rework", "Updated",
        ])
        self.assertEqual(template.steps, ["spec", "design", "conventions", "implement", "qa", "security-review", "review", "deliver", "merge"])
        self.assertEqual(template.step_statuses, ["not started", "in progress", "done", "skipped"])
        self.assertEqual([p.text for p in template.fields["Status"]], ["running", "stopped", "done", "closed"])
        self.assertEqual(template.sections, ["Summary", "Steps", "Commits", "Open questions", "History"])

    def test_worked_example_passes(self):
        self.assertEqual(check(WORKED_EXAMPLE.read_text(encoding="utf-8")), [])

    def test_template_missing_a_value_the_script_relies_on_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.md"
            path.write_text(TEMPLATE.read_text(encoding="utf-8").replace("<running | stopped | done | closed>", "<running | done | closed>"), encoding="utf-8")
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
        self.assertIn('field "Can continue": is missing', check(STOPPED.replace("- Can continue: after 2026-11-08T15:30Z\n", "")))

    def test_every_missing_field_is_reported_in_template_order(self):
        text = STOPPED.replace("- Rework: 1 of 3\n", "").replace("- Task: delivery-1\n", "")
        missing = [problem for problem in check(text) if problem.endswith(": is missing")]
        self.assertEqual(missing, ['field "Task": is missing', 'field "Rework": is missing'])

    def test_unknown_and_duplicate_fields(self):
        text = STOPPED.replace("- Rework: 1 of 3\n", "- Rework: 1 of 3\n- Rework: 2 of 3\n- Owner: someone\n")
        problems = check(text)
        self.assertIn('line 11: field "Rework" should appear once, but is also on line 10', problems)
        self.assertIn('line 12: "Owner" is not a field of the template', problems)

    def test_missing_section(self):
        self.assertIn('section "History": is missing', check(STOPPED.split("## History")[0]))

    def test_comments_and_placeholders_left(self):
        problems = check(STOPPED.replace("None.", "<!-- nothing -->\n- <decision card <n>: link>"))
        self.assertIn("the template comments (<!-- -->) should be deleted", problems)
        self.assertTrue(any("placeholder <n> should be filled in" in problem for problem in problems))


class UnknownValuesTest(unittest.TestCase):
    def test_unknown_status(self):
        self.assertIn(
            'line 6: field "Status": "paused" should be one of: running | stopped | done | closed',
            check(STOPPED.replace("- Status: stopped", "- Status: paused")),
        )

    def test_unknown_stop_reason(self):
        problems = check(STOPPED.replace("- Stopped because: usage limit", "- Stopped because: tired"))
        self.assertTrue(problems[0].startswith('line 8: field "Stopped because": "tired" should be one of:'))

    def test_current_step_not_in_table(self):
        problems = check(STOPPED.replace("- Current step: implement", "- Current step: coding"))
        self.assertIn('line 7: field "Current step": "coding" should be a step in the steps table', problems)

    def test_can_continue_with_wrong_number(self):
        problems = check(WAITING.replace("decision card 2\n", "decision card two\n", 1))
        self.assertIn('line 9: field "Can continue": "two" should be a whole number', problems)

    def test_unknown_step_status(self):
        problems = check(STOPPED.replace("| qa | not started |", "| qa | waiting |"))
        self.assertIn('line 25: step "qa": status "waiting" should be one of: not started, in progress, done, skipped', problems)

    def test_title_must_name_the_task(self):
        problems = check(STOPPED.replace("# Task state: delivery-1", "# Task state: delivery-2"))
        self.assertEqual(problems, ['title: should name the task "delivery-1" from "Task:", not "delivery-2"'])
        problems = check(STOPPED.replace("# Task state: delivery-1", "# State of delivery-1"))
        self.assertEqual(problems, ['line 1: "# State of delivery-1" should be the title "# Task state: <task>"'])

    def test_task_name_must_match_branch_and_file(self):
        problems = check(STOPPED.replace("- Branch: `task/delivery-1`", "- Branch: `task/delivery-2`"), "other.md")
        self.assertIn('field "Branch": should be `task/delivery-1`, not `task/delivery-2`', problems)
        self.assertIn('field "Task": "delivery-1" should match the file name, other.md', problems)


class MalformedTimesTest(unittest.TestCase):
    def test_updated_without_time_form(self):
        problems = check(STOPPED.replace("- Updated: 2026-11-08T12:48Z", "- Updated: 2026-11-08 12:48"))
        self.assertIn('line 11: field "Updated": "2026-11-08 12:48" should be a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_impossible_time(self):
        problems = check(STOPPED.replace("- Can continue: after 2026-11-08T15:30Z", "- Can continue: after 2026-13-08T15:30Z"))
        self.assertIn('line 9: field "Can continue": "2026-13-08T15:30Z" should be a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_local_time_with_offset(self):
        problems = check(STOPPED.replace("- Updated: 2026-11-08T12:48Z", "- Updated: 2026-11-08T21:48+09:00"))
        self.assertTrue(any("should be a UTC time" in problem for problem in problems))

    def test_history_time(self):
        problems = check(STOPPED.replace("- 2026-11-08T01:05Z: started", "- 8 Nov 2026: started"))
        self.assertIn('line 41: "8 Nov 2026" should be a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_history_out_of_order(self):
        problems = check(STOPPED.replace("- 2026-11-08T06:02Z: resumed", "- 2026-11-08T03:22Z: resumed"))
        self.assertNotIn("should not be earlier than the line before it", " ".join(problems))
        problems = check(STOPPED.replace("- 2026-11-08T12:48Z: stopped: usage", "- 2026-11-08T05:48Z: stopped: usage"))
        self.assertIn("line 44: 2026-11-08T05:48Z should not be earlier than the line before it (newest last)", problems)

    def test_open_question_time(self):
        problems = check(WAITING.replace("Waiting since 2026-11-08T03:20Z", "Waiting since yesterday"))
        self.assertIn('line 37: "yesterday" should be a UTC time in the form YYYY-MM-DDTHH:MMZ', problems)

    def test_blocks_names_steps_of_the_template(self):
        self.assertEqual(check(WAITING), [])
        for blocks in ("implement, qa", "implement and qa", "R-3", "R-3 and implement", "qa and every later step."):
            with self.subTest(blocks=blocks):
                self.assertEqual(check(WAITING.replace("Blocks: design and every later step", f"Blocks: {blocks}")), [])

    def test_blocks_with_an_unknown_step_is_reported(self):
        problems = check(WAITING.replace("Blocks: design and every later step", "Blocks: the design"))
        self.assertIn('line 37: "Blocks:" names "the design", which should be a step (spec, design, conventions, implement, '
                      'qa, security-review, review, deliver, merge), "every later step" right after a step, or a requirement (R-n)', problems)

    def test_empty_blocks_is_reported(self):
        for blocks in (".", ",", ", ."):
            with self.subTest(blocks=blocks):
                problems = check(WAITING.replace("Blocks: design and every later step", f"Blocks: {blocks}"))
                self.assertIn('line 37: "Blocks:" should name at least one step or requirement', problems)
        problems = check(WAITING.replace("Blocks: design and every later step", "Blocks: implement, , qa"))
        self.assertIn('line 37: "Blocks: implement, , qa" has an empty item between its commas or "and"', problems)

    def test_blocks_every_later_step_needs_a_step_before_it(self):
        problems = check(WAITING.replace("Blocks: design and every later step", "Blocks: every later step"))
        self.assertIn('"Blocks:" names "every later step"', " ".join(problems))


class BrokenStepsTableTest(unittest.TestCase):
    def test_missing_step(self):
        self.assertIn('Steps: step "qa" is missing', check(STOPPED.replace("| qa | not started | | | |\n", "")))

    def test_steps_out_of_order(self):
        text = STOPPED.replace("| qa | not started | | | |\n| security-review | not started | | | |\n",
                               "| security-review | not started | | | |\n| qa | not started | | | |\n")
        self.assertIn("Steps: the steps should be in this order: spec, design, conventions, implement, qa, security-review, review, deliver, merge", check(text))

    def test_unknown_and_duplicate_step(self):
        problems = check(STOPPED.replace("| review | not started | | | |", "| review | not started | | | |\n| review | not started | | | |\n| lint | not started | | | |"))
        self.assertIn('Steps: "lint" is not a step of the template', problems)
        self.assertIn('Steps: step "review" should appear once', problems)

    def test_wrong_number_of_columns(self):
        self.assertIn("line 25: should have 5 columns, not 3", check(STOPPED.replace("| qa | not started | | | |", "| qa | not started | |")))

    def test_wrong_heading(self):
        problems = check(STOPPED.replace("| Step | Status | Output | Commit | Notes |", "| Step | State | Output | Commit | Notes |"))
        self.assertEqual(problems, ["line 19: the table heading should be | Step | Status | Output | Commit | Notes |, not | Step | State | Output | Commit | Notes |"])

    def test_no_table(self):
        text = STOPPED.split("| Step |")[0] + "## Open questions" + STOPPED.split("## Open questions")[1]
        self.assertIn("Steps: should have the steps table", check(text))

    def test_done_step_needs_a_commit_hash(self):
        problems = check(STOPPED.replace("| `b7e4410` |", "| |").replace("`1f3d2b8`", "1f3d2b8"))
        self.assertIn('step "conventions": is done, so it should have a commit (a step is done only when its outputs are committed)', " ".join(problems))
        self.assertIn('step "spec": commit "1f3d2b8" should be a commit hash in backticks', " ".join(problems))

    def test_skipped_step_needs_a_reason(self):
        problems = check(STOPPED.replace("| conventions | done | `conventions.md` | `b7e4410` | |", "| conventions | skipped | | | |"))
        self.assertIn('line 23: step "conventions": is skipped, so its notes should say why', problems)


class ConsistencyTest(unittest.TestCase):
    """Where to continue must follow from the file without a guess."""

    def test_current_step_must_be_the_first_unfinished_step(self):
        problems = check(STOPPED.replace("- Current step: implement", "- Current step: qa"))
        self.assertIn('field "Current step": should be "implement", the first step that is not done or skipped, not "qa"', problems)

    def test_stopped_needs_a_reason(self):
        problems = check(STOPPED.replace("- Stopped because: usage limit", "- Stopped because: none"))
        self.assertIn('field "Stopped because": should give the reason when Status is stopped, not "none"', problems)

    def test_usage_limit_needs_the_reset_time(self):
        problems = check(STOPPED.replace("- Can continue: after 2026-11-08T15:30Z", "- Can continue: now"))
        self.assertIn('field "Can continue": should be "after YYYY-MM-DDTHH:MMZ" (when the limit resets) for a usage limit, not "now"', problems)

    def test_waited_for_card_must_be_an_open_question(self):
        problems = check(WAITING.replace("decision card 2\n", "decision card 3\n", 1))
        self.assertIn('Open questions: should list "decision card 3", which the task waits for', problems)

    def test_waiting_for_agreement_to_the_design_summary(self):
        text = (WAITING.replace("when the client answers: decision card 2", "when the client agrees: design summary")
                .replace("- [decision card 2](../../client/decision-card-2.md): which sign-in to use. ",
                         "- [design summary](../../client/design-summary.md): "))
        self.assertEqual(check(text), [])
        problems = check(text.replace("- [design summary](../../client/design-summary.md): ", "- [summary](../../client/design-summary.md): "))
        self.assertIn('Open questions: should list "design summary", which the task waits for', problems)

    def test_waiting_for_the_maintainer_says_what_they_decide(self):
        text = (WAITING.replace("- Stopped because: waiting for the client", "- Stopped because: waiting for the maintainer")
                .replace("- Can continue: when the client answers: decision card 2", "- Can continue: when the maintainer decides: whether to go on without R-3"))
        self.assertEqual(check(text), [])
        problems = check(text.replace("when the maintainer decides: whether to go on without R-3", "now"))
        self.assertIn('field "Can continue": should say what the maintainer must decide ("when the maintainer decides: ..."), not "now"', problems)

    def test_a_step_sent_back_may_keep_its_earlier_commit(self):
        text = STOPPED.replace("| qa | not started | | | |", "| qa | not started | [test report](../test-report.md) | `d2a7f13` | round 2 next |")
        self.assertEqual(check(text), [])

    def test_done_with_unfinished_step(self):
        text = WORKED_EXAMPLE.read_text(encoding="utf-8").replace("| deliver | done |", "| deliver | in progress |")
        self.assertIn('step "deliver": should be done or skipped when Status is done', check(text))

    def test_rework_above_limit(self):
        self.assertIn('field "Rework": "4 of 3" should not count more than the limit', check(STOPPED.replace("Rework: 1 of 3", "Rework: 4 of 3")))


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
        self.assertIn("delivery-1 (task/delivery-1):\n  error: task/delivery-1: should not have diverged: task/delivery-1, origin/task/delivery-1", result.stdout)
        self.assertIn("delivery-9 (task/delivery-9):\n  error: task/delivery-9:keyturn/internal/state/delivery-9.md: is missing", result.stdout)

    def test_no_task_branches(self):
        result = self.repo.run("list")
        self.assertEqual((result.returncode, result.stdout), (0, "no tasks to resume\n"))

    def test_one_task_is_judged_on_its_own(self):
        self.repo.task_branch(self.repo.root, "delivery-1", STOPPED)
        self.repo.task_branch(self.repo.root, "delivery-2", STOPPED.replace("- Status: stopped", "- Status: paused"))
        self.repo.task_branch(self.repo.root, "delivery-3", WORKED_EXAMPLE.read_text(encoding="utf-8"))

        full = self.repo.run("list")
        self.assertEqual(full.returncode, 1)
        self.assertIn("delivery-1 (task/delivery-1):\n  status: stopped\n", full.stdout)
        self.assertIn('delivery-2 (task/delivery-2):\n  error: task/delivery-2:keyturn/internal/state/delivery-2.md: line 6: field "Status"', full.stdout)
        result =self.repo.run("list", "--task", "delivery-1")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(result.stdout.startswith("delivery-1 (task/delivery-1):\n"))
        self.assertNotIn("delivery-2", result.stdout)
        done = self.repo.run("list", "--task", "delivery-3")
        self.assertIn("  status: done\n", done.stdout)
        missing = self.repo.run("list", "--task", "delivery-7")
        self.assertEqual((missing.returncode, missing.stdout), (1, "delivery-7 (task/delivery-7):\n  error: task/delivery-7: has no local or remote branch\n"))


def closed(text: str) -> str:
    """A stopped task closed after the client did not accept it (ADR 0047)."""
    text = (text.replace("- Status: stopped", "- Status: closed").replace("- Current step: implement", "- Current step: none"))
    text = re.sub(r"- Stopped because: .*", "- Stopped because: none", text)
    text = re.sub(r"- Can continue: .*", "- Can continue: not applicable", text)
    return text.rstrip("\n") + "\n- 2026-11-09T10:00Z: closed: the client chose to stop the task, in merge\n"


class ClosedTest(unittest.TestCase):
    def test_a_closed_task_is_valid_with_unfinished_steps(self):
        self.assertEqual(check(closed(STOPPED)), [])

    def test_a_closed_task_says_nothing_more_to_do(self):
        problems = check(closed(STOPPED).replace("- Current step: none", "- Current step: implement"))
        self.assertIn('field "Current step": should be "none" when Status is closed, not "implement"', " ".join(problems) + "".join(problems))
        problems = check(closed(STOPPED).rstrip("\n") + "\n- 2026-11-10T10:00Z: resumed: in implement, from commit `abc1234`\n")
        self.assertIn('History: the last line should be "closed" when Status is closed', problems)


class BeforeMergeStepTest(unittest.TestCase):
    def test_a_done_task_from_before_the_merge_step_stays_valid(self):
        done = WORKED_EXAMPLE.read_text(encoding="utf-8")
        old = re.sub(r"\n\| merge \|[^\n]*", "", done)
        self.assertNotEqual(old, done)
        self.assertEqual(check(old), [])

    def test_a_task_that_is_not_done_still_needs_the_merge_step(self):
        old = re.sub(r"\n\| merge \|[^\n]*", "", STOPPED)
        self.assertIn('Steps: step "merge" is missing', check(old))


class UnmergedTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)

    def test_no_task_branches(self):
        result = self.repo.run("unmerged", "main")
        self.assertEqual((result.returncode, result.stdout), (0, "no unmerged task branches\n"))

    def test_lists_unmerged_branches_with_their_status_local_and_remote(self):
        done = WORKED_EXAMPLE.read_text(encoding="utf-8")
        self.repo.task_branch(self.repo.root, "delivery-1", done)
        self.repo.task_branch(self.repo.origin, "delivery-2", STOPPED)
        self.repo.git(self.repo.root, "switch", "-q", "-c", "task/delivery-3", "main")
        self.repo.commit(self.repo.root, "notes.md", "no state file\n")
        self.repo.git(self.repo.root, "switch", "-q", "main")
        self.repo.git(self.repo.root, "fetch", "-q")

        result = self.repo.run("unmerged", "main")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, (
            "task/delivery-1: done\n"
            "origin/task/delivery-2: stopped\n"
            "task/delivery-3: no state file\n"
        ))

    def test_merged_and_squash_merged_branches_are_left_out(self):
        done = WORKED_EXAMPLE.read_text(encoding="utf-8")
        self.repo.task_branch(self.repo.root, "delivery-1", done)
        self.repo.git(self.repo.root, "merge", "-q", "--no-edit", "task/delivery-1")
        self.repo.task_branch(self.repo.root, "delivery-2", done)
        self.repo.git(self.repo.root, "merge", "-q", "--squash", "task/delivery-2")
        self.repo.git(self.repo.root, "commit", "-q", "-m", "squash")

        result = self.repo.run("unmerged", "main")
        self.assertEqual((result.returncode, result.stdout), (0, "no unmerged task branches\n"))

    def test_a_closed_task_is_left_out_of_the_list_and_of_unmerged(self):
        self.repo.task_branch(self.repo.root, "delivery-1", closed(STOPPED))
        result = self.repo.run("unmerged", "main")
        self.assertEqual((result.returncode, result.stdout), (0, "no unmerged task branches\n"), result.stderr)
        self.assertNotIn("delivery-1", self.repo.run("list").stdout)

    def test_work_after_closing_a_task_is_unmerged(self):
        self.repo.task_branch(self.repo.root, "delivery-1", closed(STOPPED))
        self.repo.git(self.repo.root, "switch", "-q", "task/delivery-1")
        self.repo.commit(self.repo.root, "app/main.py", "print('later')\n")
        self.repo.git(self.repo.root, "switch", "-q", "main")
        result = self.repo.run("unmerged", "main")
        self.assertEqual((result.returncode, result.stdout), (1, "task/delivery-1: closed\n"))

    def test_work_after_a_squash_merge_is_unmerged(self):
        done = WORKED_EXAMPLE.read_text(encoding="utf-8")
        self.repo.task_branch(self.repo.root, "delivery-1", done)
        self.repo.git(self.repo.root, "merge", "-q", "--squash", "task/delivery-1")
        self.repo.git(self.repo.root, "commit", "-q", "-m", "squash")
        self.repo.git(self.repo.root, "switch", "-q", "task/delivery-1")
        self.repo.commit(self.repo.root, "keyturn/internal/state/delivery-1.md", done.replace("- Status: done", "- Status: running"))
        self.repo.git(self.repo.root, "switch", "-q", "main")

        result = self.repo.run("unmerged", "main")
        self.assertEqual((result.returncode, result.stdout), (1, "task/delivery-1: running\n"))

    def test_other_work_after_a_squash_merge_is_unmerged(self):
        done = WORKED_EXAMPLE.read_text(encoding="utf-8")
        self.repo.task_branch(self.repo.root, "delivery-1", done)
        self.repo.git(self.repo.root, "merge", "-q", "--squash", "task/delivery-1")
        self.repo.git(self.repo.root, "commit", "-q", "-m", "squash")
        self.repo.git(self.repo.root, "switch", "-q", "task/delivery-1")
        self.repo.commit(self.repo.root, "app/main.py", "print('later')\n")
        self.repo.git(self.repo.root, "switch", "-q", "main")

        result = self.repo.run("unmerged", "main")
        self.assertEqual((result.returncode, result.stdout), (1, "task/delivery-1: done\n"))

    def test_default_that_is_not_a_commit(self):
        result = self.repo.run("unmerged", "origin/nothing")
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: origin/nothing: should name a commit", result.stdout)


class CheckCommandTest(unittest.TestCase):
    def run_check(self, text: str) -> subprocess.CompletedProcess:
        """Run check from the file's folder, so the problems name the same path, delivery-1.md, every run."""
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "delivery-1.md").write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, str(SCRIPT), "check", "delivery-1.md", "--now", "2026-11-08T16:00Z"],
                                  cwd=folder, capture_output=True, text=True, env=ENV)

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
        self.assertEqual(first.stdout, second.stdout)
        self.assertIn('error: delivery-1.md: line 6: field "Status": "paused" should be one of: running | stopped | done | closed\n', first.stdout)
        self.assertIn('error: delivery-1.md: Steps: step "qa" is missing\n', first.stdout)


if __name__ == "__main__":
    unittest.main()
