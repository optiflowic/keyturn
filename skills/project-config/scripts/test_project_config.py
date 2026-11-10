"""Tests for project_config.py. Run from the repository root: python3 -m unittest discover -s skills/project-config/scripts"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("project_config.py")
VALID = b'{\n  "client_language": "ja",\n  "english_only": false\n}\n'


class ProjectConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.config = self.root / "keyturn" / "config.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data: bytes) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_bytes(data)

    def run_script(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or self.root, capture_output=True, text=True)

    def assert_problems(self, *problems: str) -> None:
        result = self.run_script("check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "".join(f"error: {p}\n" for p in problems))

    # Valid files

    def test_a_valid_file_is_ok(self):
        self.write(VALID)
        result = self.run_script("check")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "ok\n", ""))

    def test_english_only_true_and_a_regional_code_are_ok(self):
        self.write(b'{"client_language": "pt-BR", "english_only": true}')
        self.assertEqual(self.run_script("check").stdout, "ok\n")

    def test_get_prints_one_setting(self):
        self.write(VALID)
        self.assertEqual(self.run_script("get", "client_language").stdout, "ja\n")
        self.assertEqual(self.run_script("get", "english_only").stdout, "false\n")

    def test_paths_are_relative_to_the_repository_root_from_any_folder(self):
        self.write(VALID)
        sub = self.root / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(self.run_script("check", cwd=sub).stdout, "ok\n")

    # Problems

    def test_a_missing_file_is_reported(self):
        self.assert_problems("keyturn/config.json: missing (create it with: project_config.py init)")

    def test_missing_settings_are_each_reported(self):
        self.write(b"{}")
        self.assert_problems("client_language: missing", "english_only: missing")

    def test_invalid_values_are_reported(self):
        self.write(b'{"client_language": "Japanese!", "english_only": "yes"}')
        self.assert_problems(
            'client_language: not a language code: "Japanese!" (use e.g. "ja", "de", "pt-BR")',
            'english_only: must be true or false, not "yes"',
        )

    def test_a_number_is_not_a_boolean(self):
        self.write(b'{"client_language": "ja", "english_only": 0}')
        self.assert_problems("english_only: must be true or false, not 0")

    def test_unknown_settings_are_reported_in_name_order(self):
        self.write(b'{"client_language": "ja", "english_only": false, "zeta": 1, "alpha": 2}')
        self.assert_problems("alpha: unknown setting", "zeta: unknown setting")

    def test_a_setting_given_twice_is_reported(self):
        self.write(b'{"client_language": "ja", "client_language": "de", "english_only": false}')
        self.assert_problems("client_language: set more than once")

    def test_malformed_json_is_reported_with_its_position(self):
        self.write(b'{"client_language": "ja",, "english_only": false}')
        result = self.run_script("check")
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stderr, r"^error: keyturn/config.json: not valid JSON: .+ \(line 1, column \d+\)\n$")

    def test_a_json_value_that_is_not_an_object_is_reported(self):
        self.write(b'["ja", false]')
        self.assert_problems("the configuration must be a JSON object ({...})")

    def test_text_that_is_not_utf8_is_reported(self):
        self.write('{"client_language": "ja", "english_only": false}'.encode("utf-16"))
        self.assert_problems("keyturn/config.json: not UTF-8 text")

    def test_get_refuses_a_broken_file_and_an_unknown_setting(self):
        self.write(b"{}")
        result = self.run_script("get", "client_language")
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.write(VALID)
        result = self.run_script("get", "model")
        self.assertEqual(result.returncode, 1)
        self.assertIn("model: unknown setting", result.stderr)

    def test_the_same_file_always_gives_the_same_result(self):
        self.write(b'{"zeta": 1, "english_only": "no", "alpha": 2}')
        results = {(r.returncode, r.stdout, r.stderr) for r in (self.run_script("check") for _ in range(3))}
        self.assertEqual(len(results), 1)

    # init

    def test_init_writes_the_canonical_file(self):
        result = self.run_script("init", "--client-language", "ja", "--no-english-only")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), VALID)
        self.assertEqual(self.run_script("check").stdout, "ok\n")

    def test_init_refuses_to_overwrite(self):
        self.write(b'{"client_language": "de", "english_only": true}')
        result = self.run_script("init", "--client-language", "ja", "--english-only")
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(self.config.read_bytes(), b'{"client_language": "de", "english_only": true}')

    def test_init_reports_a_file_it_cannot_write_without_a_traceback(self):
        (self.root / "keyturn").write_bytes(b"a file where the folder should be")
        result = self.run_script("init", "--client-language", "ja", "--english-only")
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stderr, r"^error: keyturn/config.json: cannot write: .+\n$")
        self.assertNotIn("Traceback", result.stderr)

    def test_init_refuses_an_invalid_language_and_needs_a_mode(self):
        result = self.run_script("init", "--client-language", "../x", "--english-only")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.config.exists())
        result = self.run_script("init", "--client-language", "ja")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.config.exists())


if __name__ == "__main__":
    unittest.main()
