"""Tests for gate.py. Run from the repository root: python3 -m unittest discover -s gates"""

from __future__ import annotations

import json
import os
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
        self.assert_fails(self.gate("--others", f"qa:{qa}"), "FAIL suppressions [app]: app/qa/check.py:1:")

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

    def test_a_base_that_is_not_an_ancestor_stops_the_gate(self):
        self.git("checkout", "-q", "-b", "other", self.base)
        other = self.commit("other side")
        self.git("checkout", "-q", "main")
        self.commit("main side")
        self.base = other
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("is not an ancestor", result.stderr)


if __name__ == "__main__":
    unittest.main()
