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

ADR = "# 0001. Allow one noqa\n\n- Status: accepted\n- Date: 2026-11-21\n"


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
        self.assertIn("keyturn/internal/design.md (matches keyturn/internal/design.md)", result.stdout)

    def test_a_path_with_a_newline_is_still_protected(self):
        self.put("app/qa/a\nb.txt", "")
        self.commit("odd name")
        self.assert_fails(self.gate(), "FAIL protected-paths: app/qa/a")

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

    def test_an_adr_added_in_the_range_approves_nothing(self):
        self.put("keyturn/internal/adr/0001-allow-one-noqa.md", ADR)
        self.put("app/src/main.py", "print('hello')\nimport os  # noqa: F401  ADR-0001\n")
        self.commit("ADR and suppression together")
        result = self.gate()
        self.assert_fails(result, "FAIL suppressions [app]: app/src/main.py:2:")
        self.assertIn("names ADR-0001, not accepted at the base", result.stdout)
        self.assertIn("keyturn/internal/adr/0001-allow-one-noqa.md", result.stdout)  # and the ADR is a protected path

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

    # Setup errors

    def test_a_missing_tool_stops_with_how_to_install_it(self):
        self.write_profile(dict(PROFILE, tools=[{"command": "no-such-tool-keyturn", "install": "see example.com"}]))
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no-such-tool-keyturn (profile fake) is not installed: see example.com", result.stderr)

    def test_uncommitted_changes_stop_the_gate(self):
        self.put("app/src/main.py", "print('edited')\n")
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("uncommitted changes", result.stderr)

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
