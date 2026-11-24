"""Tests for gate.py. Run from the repository root: python3 -m unittest discover -s gates"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).with_name("gate.py")

# A stand-in profile that needs only Python: "build" fails while a file named BROKEN exists,
# and the tests are the files named test_*.txt.
PROFILE = {
    "name": "fake",
    "tools": [{"command": "python3", "install": "install Python 3"}],
    "setup": [],
    "checks": [{"name": "build", "run": [sys.executable, "-c",
                                         "import pathlib, sys; sys.exit(1 if pathlib.Path('BROKEN').exists() else 0)"]}],
    "count_tests": [sys.executable, "-c", "import pathlib; print(len(list(pathlib.Path('.').rglob('test_*.txt'))))"],
    "versions": [sys.executable, "-c", "print('fake 1.0'); print('helper 2.3')"],
    "pinned": None,
    "install_scripts": None,
    "source_files": ["*.py"],
    "suppressions": [r"#\s*noqa"],
    "protected": [".lintrc"],
}

DESIGN = """# Design

## Areas the work may change

| Path | What changes | Serves |
|---|---|---|
| `app/src/**` | the code | R-1 |

## QA's tests

| Path | What is tested there |
|---|---|
| `app/qa/**` | the app, through its interface |

## Requirements coverage
"""

ADR = "# 0001. Allow one noqa\n\n- Status: accepted\n- Date: 2026-11-21\n- Allows: # noqa: F401\n"


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.profiles = Path(self.tmp.name) / "profiles"
        (self.profiles / "fake").mkdir(parents=True)
        self.write_profile(PROFILE)
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.put("keyturn/config.json", json.dumps(
            {"client_language": "en", "english_only": True, "parts": [{"path": "app", "profile": "fake"}]}))
        self.put("keyturn/internal/design.md", DESIGN)
        self.put("app/src/main.py", "print('hello')\n")
        self.put("app/src/test_one.txt", "")
        self.put("app/qa/test_qa.txt", "")
        self.base = self.commit("base")

    def tearDown(self):
        self.tmp.cleanup()

    def write_profile(self, profile: dict) -> None:
        (self.profiles / profile["name"] / "profile.json").write_text(json.dumps(profile), encoding="utf-8")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def put(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def gate(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(GATE), "--base", self.base, "--profiles", str(self.profiles), *extra],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def assert_fails(self, result: subprocess.CompletedProcess, line_start: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(any(line.startswith(line_start) for line in result.stdout.splitlines()), result.stdout)

    # Passing

    def test_a_change_inside_the_areas_passes(self):
        self.put("app/src/main.py", "print('hello, world')\n")
        self.put("app/src/test_two.txt", "")
        self.commit("change")
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS protected-paths: ok", result.stdout)
        self.assertIn("PASS test-count [app]: 2 tests at the base, 3 at the head", result.stdout)
        self.assertIn("PASS build [app]: ok", result.stdout)
        self.assertTrue(result.stdout.splitlines()[-1].startswith("gate: passed"))

    def test_the_log_records_every_check(self):
        self.commit("nothing")
        log = Path(self.tmp.name) / "gate.json"
        self.assertEqual(self.gate("--log", str(log)).returncode, 0)
        record = json.loads(log.read_text(encoding="utf-8"))
        self.assertTrue(record["passed"])
        self.assertEqual([c["check"] for c in record["checks"]], ["protected-paths", "suppressions", "test-count", "build"])
        self.assertEqual(record["versions"], [{"part": "app", "profile": "fake", "versions": ["fake 1.0", "helper 2.3"]}])

    def test_the_tool_versions_are_printed(self):
        self.commit("nothing")
        result = self.gate()
        self.assertIn("VERSIONS [app]: fake 1.0; helper 2.3", result.stdout)
        self.assertTrue(result.stdout.splitlines()[-1].startswith("gate: passed"))

    def test_versions_that_cannot_be_read_are_recorded_and_do_not_fail_the_gate(self):
        self.write_profile(dict(PROFILE, versions=[sys.executable, "-c", "import sys; print('no such tool'); sys.exit(3)"]))
        self.commit("nothing")
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VERSIONS [app]: not read (exit 3): no such tool", result.stdout)

    # Protected paths

    def test_a_change_to_qa_s_folder_fails(self):
        self.put("app/qa/test_qa.txt", "changed")
        self.commit("change QA's test")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/qa/test_qa.txt (matches app/qa/**)")

    def test_the_developer_s_handoff_notes_are_not_protected(self):
        self.put("keyturn/internal/handoff.md", "# Handoff\n")
        self.commit("handoff")
        self.assertEqual(self.gate().returncode, 0)

    def test_other_roles_documents_and_git_attributes_are_protected(self):
        self.put("keyturn/client/requirements.md", "changed")
        self.put("app/.gitignore", "BROKEN\n")
        self.commit("change the requirements and an ignore file")
        result = self.gate()
        self.assert_fails(result, "FAIL protected-paths:")
        self.assertIn("keyturn/client/requirements.md (matches keyturn/client/**)", result.stdout)
        self.assertIn("app/.gitignore (matches **/.gitignore)", result.stdout)

    def test_a_linter_config_the_profile_names_is_protected(self):
        self.put("app/.lintrc", "relaxed")
        self.commit("add a linter config")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/.lintrc (matches **/.lintrc)")

    def test_moving_a_protected_file_out_fails(self):
        self.git("mv", "app/qa/test_qa.txt", "app/src/test_qa.txt")
        self.commit("move QA's test")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/qa/test_qa.txt (matches app/qa/**)")

    def test_the_configuration_and_ci_jobs_are_protected(self):
        self.put(".github/workflows/ci.yml", "on: push\n")
        self.commit("add CI")
        self.assert_fails(self.gate(), "FAIL protected-paths: .github/workflows/ci.yml (matches .github/workflows/**)")

    def test_narrowing_qa_s_tests_in_the_design_does_not_unprotect_them(self):
        self.put("keyturn/internal/design.md", DESIGN.replace("`app/qa/**`", "`app/other/**`"))
        self.put("app/qa/test_qa.txt", "changed")
        self.commit("narrow the design, then change QA's test")
        result = self.gate()
        self.assert_fails(result, "FAIL protected-paths:")
        self.assertIn("app/qa/test_qa.txt (matches app/qa/**)", result.stdout)
        self.assertIn("keyturn/internal/design.md (matches keyturn/internal/**)", result.stdout)

    def test_a_path_with_a_newline_is_still_protected(self):
        self.put("app/qa/a\nb.txt", "")
        self.commit("odd name")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/qa/a")

    def test_a_qa_folder_written_without_a_wildcard_protects_everything_under_it(self):
        self.put("keyturn/internal/design.md", DESIGN.replace("`app/qa/**`", "`app/qa/`"))
        self.base = self.commit("design names the folder only")
        self.put("app/qa/test_qa.txt", "changed")
        self.commit("change QA's test")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/qa/test_qa.txt (matches app/qa/**)")

    def test_a_template_placeholder_in_qa_s_tests_stops_the_gate(self):
        self.put("keyturn/internal/design.md", DESIGN.replace("`app/qa/**`", "`<folder>/**`"))
        self.base = self.commit("unfilled design")
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("template placeholder", result.stderr)

    def test_a_change_to_a_protected_path_that_a_later_commit_undoes_still_fails(self):
        self.put("app/qa/test_qa.txt", "changed")
        self.commit("change QA's test")
        self.put("app/qa/test_qa.txt", "")
        self.commit("change it back")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/qa/test_qa.txt (matches app/qa/**)")

    def test_a_part_folder_that_links_outside_the_repository_fails(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "test_a.txt").write_text("", encoding="utf-8")
        self.git("rm", "-q", "-r", "app")
        (self.root / "app").symlink_to(outside)
        self.commit("replace the part with a link")
        result = self.gate()
        self.assert_fails(result, "FAIL test-count [app]:")
        self.assertIn("leads outside the repository", result.stdout)

    def test_git_s_variables_of_the_caller_do_not_reach_the_checks(self):
        self.git("rm", "-q", "app/src/test_one.txt")
        self.commit("delete a test")
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=other, env=self.env, check=True)
        env = dict(self.env, GIT_DIR=str(other / ".git"), GIT_WORK_TREE=str(other))
        result = subprocess.run([sys.executable, str(GATE), "--base", self.base, "--profiles", str(self.profiles)],
                                cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL test-count [app]: 2 tests at the base, 1 at the head", result.stdout)

    # Suppressions

    def test_an_added_line_that_starts_with_two_pluses_does_not_hide_the_next_lines(self):
        self.put("app/src/main.py", "print('hello')\n++ x\nimport os  # noqa\n")
        self.commit("suppress after a ++ line")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: app/src/main.py:3:")

    def test_a_suppression_in_a_file_with_a_space_in_its_name_is_found(self):
        self.put("app/src/two words.py", "import os  # noqa\n")
        self.commit("suppress in a file with a space")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: app/src/two words.py:1:")


    def test_a_new_suppression_fails(self):
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa: F401\n")
        self.commit("suppress")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: app/src/main.py:2: import os  # noqa: F401 (names no accepted ADR)")

    def test_a_suppression_that_names_an_adr_accepted_at_the_base_passes(self):
        self.put("keyturn/internal/adr/0001-allow-one-noqa.md", ADR)
        self.base = self.commit("ADR")
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa: F401  ADR-0001\n")
        self.commit("suppress")
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_an_accepted_adr_that_does_not_allow_the_suppression_approves_nothing(self):
        self.put("keyturn/internal/adr/0001-use-postgres.md", "# 0001. Use Postgres\n\n- Status: accepted\n")
        self.base = self.commit("ADR")
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa  ADR-0001\n")
        self.commit("suppress")
        result = self.gate()
        self.assert_fails(result, "FAIL suppressions [app]: app/src/main.py:2:")
        self.assertIn('has no "- Allows:" line that this line contains', result.stdout)

    def test_an_adr_added_in_the_range_approves_nothing(self):
        self.put("keyturn/internal/adr/0001-allow-one-noqa.md", ADR)
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa: F401  ADR-0001\n")
        self.commit("ADR and suppression together")
        result = self.gate()
        self.assert_fails(result, "FAIL suppressions [app]: app/src/main.py:2:")
        self.assertIn("names ADR-0001, not accepted at the base", result.stdout)
        self.assertIn("keyturn/internal/adr/0001-allow-one-noqa.md", result.stdout)  # and the ADR is a protected path

    def test_an_adr_that_allows_a_suppression_in_a_folder_passes_it_there_without_its_number(self):
        self.put("keyturn/internal/adr/0001-generated-code.md",
                 "# 0001. Generated code\n\n- Status: accepted\n- Allows in app/src/gen/**: # noqa: generated\n")
        self.base = self.commit("ADR")
        self.put("app/src/gen/models.py", "import os  # noqa: generated\n")
        self.commit("generated")
        self.assertEqual(self.gate().returncode, 0)

    def test_the_backticks_around_what_an_adr_allows_are_not_part_of_it(self):
        self.put("keyturn/internal/adr/0001-allow-one-noqa.md", ADR.replace("- Allows: # noqa: F401", "- Allows: `# noqa: F401`"))
        self.base = self.commit("ADR")
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa: F401  ADR-0001\n")
        self.commit("suppress")
        self.assertEqual(self.gate().returncode, 0)

    def test_an_adr_that_allows_a_suppression_in_a_folder_approves_nothing_outside_it(self):
        self.put("keyturn/internal/adr/0001-generated-code.md",
                 "# 0001. Generated code\n\n- Status: accepted\n- Allows in `app/src/gen/**`: # noqa: generated\n")
        self.base = self.commit("ADR")
        self.put("app/src/main.py", "import os  # noqa: generated\n")
        self.put("app/src/gen/models.py", "import os  # noqa\n")
        self.commit("outside the folder, and another suppression inside it")
        result = self.gate()
        self.assert_fails(result, "FAIL suppressions [app]:")
        self.assertIn("app/src/main.py:1:", result.stdout)
        self.assertIn("app/src/gen/models.py:1:", result.stdout)

    def test_a_folder_allowance_in_an_adr_that_is_not_accepted_approves_nothing(self):
        self.put("keyturn/internal/adr/0001-generated-code.md",
                 "# 0001. Generated code\n\n- Status: proposed\n- Allows in app/src/gen/**: # noqa: generated\n")
        self.base = self.commit("ADR")
        self.put("app/src/gen/models.py", "import os  # noqa: generated\n")
        self.commit("generated")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: app/src/gen/models.py:1:")

    def test_marking_a_file_as_binary_does_not_hide_a_suppression(self):
        self.put(".gitattributes", "*.py -diff\n")
        self.base = self.commit("attributes")
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa\n")
        self.commit("suppress")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: app/src/main.py:2:")

    def test_a_suppression_outside_every_part_is_found(self):
        self.put("tools/gen.py", "import os  # noqa\n")
        self.commit("suppress outside the parts")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: tools/gen.py:1:")

    def test_a_carriage_return_does_not_make_a_line_look_like_a_patch_header(self):
        self.put("app/src/main.py", 'print("hello")\npayload = """\rdiff --git a/x b/x\n"""\nimport os  # noqa\n')
        self.commit("hide a suppression after a carriage return")
        self.assert_fails(self.gate(), "FAIL suppressions [app]: app/src/main.py:4:")

    def test_a_suppression_in_a_file_the_profile_does_not_cover_is_not_counted(self):
        self.put("app/src/notes.md", "# noqa is just text here\n")
        self.commit("notes")
        self.assertEqual(self.gate().returncode, 0)

    # Test count

    def test_a_deleted_test_fails(self):
        self.git("rm", "-q", "app/src/test_one.txt")
        self.commit("delete a test")
        self.assert_fails(self.gate(), "FAIL test-count [app]: 2 tests at the base, 1 at the head")

    def test_a_part_that_is_new_starts_from_zero_tests(self):
        self.put("keyturn/config.json", json.dumps({"client_language": "en", "english_only": True, "parts": [
            {"path": "app", "profile": "fake"}, {"path": "tool", "profile": "fake"}]}))
        self.base = self.commit("add a part")
        self.put("tool/test_a.txt", "")
        self.commit("first test of the new part")
        result = self.gate()
        self.assertIn("PASS test-count [tool]: 0 tests at the base, 1 at the head", result.stdout)

    # Profile checks

    def test_a_failing_profile_check_fails(self):
        self.put("app/BROKEN", "")
        self.commit("break the build")
        self.assert_fails(self.gate(), "FAIL build [app]: exit 1")

    # Failures only in QA's folders (ADR 0065)

    def with_lint(self) -> None:
        """A profile whose "lint" fails while a .txt file in the part says BAD."""
        lint = {"name": "lint", "run": [sys.executable, "-c",
                                        "import pathlib, sys; sys.exit(1 if any('BAD' in p.read_text() "
                                        "for p in pathlib.Path('.').rglob('*.txt')) else 0)"]}
        self.write_profile(dict(PROFILE, checks=PROFILE["checks"] + [lint]))

    def test_a_check_that_fails_only_in_qa_s_folders_is_marked(self):
        self.with_lint()
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer")
        self.put("app/qa/test_qa.txt", "BAD")
        qa = self.commit("QA's test")
        log = Path(self.tmp.name) / "gate.json"
        result = self.gate("--others", f"qa:{qa}", "--log", str(log))
        self.assert_fails(result, "FAIL lint [app] (QA's folders only): exit 1")
        self.assertIn("PASS build [app]: ok", result.stdout)
        self.assertTrue(result.stdout.splitlines()[-1].startswith("gate: failed"))
        record = json.loads(log.read_text(encoding="utf-8"))
        self.assertEqual([(c["check"], c["qa_only"]) for c in record["checks"] if not c["passed"]], [("lint", True)])
        self.assertFalse(any(c["qa_only"] for c in record["checks"] if c["passed"]))

    def test_a_failure_in_the_developer_s_files_is_never_marked(self):
        self.with_lint()
        self.put("app/src/test_one.txt", "BAD")
        self.commit("developer")
        result = self.gate()
        self.assert_fails(result, "FAIL lint [app]: exit 1")
        self.assertNotIn("QA's folders only", result.stdout)

    def test_a_failure_in_both_the_developer_s_files_and_qa_s_is_not_marked(self):
        self.with_lint()
        self.put("app/src/test_one.txt", "BAD")
        self.commit("developer")
        self.put("app/qa/test_qa.txt", "BAD")
        qa = self.commit("QA's test")
        result = self.gate("--others", f"qa:{qa}")
        self.assert_fails(result, "FAIL lint [app]: exit 1")
        self.assertNotIn("QA's folders only", result.stdout)

    def test_only_the_checks_that_fail_because_of_qa_s_folders_are_marked(self):
        self.with_lint()
        self.put("app/BROKEN", "")
        self.commit("developer breaks the build")
        self.put("app/qa/test_qa.txt", "BAD")
        qa = self.commit("QA's test")
        result = self.gate("--others", f"qa:{qa}")
        self.assert_fails(result, "FAIL build [app]: exit 1")
        self.assertIn("FAIL lint [app] (QA's folders only): exit 1", result.stdout)

    def test_a_developer_change_to_qa_s_folders_fails_protected_paths_unmarked(self):
        self.with_lint()
        self.put("app/qa/test_qa.txt", "BAD")
        self.commit("developer writes in QA's folder")
        result = self.gate()
        self.assert_fails(result, "FAIL protected-paths: app/qa/test_qa.txt")
        self.assertIn("FAIL lint [app] (QA's folders only): exit 1", result.stdout)

    def test_a_drop_in_the_test_count_in_qa_s_folders_is_not_marked(self):
        self.git("rm", "-q", "app/qa/test_qa.txt")
        self.put("keyturn/internal/test-report.md", "# Test report\n")
        qa = self.commit("QA removes a test")
        self.assert_fails(self.gate("--others", f"qa:{qa}"), "FAIL test-count [app]: 2 tests at the base, 1 at the head")

    def test_a_check_that_did_not_run_after_a_failed_setup_is_not_marked(self):
        self.write_profile(dict(PROFILE, setup=[[sys.executable, "-c", "import sys; sys.exit(3)"]]))
        self.put("app/qa/test_qa.txt", "x")
        qa = self.commit("QA's test")
        result = self.gate("--others", f"qa:{qa}")
        self.assert_fails(result, "FAIL build [app]: not run: setup failed (exit 3)")
        self.assertNotIn("QA's folders only", result.stdout)

    def test_a_failure_in_a_part_without_qa_s_files_is_not_marked(self):
        # The tool part's check fails while app/qa has a file, but tool holds none of QA's files: it is not run again.
        self.write_profile(dict(PROFILE, checks=[{"name": "build", "run": [
            sys.executable, "-c", "import pathlib, sys; sys.exit(1 if pathlib.Path('../app/qa/test_qa.txt').exists() "
                                  "and pathlib.Path('NEEDS_NO_QA').exists() else 0)"]}]))
        self.put("keyturn/config.json", json.dumps({"client_language": "en", "english_only": True, "parts": [
            {"path": "app", "profile": "fake"}, {"path": "tool", "profile": "fake"}]}))
        self.base = self.commit("add a part")
        self.put("tool/NEEDS_NO_QA", "")
        self.commit("developer")
        result = self.gate()
        self.assert_fails(result, "FAIL build [tool]: exit 1")
        self.assertNotIn("QA's folders only", result.stdout)

    def test_a_suppression_in_the_developer_s_files_too_is_not_marked(self):
        self.put("app/src/check.py", "import os  # noqa\n")
        self.commit("developer")
        self.put("app/qa/check.py", "import os  # noqa\n")
        qa = self.commit("QA's test with a suppression")
        result = self.gate("--others", f"qa:{qa}")
        self.assert_fails(result, "FAIL suppressions [app]: ")
        self.assertNotIn("QA's folders only", result.stdout)

    def test_qa_s_files_with_special_names_are_removed_for_the_rerun(self):
        self.with_lint()
        self.put("app/qa/[x]*.txt", "BAD")
        qa = self.commit("QA's test")
        self.assert_fails(self.gate("--others", f"qa:{qa}"), "FAIL lint [app] (QA's folders only): exit 1")

    # Other roles' commits (ADR 0029)

    def qa_commit(self) -> str:
        self.put("app/qa/test_qa2.txt", "")
        self.put("keyturn/internal/test-report.md", "# Test report\n")
        return self.commit("QA's tests")

    def test_another_role_s_commits_named_with_others_are_left_out(self):
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer")
        qa = self.qa_commit()
        self.put("keyturn/internal/state/task.md", "# State\n")
        state = self.commit("deliver's state")
        result = self.gate("--others", f"qa:{qa}", "--others", f"deliver:{state}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_fails(self.gate(), "FAIL protected-paths:")  # without the list, every commit is the developer's

    def start_before_the_documents(self) -> dict[str, str]:
        """Move the base to a commit without the task's documents, and commit them as spec, design, and conventions would."""
        self.git("rm", "-q", "keyturn/internal/design.md")
        self.base = self.commit("the default branch, before the task")
        self.put("keyturn/client/requirements.md", "# Requirements\n")
        spec = self.commit("spec")
        self.put("keyturn/internal/design.md", DESIGN)
        self.put("keyturn/internal/adr/0001-allow-one-noqa.md", ADR)
        design = self.commit("design")
        self.put("keyturn/internal/conventions.md", "# Conventions\n")
        self.put(".lintrc", "strict\n")
        conventions = self.commit("conventions")
        return {"spec": spec, "design": design, "conventions": conventions}

    def others(self, roles: dict[str, str]) -> list[str]:
        return [argument for role, commit in roles.items() for argument in ("--others", f"{role}:{commit}")]

    def test_the_document_roles_commits_before_the_developer_s_are_left_out(self):
        roles = self.start_before_the_documents()
        self.put("app/src/main.py", "import os  # noqa: F401 ADR-0001\n")
        self.commit("developer")
        result = self.gate(*self.others(roles))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)  # the ADR is read at the design's commit

    def test_a_conventions_commit_may_change_a_gitignore_and_the_developer_s_may_not(self):
        roles = self.start_before_the_documents()
        self.put("app/.gitignore", "node_modules/\n")
        named = [*self.others(roles), "--others", f"conventions:{self.commit('conventions: what Git ignores')}"]
        result = self.gate(*named)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.put("app/.gitignore", "node_modules/\nsrc/\n")
        self.commit("developer")
        self.assert_fails(self.gate(*named), "FAIL protected-paths: app/.gitignore (matches **/.gitignore)")

    def pin(self) -> None:
        """Give the stand-in profile a lock file, app/tools.lock, whose lines are "<tool> <version>"."""
        self.write_profile(dict(PROFILE, pinned={"files": ["tools.json", "tools.lock"], "lock": "tools.lock",
                                                 "read": [sys.executable, "-c", "import sys; print(sys.stdin.read())"]}))

    def test_a_developer_change_to_a_pinned_tool_s_version_fails(self):
        self.pin()
        self.put("app/tools.lock", "lint 2.0\ntest 1.0\n")
        self.base = self.commit("tools")
        self.put("app/tools.lock", "lint 1.0\ntest 1.0\nother 3.0\n")
        self.commit("developer: an older linter")
        result = self.gate()
        self.assert_fails(result, "FAIL pinned-tools [app]: lint: 2.0 at the base, 1.0 at the head")
        self.assertIn("other: not installed at the base, 3.0 at the head", result.stdout)

    def test_a_pinned_tool_s_version_set_by_conventions_is_kept_by_the_developer(self):
        self.pin()
        roles = self.start_before_the_documents()
        self.put("app/tools.json", "{}\n")
        self.put("app/tools.lock", "lint 2.0\n")
        named = [*self.others(roles), "--others", f"conventions:{self.commit('conventions: the tools')}"]
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer: code only")
        result = self.gate(*named)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS pinned-tools [app]: ok", result.stdout)
        self.put("app/tools.lock", "lint 2.1\n")
        self.commit("developer: a newer linter")
        self.assert_fails(self.gate(*named), "FAIL pinned-tools [app]: lint: 2.0 at the conventions commit")

    # Prints the lines of app/unmarked.txt at the head, as the profile's "installed" command prints each installed package
    # whose script the lock file does not mark.
    UNMARKED = [sys.executable, "-c", "import pathlib; p = pathlib.Path('unmarked.txt'); print(p.read_text() if p.exists() else '')"]

    def scripts(self, read: list[str] | None = None, installed: list[str] | None = None, **profile) -> None:
        """Give the stand-in profile a lock file, app/deps.lock, whose lines are the "<package>@<version>" of each package
        with an install script."""
        self.write_profile(dict(PROFILE, **profile, install_scripts={
            "lock": "deps.lock", "read": read or [sys.executable, "-c", "import sys; print(sys.stdin.read())"],
            "installed": installed or self.UNMARKED}))

    def allow_scripts(self, value: str, status: str = "accepted") -> None:
        self.put("keyturn/internal/adr/0002-native-module.md",
                 f"# 0002. Build a native module\n\n- Status: {status}\n- Allows install scripts: {value}\n\n## Context\n")

    def test_a_new_package_with_an_install_script_fails(self):
        self.scripts()
        self.put("app/deps.lock", "old@1.0.0\n")
        self.base = self.commit("a package that was there")
        self.put("app/deps.lock", "old@1.0.0\nnative@2.0.0\n")
        self.commit("developer: a package with a script")
        result = self.gate()
        self.assert_fails(result, "FAIL install-scripts [app]: app/deps.lock: native@2.0.0 runs scripts on install")
        self.assertNotIn("old@1.0.0", result.stdout)

    def test_a_package_with_a_script_already_at_the_base_passes(self):
        self.scripts()
        self.put("app/deps.lock", "old@1.0.0\n")
        self.base = self.commit("a package that was there")
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer: code only")
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS install-scripts [app]: ok", result.stdout)

    def test_a_new_version_of_a_package_with_a_script_fails(self):
        self.scripts()
        self.put("app/deps.lock", "native@1.0.0\n")
        self.base = self.commit("a package that was there")
        self.put("app/deps.lock", "native@1.1.0\n")
        self.commit("developer: a newer version")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: app/deps.lock: native@1.1.0 runs scripts on install")

    def test_a_lock_file_missing_at_the_base_reads_as_no_packages(self):
        self.scripts()
        self.put("app/deps.lock", "native@1.0.0\n")
        self.commit("developer: the first lock file")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: app/deps.lock: native@1.0.0 runs scripts on install")

    def test_a_package_an_adr_accepted_at_the_base_allows_passes(self):
        self.scripts()
        self.allow_scripts("`@scope/native@2.0.0`")
        self.base = self.commit("design: allow the script")
        self.put("app/deps.lock", "@scope/native@2.0.0\n")
        self.commit("developer: the package")
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS install-scripts [app]: @scope/native@2.0.0: allowed by ADR-0002", result.stdout)

    def test_an_adr_for_another_version_allows_nothing(self):
        self.scripts()
        self.allow_scripts("native@2.0.0")
        self.base = self.commit("design: allow the script")
        self.put("app/deps.lock", "native@2.0.1\n")
        self.commit("developer: another version")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: app/deps.lock: native@2.0.1 runs scripts on install")

    def test_an_adr_that_is_not_accepted_allows_nothing(self):
        self.scripts()
        self.allow_scripts("native@2.0.0", status="proposed")
        self.base = self.commit("design: a proposed allowance")
        self.put("app/deps.lock", "native@2.0.0\n")
        self.commit("developer: the package")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: app/deps.lock: native@2.0.0 runs scripts on install")

    def test_an_adr_the_developer_adds_allows_no_install_script(self):
        self.scripts()
        self.allow_scripts("native@2.0.0")
        self.put("app/deps.lock", "native@2.0.0\n")
        self.commit("developer: the package and its own allowance")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: app/deps.lock: native@2.0.0 runs scripts on install")

    def test_an_adr_of_the_design_commit_named_with_others_allows_the_script(self):
        self.scripts()
        roles = self.start_before_the_documents()
        self.allow_scripts("native@2.0.0")
        named = [*self.others(roles), "--others", f"design:{self.commit('design: allow the script')}"]
        self.put("app/deps.lock", "native@2.0.0\n")
        self.commit("developer: the package")
        result = self.gate(*named)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS install-scripts [app]: native@2.0.0: allowed by ADR-0002", result.stdout)

    def test_an_allowance_a_conventions_commit_adds_allows_nothing(self):
        read = [sys.executable, "-c", "import sys; print(sys.stdin.read())"]
        self.write_profile(dict(PROFILE, pinned={"files": ["deps.lock"], "lock": "deps.lock", "read": read},
                                install_scripts={"lock": "deps.lock", "read": read, "installed": self.UNMARKED}))
        roles = self.start_before_the_documents()
        self.allow_scripts("native@2.0.0")
        self.put("app/deps.lock", "native@2.0.0\n")
        named = [*self.others(roles), "--others", f"conventions:{self.commit('conventions: a tool and its own allowance')}"]
        result = self.gate(*named)
        self.assert_fails(result, "FAIL install-scripts [app]: app/deps.lock: native@2.0.0 runs scripts on install, "
                                  "and no ADR accepted at the design commit")

    def test_an_installed_package_whose_script_the_lock_file_does_not_mark_fails(self):
        self.scripts()
        self.put("app/deps.lock", "old@1.0.0\n")
        self.base = self.commit("a package that was there")
        self.put("app/unmarked.txt", "node_modules/sneaky: runs postinstall on install\n")
        self.commit("developer: a lock file without the mark")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: node_modules/sneaky: runs postinstall on install")

    def test_a_comparison_that_cannot_run_fails(self):
        self.scripts(installed=[sys.executable, "-c", "import sys; sys.exit('broken lock file')"])
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: installed packages not compared with the lock file (exit 1)")

    def test_a_failing_setup_fails_the_comparison(self):
        self.scripts(setup=[[sys.executable, "-c", "import sys; sys.exit('cannot install')"]])
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: installed packages not compared with the lock file: setup failed")

    def test_an_allowance_a_conventions_commit_adds_allows_nothing_after_a_later_design_commit(self):
        self.scripts()
        roles = self.start_before_the_documents()
        self.allow_scripts("native@2.0.0")
        conventions = self.commit("conventions: its own allowance")
        self.put("keyturn/internal/design.md", DESIGN + "\nRedone.\n")
        design = self.commit("design: redone after conventions")
        named = [*self.others(roles), "--others", f"conventions:{conventions}", "--others", f"design:{design}"]
        self.put("app/deps.lock", "native@2.0.0\n")
        self.commit("developer: the package")
        self.assert_fails(self.gate(*named), "FAIL install-scripts [app]: app/deps.lock: native@2.0.0 runs scripts on install")

    def test_an_allowance_at_the_base_still_allows_after_a_design_commit(self):
        self.scripts()
        self.allow_scripts("native@2.0.0")
        roles = self.start_before_the_documents()
        self.put("app/deps.lock", "native@2.0.0\n")
        self.commit("developer: the package")
        result = self.gate(*self.others(roles))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_lock_file_read_through_a_symbolic_link_fails(self):
        self.scripts()
        self.write_profile(dict(json.loads((self.profiles / "fake" / "profile.json").read_text()),
                                pinned={"files": ["deps.lock"], "lock": "deps.lock",
                                        "read": [sys.executable, "-c", "import sys; print(sys.stdin.read())"]}))
        self.git("mv", "app", "frontend")
        os.symlink("frontend", self.root / "app")
        self.base = self.commit("the part's folder is a link")
        self.put("frontend/deps.lock", "native@2.0.0\n")
        self.commit("developer: the package")
        result = self.gate()
        self.assert_fails(result, "FAIL install-scripts [app]: app/deps.lock at the base: app is a symbolic link")
        self.assert_fails(result, "FAIL pinned-tools [app]: app/deps.lock at the base: app is a symbolic link")

    def test_a_lock_file_that_cannot_be_read_fails(self):
        self.scripts(read=[sys.executable, "-c", "import sys; sys.exit('not a lock file')"])
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer")
        self.assert_fails(self.gate(), "FAIL install-scripts [app]: app/deps.lock at the base: not a lock file")

    def test_a_conventions_commit_may_not_change_another_part_file(self):
        self.pin()
        roles = self.start_before_the_documents()
        self.put("app/src/main.py", "print('conventions')\n")
        named = [*self.others(roles), "--others", f"conventions:{self.commit('conventions: code')}"]
        result = self.gate(*named)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changes app/src/main.py, which a conventions commit may not", result.stderr)

    def test_qa_s_folders_are_read_at_the_newest_document_commit(self):
        roles = self.start_before_the_documents()
        self.put("app/qa/test_qa.txt", "weakened")
        self.commit("developer changes QA's test")
        self.assert_fails(self.gate(*self.others(roles)), "FAIL protected-paths: app/qa/test_qa.txt (matches app/qa/**)")

    def test_a_document_commit_after_the_developer_s_stops_the_gate(self):
        roles = self.start_before_the_documents()
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer")
        self.put("keyturn/internal/design.md", DESIGN + "\nchanged\n")
        roles["design"] = self.commit("design, later")
        result = self.gate(*self.others(roles))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("the documents are fixed before the developer's work", result.stderr)

    def test_a_document_commit_that_changes_code_stops_the_gate(self):
        roles = self.start_before_the_documents()
        self.put("app/src/main.py", "print('hidden in the spec')\n")
        disguised = self.commit("spec and code")
        result = self.gate(*self.others(roles), "--others", f"spec:{disguised}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changes app/src/main.py, which a spec commit may not", result.stderr)

    def test_another_named_commit_between_the_document_commits_is_not_the_developer_s(self):
        roles = self.start_before_the_documents()
        self.put("keyturn/internal/state/task.md", "# State\n")
        state = self.commit("deliver's state, between conventions and a later conventions commit")
        self.put(".lintrc", "stricter\n")
        later = self.commit("conventions again")
        result = self.gate(*self.others(roles), "--others", f"deliver:{state}", "--others", f"conventions:{later}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_an_adr_the_developer_adds_after_the_documents_approves_nothing(self):
        roles = self.start_before_the_documents()
        self.put("keyturn/internal/adr/0002-allow-everything.md", ADR.replace("0001", "0002").replace("# noqa: F401", "# noqa"))
        self.put("app/src/main.py", "import os  # noqa ADR-0002\n")
        self.commit("developer approves their own suppression")
        result = self.gate(*self.others(roles))
        self.assert_fails(result, "FAIL suppressions [app]: app/src/main.py:1:")

    def test_a_developer_change_to_a_linter_config_still_fails(self):
        roles = self.start_before_the_documents()
        self.put(".lintrc", "loose\n")
        self.commit("developer loosens the linter")
        self.assert_fails(self.gate(*self.others(roles)), "FAIL protected-paths: .lintrc")

    def test_a_developer_change_to_qa_s_folder_fails_even_when_qa_commits_after_it(self):
        self.put("app/qa/test_qa.txt", "weakened")
        self.commit("developer changes QA's test")
        self.put("app/qa/test_qa.txt", "")
        qa = self.commit("QA restores it")
        self.assert_fails(self.gate("--others", f"qa:{qa}"), "FAIL protected-paths: app/qa/test_qa.txt (matches app/qa/**)")

    def test_a_developer_commit_that_edits_the_state_file_fails(self):
        self.put("keyturn/internal/state/task.md", "qa: abc\n")
        self.commit("developer edits the list")
        qa = self.qa_commit()
        self.assert_fails(self.gate("--others", f"qa:{qa}"), "FAIL protected-paths: keyturn/internal/state/task.md")

    def test_a_named_commit_that_changes_what_its_role_may_not_stops_the_gate(self):
        self.put("app/qa/test_qa2.txt", "")
        self.put("app/src/main.py", "print('hidden')\n")
        disguised = self.commit("QA's tests and a code change")
        result = self.gate("--others", f"qa:{disguised}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changes app/src/main.py, which a qa commit may not", result.stderr)

    def test_a_deliver_commit_may_change_the_state_file_the_gate_log_and_the_delivery_documents(self):
        self.put("keyturn/internal/state/task.md", "# State\n")
        self.put("keyturn/internal/gate/task.json", "{}\n")
        self.put("keyturn/client/acceptance-guide.md", "# Acceptance guide\n")
        self.put("keyturn/client/delivery-report.md", "# Delivery report\n")
        delivery = self.commit("deliver's last step")
        result = self.gate("--others", f"deliver:{delivery}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.put("keyturn/client/requirements.md", "# Requirements, changed\n")
        disguised = self.commit("a deliver commit that changes the requirements")
        result = self.gate("--others", f"deliver:{delivery}", "--others", f"deliver:{disguised}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changes keyturn/client/requirements.md, which a deliver commit may not", result.stderr)

    def test_a_merge_commit_may_change_only_the_approvals_and_a_decision_card(self):
        self.put("keyturn/client/approvals.md", "# Approvals\n\naccepted\n")
        self.put("keyturn/client/decision-card-3.md", "# Decision: what to do after the delivery was not accepted\n")
        acceptance = self.commit("merge: the client's acceptance")
        self.assertEqual(self.gate("--others", f"merge:{acceptance}").returncode, 0)
        self.put("keyturn/client/delivery-report.md", "# Delivery report, changed\n")
        disguised = self.commit("a merge commit that changes the delivery report")
        result = self.gate("--others", f"merge:{acceptance}", "--others", f"merge:{disguised}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changes keyturn/client/delivery-report.md, which a merge commit may not", result.stderr)

    def test_a_developer_commit_that_writes_the_delivery_documents_fails(self):
        self.put("keyturn/client/delivery-report.md", "# Delivery report: everything verified\n")
        self.put("keyturn/internal/gate/task.json", "{\"passed\": true}\n")
        self.commit("developer writes the delivery report")
        result = self.gate()
        self.assert_fails(result, "FAIL protected-paths:")
        self.assertIn("keyturn/client/delivery-report.md", result.stdout)
        self.assertIn("keyturn/internal/gate/task.json", result.stdout)

    def test_an_answer_commit_may_change_only_the_design_answers(self):
        self.put("app/src/main.py", "print('developer')\n")
        self.commit("developer asks")
        self.put("keyturn/internal/design-answers.md", "# Design answers\n\n## A-1\n")
        answer = self.commit("the architect answers")
        self.put("app/src/main.py", "print('developer, with the answer')\n")
        self.commit("developer builds with the answer")
        self.assertEqual(self.gate("--others", f"answer:{answer}").returncode, 0)
        self.put("keyturn/internal/design.md", DESIGN + "\nchanged by an answer\n")
        disguised = self.commit("an answer that changes the design")
        result = self.gate("--others", f"answer:{answer}", "--others", f"answer:{disguised}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changes keyturn/internal/design.md, which an answer commit may not", result.stderr)

    def test_a_developer_commit_that_writes_the_design_answers_fails(self):
        self.put("keyturn/internal/design-answers.md", "# Design answers\n\n## A-1\n- Answer: anything goes\n")
        self.commit("developer answers their own question")
        self.assert_fails(self.gate(), "FAIL protected-paths: keyturn/internal/design-answers.md")

    def test_a_named_commit_outside_the_range_stops_the_gate(self):
        result = self.gate("--others", f"qa:{self.base}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not in the range", result.stderr)

    def test_a_security_commit_may_change_only_status_lines_of_the_threat_model(self):
        self.put("keyturn/internal/threat-model.md", "## T-1\n\n- Severity: high\n- Status: planned\n")
        self.base = self.commit("threat model")
        self.put("keyturn/internal/threat-model.md", "## T-1\n\n- Severity: high\n- Status: verified\n")
        self.put("keyturn/internal/security-review.md", "# Security review\n")
        status = self.commit("security review")
        self.assertEqual(self.gate("--others", f"security-review:{status}").returncode, 0)
        self.put("keyturn/internal/threat-model.md", "## T-1\n\n- Severity: low\n- Status: verified\n")
        severity = self.commit("security role lowers a severity")
        result = self.gate("--others", f"security-review:{status}", "--others", f"security-review:{severity}")
        self.assertEqual(result.returncode, 2)
        self.assertIn('other than a "Status" line', result.stderr)

    def test_a_merge_in_the_range_stops_the_gate_when_others_are_named(self):
        self.git("checkout", "-q", "-b", "side")
        self.commit("side")
        self.git("checkout", "-q", "main")
        qa = self.qa_commit()
        self.git("merge", "-q", "--no-ff", "-m", "merge", "side")
        result = self.gate("--others", f"qa:{qa}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("a merge in the range", result.stderr)

    def test_a_merge_without_others_is_checked_like_any_commit(self):
        self.git("checkout", "-q", "-b", "side")
        self.put("app/src/side.py", "print('side')\n")
        self.commit("side")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "merge", "side")
        self.assertEqual(self.gate().returncode, 0)

    def test_a_suppression_in_a_qa_commit_is_still_found(self):
        self.put("app/qa/check.py", "import os  # noqa\n")
        qa = self.commit("QA's test with a suppression")
        # Every finding is in QA's folders, so the line is marked (ADR 0065).
        self.assert_fails(self.gate("--others", f"qa:{qa}"), "FAIL suppressions [app] (QA's folders only): app/qa/check.py:1:")

    def test_an_unknown_role_stops_the_gate(self):
        result = self.gate("--others", f"developer:{self.base}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("use ROLE:COMMIT", result.stderr)

    # Setup errors

    def test_a_missing_tool_stops_with_how_to_install_it(self):
        self.write_profile(dict(PROFILE, tools=[{"command": "no-such-tool-keyturn", "install": "see example.com"}]))
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no-such-tool-keyturn (profile fake) is not installed: see example.com", result.stderr)

    def test_files_that_are_not_committed_are_not_checked(self):
        self.put(".git/info/exclude", "BROKEN\ntest_extra.txt\n")
        self.put("app/BROKEN", "")  # would fail the build if the gate used the working tree
        self.git("rm", "-q", "app/src/test_one.txt")
        self.commit("delete a test")
        self.put("app/src/test_extra.txt", "")  # an ignored stand-in does not make up the count
        self.assert_fails(self.gate(), "FAIL test-count [app]: 2 tests at the base, 1 at the head")
        self.assertIn("PASS build [app]: ok", self.gate().stdout)

    def test_a_failing_setup_fails_the_checks_of_its_part(self):
        self.write_profile(dict(PROFILE, setup=[[sys.executable, "-c", "import sys; sys.exit(3)"]]))
        result = self.gate()
        self.assert_fails(result, "FAIL test-count [app]: at the base: setup failed (exit 3)")
        self.assertIn("FAIL build [app]: not run: setup failed (exit 3)", result.stdout)

    def test_a_configuration_without_parts_stops_the_gate(self):
        self.put("keyturn/config.json", json.dumps({"client_language": "en", "english_only": True}))
        self.commit("no parts")
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn('no "parts"', result.stderr)

    def test_a_design_without_qa_s_tests_stops_the_gate(self):
        self.put("keyturn/internal/design.md", "# Design\n")
        self.base = self.commit("no QA section")
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no \"QA's tests\" section", result.stderr)

    def test_a_broken_profile_stops_the_gate(self):
        self.write_profile(dict(PROFILE, checks=[]))
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("profile fake: checks: must be a non-empty list", result.stderr)

    def test_a_profile_with_a_broken_install_scripts_field_stops_the_gate(self):
        self.write_profile(dict(PROFILE, install_scripts={"lock": "../deps.lock", "read": [], "installed": []}))
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("profile fake: install_scripts: must be null, or", result.stderr)

    def test_a_base_that_is_not_an_ancestor_stops_the_gate(self):
        self.git("checkout", "-q", "-b", "other", self.base)
        other = self.commit("other side")
        self.git("checkout", "-q", "main")
        self.commit("main side")
        self.base = other
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("is not an ancestor", result.stderr)


class TaskRangeTest(unittest.TestCase):
    """The gate finds a task's base and the other roles' commits itself, as in CI (ADR 0043)."""

    # The repository and its helpers are GateTest's; its tests are not run again here.
    tearDown, write_profile, git, put, commit, gate, assert_fails = (
        GateTest.tearDown, GateTest.write_profile, GateTest.git, GateTest.put, GateTest.commit, GateTest.gate,
        GateTest.assert_fails)

    STEPS = ("spec", "design", "conventions", "implement", "qa", "security-review", "review", "deliver")

    def setUp(self):
        GateTest.setUp(self)
        self.git("switch", "-q", "-c", "task/t1")
        self.lines: list[str] = []
        self.done: set[str] = set()
        self.record()  # started
        self.put("keyturn/client/requirements.md", "# Requirements\n")
        self.step("spec")
        self.put("keyturn/internal/conventions.md", "# Conventions\n")
        self.put(".lintrc", "rules\n")
        self.step("conventions")

    def state_text(self) -> str:
        rows = "\n".join(f"| {step} | {'done' if step in self.done else 'not started'} | | | |" for step in self.STEPS)
        commits = "\n".join(self.lines) or "None."
        return (f"# Task state: t1\n\n- Task: t1\n\n## Steps\n\n| Step | Status | Output | Commit | Notes |\n"
                f"|---|---|---|---|---|\n{rows}\n\n## Commits\n\n<!--\n- `0000000`: spec, round 1\n-->\n\n"
                f"{commits}\n\n## History\n\n- started\n")

    def record(self) -> str:
        """A state commit, listing every commit since the last one listed."""
        listed = {line.split("`")[1] for line in self.lines}
        head = self.git("rev-parse", "HEAD")
        if head != self.base:
            for commit in self.git("rev-list", "--reverse", f"{self.base}..HEAD").split():
                if commit[:7] not in listed:
                    self.lines.append(f"- `{commit[:7]}`: {self.roles.get(commit, 'deliver')}, round 1")
        self.put("keyturn/internal/state/t1.md", self.state_text())
        return self.commit("state")

    @property
    def roles(self) -> dict:
        if not hasattr(self, "_roles"):
            self._roles = {}
        return self._roles

    def step(self, role: str, done: bool = True) -> str:
        commit = self.commit(role)
        self.roles[commit] = role
        if done:
            self.done.add(role)
        self.record()
        return commit

    def task_gate(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(GATE), "--task", "t1", "--default-branch", "main",
                               "--profiles", str(self.profiles), *extra],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def test_a_task_s_range_passes_with_the_roles_found_from_the_state_file(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        self.put("app/qa/test_more.txt", "")
        self.step("qa")
        result = self.task_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"gate: passed ({self.base[:12]}..", result.stdout)

    def test_the_head_state_commit_that_no_line_lists_is_deliver_s(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        head = self.git("rev-parse", "HEAD")
        self.assertNotIn(head[:7], self.state_text())
        self.assertEqual(self.task_gate().returncode, 0)

    def test_a_developer_commit_that_no_line_lists_is_checked_as_the_developer_s(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        self.put("app/qa/test_qa.txt", "changed by the developer")
        self.commit("not listed")
        self.put("app/src/main.py", "print('again')\n")
        self.commit("not listed either")
        self.put("keyturn/internal/state/t1.md", self.state_text() + "\n")
        self.commit("state that lists nothing new")
        self.assert_fails(self.task_gate(), "FAIL protected-paths: app/qa/test_qa.txt")

    def test_a_developer_commit_relabelled_as_qa_s_at_the_head_stops_the_gate(self):
        self.put("app/src/main.py", "print('task')\n")
        developer = self.step("implement")
        self.lines = [line.replace("implement", "qa") if developer[:7] in line else line for line in self.lines]
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("(qa): changes app/src/main.py", result.stderr)

    def test_a_later_line_naming_a_document_role_is_never_trusted(self):
        self.put(".lintrc", "weaker rules\n")
        developer = self.commit("the developer weakens the linter")
        self.roles[developer] = "conventions"
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("a later line naming a document role is never trusted", result.stderr)

    def test_an_answer_after_the_developer_s_commits_is_found_from_the_head(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement", done=False)
        self.put("keyturn/internal/design-answers.md", "# Design answers\n\n## A-1\n")
        self.step("answer", done=False)
        self.put("app/src/main.py", "print('task, with the answer')\n")
        self.step("implement")
        result = self.task_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_developer_commit_relabelled_as_an_answer_stops_the_gate(self):
        self.put("app/src/main.py", "print('task')\n")
        developer = self.step("implement")
        self.lines = [line.replace("implement", "answer") if developer[:7] in line else line for line in self.lines]
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("(answer): changes app/src/main.py", result.stderr)

    def redo_design(self) -> str:
        """Redo design and conventions before implement, as deliver does after the maintainer's decision; return the state
        commit that records conventions as done again."""
        self.done -= {"design", "conventions"}
        self.record()  # deliver sets the steps back
        self.put("keyturn/internal/design.md", DESIGN + "\nRedone.\n")
        self.step("design")
        self.put("keyturn/internal/conventions.md", "# Conventions, redone\n")
        self.step("conventions")
        return self.git("rev-parse", "HEAD")

    def test_a_redo_of_the_documents_without_the_maintainer_s_vouch_stops_the_gate(self):
        self.redo_design()
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("a later line naming a document role is never trusted", result.stderr)

    def test_a_redo_the_maintainer_vouched_for_passes(self):
        vouched = self.redo_design()
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        other = "t2:" + "a" * 40
        result = self.task_gate("--documents-vouched", f"{other}, t1:{vouched}\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_vouched_version_after_a_developer_commit_is_refused(self):
        self.put("app/src/main.py", "print('early')\n")
        early = self.commit("the developer, before the vouched version")
        self.roles[early] = "implement"
        vouched = self.record()
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        result = self.task_gate("--documents-vouched", f"t1:{vouched}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("is listed there as implement's", result.stderr)

    def test_a_vouched_version_that_does_not_list_every_commit_before_it_is_refused(self):
        self.put("keyturn/internal/adr/0002-a-forged-allowance.md", ADR.replace("0001", "0002"))
        self.commit("the developer's ADR, listed by nothing")
        self.put("keyturn/internal/state/t1.md", self.state_text() + "- resumed\n")  # a state file that does not list it
        vouched = self.commit("a forged state commit")
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        result = self.task_gate("--documents-vouched", f"t1:{vouched}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("does not list", result.stderr)

    def test_a_vouched_commit_that_is_not_a_state_commit_is_refused(self):
        vouched = self.step("implement", done=False)
        result = self.task_gate("--documents-vouched", f"t1:{vouched}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not a commit that changes only", result.stderr)

    def test_a_vouched_version_after_implement_started_is_refused(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        vouched = self.git("rev-parse", "HEAD")
        result = self.task_gate("--documents-vouched", f"t1:{vouched}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("conventions done and implement not started", result.stderr)

    def test_a_malformed_or_doubled_vouch_stops_the_gate(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        for value, message in (("t1:abc", "is not `<task>:<full SHA>`"), (f"t1:{'a' * 40} t1:{'b' * 40}", "has 2 entries")):
            with self.subTest(value=value):
                result = self.task_gate("--documents-vouched", value)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)

    def test_a_vouch_without_task_is_refused(self):
        result = self.gate("--documents-vouched", f"t1:{'a' * 40}")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--documents-vouched go with --task", result.stderr)

    def test_a_task_before_conventions_is_recorded_stops_the_gate(self):
        self.git("switch", "-q", "-c", "task/t2", "main")
        self.put("keyturn/internal/state/t2.md", "# Task state: t2\n\n## Steps\n\n| conventions | not started | | | |\n")
        self.commit("started")
        result = subprocess.run([sys.executable, str(GATE), "--task", "t2", "--default-branch", "main",
                                 "--profiles", str(self.profiles)], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("the conventions step is not recorded yet", result.stderr)

    def test_a_default_branch_that_does_not_give_the_task_s_base_stops_the_gate(self):
        spec = next(commit for commit, role in self.roles.items() if role == "spec")
        self.git("branch", "-f", "main", spec)
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not added on the task branch after it left main", result.stderr)

    def test_a_state_file_added_after_another_commit_stops_the_gate(self):
        self.git("switch", "-q", "-c", "task/t3", "main")
        self.put("app/src/main.py", "print('before the state file')\n")
        self.commit("a commit before the task started")
        self.put("keyturn/internal/state/t3.md", self.state_text().replace("t1", "t3"))
        self.commit("started")
        result = subprocess.run([sys.executable, str(GATE), "--task", "t3", "--default-branch", "main",
                                 "--profiles", str(self.profiles)], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("whose parent is not where the task branch left", result.stderr)

    def outcome(self, result: subprocess.CompletedProcess) -> tuple[int, list[str]]:
        lines = [line for line in result.stdout.splitlines() if line.startswith(("PASS ", "FAIL "))]
        return result.returncode, lines

    def test_the_task_mode_gives_the_same_result_as_deliver_s_call(self):
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        self.put("app/qa/test_more.txt", "")
        self.step("qa")
        self.put("app/BROKEN", "")  # the fake profile's build fails while it exists
        self.step("implement")
        others = []
        for commit in self.git("rev-list", "--reverse", f"{self.base}..HEAD").split():
            role = self.roles.get(commit, "deliver")
            if role != "implement":
                others += ["--others", f"{role}:{commit}"]
        by_task = self.task_gate()
        by_deliver = self.gate(*others)
        self.assertEqual(by_task.returncode, 1, by_task.stdout + by_task.stderr)
        self.assertEqual(self.outcome(by_task), self.outcome(by_deliver))

    def test_a_commit_named_as_two_roles_at_the_head_stops_the_gate(self):
        qa = self.commit("qa")
        self.roles[qa] = "qa"
        self.record()
        self.lines.append(f"- `{qa[:7]}`: review, round 1")
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("and as qa's too", result.stderr)

    def test_a_developer_commit_also_named_as_qa_s_stops_the_gate(self):
        self.put("app/qa/test_qa.txt", "changed by the developer")
        developer = self.step("implement")
        self.lines.append(f"- `{developer}`: qa, round 1")
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("and as implement's too", result.stderr)

    def test_a_listed_commit_that_is_not_in_the_range_stops_the_gate(self):
        self.lines.append(f"- `{self.base[:7]}`: qa, round 1")
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("is not a commit it could list", result.stderr)

    def test_an_unknown_step_stops_the_gate(self):
        qa = self.commit("qa")
        self.roles[qa] = "build"
        self.record()
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("build is not a step of the task state file", result.stderr)

    def test_a_state_file_deleted_at_the_head_stops_the_gate(self):
        self.git("rm", "-q", "keyturn/internal/state/t1.md")
        self.commit("delete the state file")
        result = self.task_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("missing at the head", result.stderr)

    def test_a_task_name_that_is_not_one_stops_the_gate(self):
        for name in ("A", "a/b", "-x"):
            result = subprocess.run([sys.executable, str(GATE), f"--task={name}", "--default-branch", "main",
                                     "--profiles", str(self.profiles)], cwd=self.root, env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, name + result.stdout + result.stderr)
            self.assertIn("not a task name", result.stderr)

    def test_an_unlisted_role_commit_at_the_head_is_checked_as_the_developer_s(self):
        self.put("app/qa/test_more.txt", "")
        self.commit("a qa commit no state commit lists yet")
        self.assert_fails(self.task_gate(), "FAIL protected-paths: app/qa/test_more.txt")

    def test_a_developer_commit_after_the_record_is_checked_as_the_developer_s(self):
        recorded = self.state_text()
        conventions = next(c for c, role in self.roles.items() if role == "conventions")
        # A later developer commit whose hash starts like the conventions commit's is not taken for it: the record's
        # line still names only the commit before it, so the developer's change to the linter config is checked.
        self.put(".lintrc", "weaker rules\n")
        developer = self.commit("the developer weakens the linter")
        self.roles[developer] = "implement"
        self.record()
        self.assertIn(conventions[:7], recorded)
        self.assert_fails(self.task_gate(), "FAIL protected-paths: .lintrc")

    def test_full_hashes_are_read_too(self):
        self.lines = [line.replace(line.split("`")[1], self.git("rev-parse", line.split("`")[1])) for line in self.lines]
        self.put("app/src/main.py", "print('task')\n")
        self.step("implement")
        self.assertEqual(self.task_gate().returncode, 0)

    def test_others_with_task_is_refused(self):
        result = self.task_gate("--others", f"qa:{self.base}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--task needs --default-branch", result.stderr)


class ShippedProfiles(unittest.TestCase):
    """Every profile in keyturn's profiles/ is one the gate accepts, and has the README the roles read."""

    def test_every_shipped_profile_is_valid(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("gate_module", GATE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module  # its dataclasses look their module up there
        try:
            spec.loader.exec_module(module)
        finally:
            del sys.modules[spec.name]
        folders = sorted(p for p in (GATE.parent.parent / "profiles").iterdir() if p.is_dir())
        self.assertTrue(folders)
        for folder in folders:
            with self.subTest(profile=folder.name):
                profile = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
                self.assertEqual(module.profile_problems(folder.name, profile), [])
                self.assertTrue((folder / "README.md").is_file())


    @unittest.skipUnless(shutil.which("node"), "needs Node.js")
    def test_react_spa_reads_every_package_with_an_install_script_but_the_part_itself(self):
        profile = json.loads((GATE.parent.parent / "profiles" / "react-spa" / "profile.json").read_text(encoding="utf-8"))
        lock = {"lockfileVersion": 3, "packages": {
            "": {"name": "app", "hasInstallScript": True},
            "node_modules/plain": {"version": "1.0.0"},
            "node_modules/native": {"version": "2.0.0", "hasInstallScript": True},
            "node_modules/a/node_modules/@scope/deep": {"version": "3.1.0", "hasInstallScript": True}}}
        read = profile["install_scripts"]["read"]
        result = subprocess.run(read, input=json.dumps(lock), capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.split(), ["native@2.0.0", "@scope/deep@3.1.0"])
        empty = subprocess.run(read, input="", capture_output=True, text=True, check=True)
        self.assertEqual(empty.stdout, "")

    @unittest.skipUnless(shutil.which("node"), "needs Node.js")
    def test_react_spa_finds_an_installed_script_that_the_lock_file_does_not_mark(self):
        profile = json.loads((GATE.parent.parent / "profiles" / "react-spa" / "profile.json").read_text(encoding="utf-8"))
        installed = profile["install_scripts"]["installed"]
        with tempfile.TemporaryDirectory() as folder:
            part = Path(folder)

            def package(key: str, manifest: dict, gyp: bool = False) -> None:
                (part / key).mkdir(parents=True)
                (part / key / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
                if gyp:
                    (part / key / "binding.gyp").write_text("{}", encoding="utf-8")

            def compare(packages: dict) -> list[str]:
                (part / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": packages}), encoding="utf-8")
                result = subprocess.run(installed, cwd=part, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout.splitlines()

            package("node_modules/plain", {"name": "plain", "scripts": {"test": "x", "prepare": "x"}})
            package("node_modules/marked", {"name": "marked", "scripts": {"postinstall": "node setup.js"}})
            package("node_modules/a/node_modules/deep", {"name": "deep", "scripts": {"preinstall": "x", "install": "y"}})
            package("node_modules/gyp", {"name": "gyp"}, gyp=True)
            package("node_modules/no-gyp", {"name": "no-gyp", "gypfile": False}, gyp=True)
            package("node_modules/prebuilt", {"name": "prebuilt"})
            honest = {"": {"name": "app", "scripts": {"postinstall": "x"}},
                      "node_modules/plain": {"version": "1.0.0"},
                      "node_modules/marked": {"version": "1.0.0", "hasInstallScript": True},
                      "node_modules/a/node_modules/deep": {"version": "1.0.0", "hasInstallScript": True},
                      "node_modules/gyp": {"version": "1.0.0", "hasInstallScript": True},
                      "node_modules/no-gyp": {"version": "1.0.0"},
                      # a mark with no script in the installed manifest (as fsevents has) is left to install-scripts
                      "node_modules/prebuilt": {"version": "1.0.0", "hasInstallScript": True},
                      # an optional package for another platform is not installed
                      "node_modules/other-os": {"version": "1.0.0", "optional": True}}
            self.assertEqual(compare(honest), [])
            edited = {key: {k: v for k, v in entry.items() if k != "hasInstallScript"} for key, entry in honest.items()}
            self.assertEqual(compare(edited), [
                "node_modules/marked: runs postinstall on install, but package-lock.json does not mark it with hasInstallScript",
                "node_modules/a/node_modules/deep: runs preinstall, install on install, but package-lock.json does not mark it "
                "with hasInstallScript",
                "node_modules/gyp: runs node-gyp rebuild (it has a binding.gyp) on install, but package-lock.json does not mark "
                "it with hasInstallScript"])
            (part / "package-lock.json").unlink()
            result = subprocess.run(installed, cwd=part, capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout), (0, ""))

if __name__ == "__main__":
    unittest.main()
