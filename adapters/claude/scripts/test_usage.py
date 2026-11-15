"""Tests for usage.py. Run: python3 -m unittest discover -s adapters/claude/scripts"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("usage.py")
NOW = 1_800_000_000.0  # a fixed "now", in epoch seconds
HOUR = 3600.0


def status(five_hour: float | None = 42.0, seven_day: float | None = 13.0, resets_in: float = 2 * HOUR) -> str:
    limits = {}
    if five_hour is not None:
        limits["five_hour"] = {"used_percentage": five_hour, "resets_at": NOW + resets_in}
    if seven_day is not None:
        limits["seven_day"] = {"used_percentage": seven_day, "resets_at": NOW + 3 * 24 * HOUR}
    return json.dumps({"workspace": {"current_dir": "/tmp"}, "rate_limits": limits})


class UsageTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.file = Path(self.folder.name) / "usage.json"

    def tearDown(self):
        self.folder.cleanup()

    def run_script(self, *args: str, stdin: str = "", now: float = NOW,
                   extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = {name: value for name, value in os.environ.items() if not name.startswith("KEYTURN_")}
        env["KEYTURN_USAGE_FILE"] = str(self.file)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, str(SCRIPT), "--now", str(now), *args],
                              input=stdin, capture_output=True, text=True, env=env)

    def record(self, text: str, now: float = NOW) -> None:
        self.assertEqual(self.run_script("statusline", stdin=text, now=now).returncode, 0)

    # statusline

    def test_statusline_records_and_prints_both_windows(self):
        result = self.run_script("statusline", stdin=status())
        self.assertEqual(result.stdout.strip(), "5-hour 42%  7-day 13%")
        saved = json.loads(self.file.read_text())
        self.assertEqual(saved["written_at"], NOW)
        self.assertEqual(saved["windows"]["five_hour"],
                         {"used_percentage": 42.0, "resets_at": NOW + 2 * HOUR, "recorded_at": NOW})

    def test_statusline_without_rate_limits_records_nothing_known(self):
        result = self.run_script("statusline", stdin=json.dumps({"workspace": {}}))
        self.assertEqual(result.stdout.strip(), "usage: unknown")
        self.assertEqual(json.loads(self.file.read_text())["windows"], {})

    def test_statusline_never_fails_on_bad_input(self):
        for text in ("not json", "[]", json.dumps({"rate_limits": []})):
            with self.subTest(text=text):
                result = self.run_script("statusline", stdin=text)
                self.assertEqual((result.returncode, result.stdout.strip()), (0, "usage: unknown"))

    def test_statusline_keeps_a_window_the_input_leaves_out_until_it_resets(self):
        self.record(status(five_hour=95.0, resets_in=HOUR))
        self.record(json.dumps({"workspace": {}}), now=NOW + 60)
        decision = json.loads(self.run_script("hook", stdin="{}", now=NOW + 120).stdout)
        self.assertIn("5-hour window at 95%", decision["hookSpecificOutput"]["permissionDecisionReason"])
        self.record(json.dumps({"workspace": {}}), now=NOW + 2 * HOUR)
        self.assertNotIn("five_hour", json.loads(self.file.read_text())["windows"])

    def test_statusline_skips_values_out_of_range_or_of_the_wrong_type(self):
        for used in (-1, 101, "42", True, None):
            with self.subTest(used=used):
                limits = {"five_hour": {"used_percentage": used, "resets_at": NOW + HOUR}}
                result = self.run_script("statusline", stdin=json.dumps({"rate_limits": limits}))
                self.assertEqual(result.stdout.strip(), "usage: unknown")

    def test_statusline_reports_a_file_it_cannot_write(self):
        blocker = Path(self.folder.name) / "not-a-folder"
        blocker.write_text("")
        env = dict(os.environ, KEYTURN_USAGE_FILE=str(blocker / "usage.json"))
        result = subprocess.run([sys.executable, str(SCRIPT), "--now", str(NOW), "statusline"],
                                input=status(), capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith("usage: not recorded ("), result.stdout)
        self.assertEqual(result.stderr, "")

    # check (soft stop)

    def test_check_passes_below_the_soft_limit(self):
        self.record(status(five_hour=79.0))
        result = self.run_script("check")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "ok: 5-hour window at 79%, 7-day window at 13%")

    def test_check_stops_at_the_soft_limit_and_says_when(self):
        self.record(status(five_hour=80.0, resets_in=HOUR))
        result = self.run_script("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("stop: 5-hour window at 80% (limit 80%), can continue after", result.stdout)

    def test_check_applies_to_the_seven_day_window_too(self):
        self.record(status(seven_day=85.0))
        self.assertIn("stop: 7-day window at 85%", self.run_script("check").stdout)

    def test_check_soft_limit_is_configurable(self):
        self.record(status(five_hour=70.0))
        self.assertEqual(self.run_script("check", "--soft", "60").returncode, 1)

    def test_check_stops_when_nothing_is_recorded(self):
        result = self.run_script("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no usage recorded", result.stdout)

    def test_check_stops_when_a_window_is_missing(self):
        self.record(status(seven_day=None))
        result = self.run_script("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("7-day window: not in the last recording", result.stdout)

    def test_check_stops_when_the_recording_is_old(self):
        self.record(status(five_hour=10.0), now=NOW - 20 * 60)
        result = self.run_script("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("more than 15 minutes ago", result.stdout)

    def test_check_stops_after_a_reset_until_a_new_value_arrives(self):
        self.record(status(five_hour=95.0, resets_in=60))
        result = self.run_script("check", now=NOW + 120)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no newer value yet", result.stdout)

    # hook (hard stop)

    def test_hook_allows_below_the_hard_limit(self):
        self.record(status(five_hour=89.0))
        result = self.run_script("hook", stdin="{}")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_hook_denies_at_the_hard_limit(self):
        self.record(status(seven_day=90.0))
        result = self.run_script("hook", stdin="{}")
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("7-day window at 90% (limit 90%)", decision["permissionDecisionReason"])

    def test_hook_still_denies_on_an_old_high_value(self):
        self.record(status(five_hour=95.0, resets_in=3 * HOUR), now=NOW - HOUR)
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)

    def test_hook_does_not_block_on_missing_data(self):
        result = self.run_script("hook", stdin="{}")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_hook_ignores_a_value_past_its_reset(self):
        self.record(status(five_hour=95.0, resets_in=60))
        self.assertEqual(self.run_script("hook", stdin="{}", now=NOW + 120).stdout, "")

    def test_hook_still_denies_when_the_other_window_has_an_impossible_reset_time(self):
        windows = {"five_hour": {"used_percentage": 95.0, "resets_at": NOW + HOUR, "recorded_at": NOW},
                   "seven_day": {"used_percentage": 10.0, "resets_at": -1e100, "recorded_at": NOW}}
        self.file.write_text(json.dumps({"written_at": NOW, "windows": windows}))
        result = self.run_script("hook", stdin="{}")
        self.assertEqual(result.returncode, 0)
        self.assertIn("5-hour window at 95%", json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"])

    def test_installed_hook_takes_the_hard_limit_from_the_environment(self):
        hooks = json.loads((SCRIPT.parents[3] / "hooks" / "hooks.json").read_text())
        command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertNotIn("--hard", command)

    def test_hook_hard_limit_is_configurable(self):
        self.record(status(five_hour=75.0))
        self.assertIn("deny", self.run_script("hook", "--hard", "70", stdin="{}").stdout)

    def test_limits_can_come_from_the_environment(self):
        self.record(status(five_hour=75.0))
        self.assertEqual(self.run_script("check", extra_env={"KEYTURN_SOFT_LIMIT": "70"}).returncode, 1)
        self.assertIn("deny", self.run_script("hook", stdin="{}", extra_env={"KEYTURN_HARD_LIMIT": "70"}).stdout)

    def test_limits_must_be_percentages(self):
        for value in ("0", "101", "nan", "inf", "abc"):
            with self.subTest(value=value):
                for args in (("check", "--soft", value), ("hook", "--hard", value)):
                    result = self.run_script(*args, stdin="{}")
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("not a percentage", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_max_age_must_be_positive(self):
        for value in ("0", "-5", "nan", "abc"):
            with self.subTest(value=value):
                result = self.run_script("--max-age-minutes", value, "check")
                self.assertEqual(result.returncode, 2)
                self.assertIn("not a positive number of minutes", result.stderr)

    # the recorded file

    def test_a_malformed_file_is_unknown_never_ok_and_never_blocks(self):
        bad_windows = [
            {"recorded_at": NOW, "resets_at": NOW + HOUR},                                  # a missing key
            {"used_percentage": "95", "resets_at": NOW + HOUR, "recorded_at": NOW},        # a string
            {"used_percentage": float("nan"), "resets_at": NOW + HOUR, "recorded_at": NOW},
            {"used_percentage": 150, "resets_at": NOW + HOUR, "recorded_at": NOW},
            {"used_percentage": 50, "resets_at": "soon", "recorded_at": NOW},
        ]
        for window in bad_windows:
            with self.subTest(window=window):
                good = {"used_percentage": 10, "resets_at": NOW + HOUR, "recorded_at": NOW}
                self.file.write_text(json.dumps({"written_at": NOW, "windows": {"five_hour": window, "seven_day": good}}))
                check = self.run_script("check")
                self.assertEqual(check.returncode, 1)
                self.assertIn("5-hour window: not in the last recording", check.stdout)
                self.assertNotIn("Traceback", check.stderr)
                hook = self.run_script("hook", stdin="{}")
                self.assertEqual((hook.returncode, hook.stdout), (0, ""))

    def test_a_relative_usage_file_is_refused(self):
        check = self.run_script("check", extra_env={"KEYTURN_USAGE_FILE": "usage.json"})
        self.assertEqual(check.returncode, 1)
        self.assertIn("stop: KEYTURN_USAGE_FILE must be an absolute path", check.stdout)
        hook = self.run_script("hook", stdin="{}", extra_env={"KEYTURN_USAGE_FILE": "usage.json"})
        self.assertEqual(hook.returncode, 2)
        self.assertIn("must be an absolute path", hook.stderr)

    def test_a_window_that_resets_now_is_past_its_reset(self):
        self.record(status(five_hour=95.0, resets_in=60))
        self.assertIn("no newer value yet", self.run_script("check", now=NOW + 60).stdout)
        self.assertEqual(self.run_script("hook", stdin="{}", now=NOW + 60).stdout, "")

    # release (a person lifts a stop until the window resets)

    def tool_call(self, **tool_input) -> str:
        return json.dumps({"tool_name": "Bash" if "command" in tool_input else "Write", "tool_input": tool_input})

    def test_release_lifts_the_soft_stop_until_the_window_resets(self):
        self.record(status(five_hour=85.0))
        self.assertEqual(self.run_script("check").returncode, 1)
        result = self.run_script("release")
        self.assertEqual(result.returncode, 0)
        self.assertIn("5-hour window at 85%, soft stop lifted until", result.stdout)
        check = self.run_script("check")
        self.assertEqual(check.returncode, 0)
        self.assertIn("released by a person until", check.stdout)

    def test_a_soft_release_keeps_the_hard_stop(self):
        self.record(status(five_hour=85.0))
        self.run_script("release")
        self.record(status(five_hour=95.0))
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)

    def test_release_lifts_the_hard_stop_too(self):
        self.record(status(five_hour=95.0))
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)
        self.assertIn("hard stop and soft stop lifted", self.run_script("release").stdout)
        self.assertEqual(self.run_script("hook", stdin="{}").stdout, "")
        self.assertEqual(self.run_script("check").returncode, 0)

    def test_the_next_window_stops_again(self):
        self.record(status(five_hour=95.0, resets_in=HOUR))
        self.run_script("release")
        later = NOW + 2 * HOUR
        self.record(status(five_hour=95.0, resets_in=6 * HOUR), now=later)  # the next window, with a new reset time
        self.assertIn("deny", self.run_script("hook", stdin="{}", now=later).stdout)
        self.assertEqual(self.run_script("check", now=later).returncode, 1)

    def test_a_release_ends_at_the_reset_time(self):
        self.record(status(five_hour=95.0, resets_in=HOUR))
        self.run_script("release")
        after = NOW + HOUR + 60  # past the reset, before a new value arrives
        self.assertIn("no newer value yet", self.run_script("check", now=after).stdout)
        self.record(status(five_hour=95.0, resets_in=HOUR), now=after)  # an old value sent again does not count
        self.assertEqual(self.run_script("check", now=after).returncode, 1)

    def test_release_works_on_an_old_recording(self):
        self.record(status(five_hour=95.0, resets_in=3 * HOUR))
        later = NOW + HOUR  # the hard stop kept anything from refreshing the recording
        self.assertIn("deny", self.run_script("hook", stdin="{}", now=later).stdout)
        self.assertEqual(self.run_script("release", now=later).returncode, 0)
        self.assertEqual(self.run_script("hook", stdin="{}", now=later).stdout, "")

    def test_release_records_each_window_at_its_own_stop(self):
        self.record(status(five_hour=95.0, seven_day=85.0))
        result = self.run_script("release")
        self.assertIn("5-hour window at 95%, hard stop and soft stop lifted", result.stdout)
        self.assertIn("7-day window at 85%, soft stop lifted", result.stdout)

    def test_release_limits_must_be_percentages(self):
        result = self.run_script("release", "--soft", "abc")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a percentage", result.stderr)

    def test_releasing_again_keeps_a_hard_release(self):
        self.record(status(five_hour=95.0))
        self.run_script("release", "--hard", "90")
        self.assertIn("hard stop and soft stop lifted", self.run_script("release", "--hard", "99").stdout)
        self.assertEqual(self.run_script("hook", stdin="{}").stdout, "")

    def test_release_with_nothing_to_release(self):
        self.record(status(five_hour=42.0))
        result = self.run_script("release")
        self.assertEqual(result.returncode, 1)
        self.assertIn("nothing to release", result.stdout)
        self.assertFalse((Path(self.folder.name) / "usage-release.json").exists())

    def test_release_needs_a_known_value(self):
        self.record(status(five_hour=85.0, seven_day=None))
        result = self.run_script("release")
        self.assertIn("not released: 7-day window", result.stdout)
        self.assertEqual(self.run_script("check").returncode, 1)  # the unknown window still stops

    def test_a_broken_release_file_releases_nothing(self):
        self.record(status(five_hour=95.0))
        (Path(self.folder.name) / "usage-release.json").write_text("{not json")
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)
        self.assertEqual(self.run_script("check").returncode, 1)

    def test_hook_denies_an_agent_that_tries_to_release(self):
        release_path = str(Path(self.folder.name) / "usage-release.json")
        for call in (self.tool_call(command="python3 adapters/claude/scripts/usage.py release"),
                     self.tool_call(command="python3 usage.py --max-age-minutes 5 release --soft 99"),
                     self.tool_call(command=f"echo '{{}}' > {release_path}"),
                     self.tool_call(command='python3 "${CLAUDE_PLUGIN_ROOT}/adapters/claude/scripts/usage.py" release'),
                     self.tool_call(command='python3 usage.py "release"'),
                     self.tool_call(command="python3 usage.py 'release'"),
                     self.tool_call(command="python3 usage.py \\\nrelease"),
                     self.tool_call(file_path=release_path, content="{}"),
                     self.tool_call(file_path="usage-release.json", content="{}"),
                     json.dumps({"tool_name": "NotebookEdit", "tool_input": {"notebook_path": release_path}})):
            with self.subTest(call=call):
                result = self.run_script("hook", stdin=call)
                decision = json.loads(result.stdout)["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn("only a person can release", decision["permissionDecisionReason"])

    def test_hook_allows_other_calls_that_name_the_script(self):
        for call in (self.tool_call(command="python3 adapters/claude/scripts/usage.py check"),
                     self.tool_call(command='python3 usage.py check && git commit -m "release notes"'),
                     self.tool_call(file_path="/tmp/README.md", content="run `usage.py release` yourself")):
            with self.subTest(call=call):
                self.assertEqual(self.run_script("hook", stdin=call).stdout, "")

    # plans without a 5-hour window

    def test_a_plan_without_a_five_hour_window_stops_only_on_the_seven_day_window(self):
        self.record(status(five_hour=None, seven_day=10.0))
        self.assertEqual(self.run_script("check").returncode, 1)  # not said: it may not have arrived yet
        plan = {"KEYTURN_PLAN_WINDOWS": "seven_day"}
        result = self.run_script("check", extra_env=plan)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "ok: 7-day window at 10%"))
        self.record(status(five_hour=None, seven_day=85.0))
        self.assertEqual(self.run_script("check", extra_env=plan).returncode, 1)

    def test_a_window_the_plan_has_still_stops_until_it_arrives(self):
        self.record(status(five_hour=42.0, seven_day=None))
        result = self.run_script("check", extra_env={"KEYTURN_PLAN_WINDOWS": "seven_day"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("7-day window: not in the last recording", result.stdout)

    def test_release_covers_a_recorded_window_the_plan_leaves_out(self):
        self.record(status(five_hour=95.0, seven_day=10.0))
        plan = {"KEYTURN_PLAN_WINDOWS": "seven_day"}
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)  # a known value still stops the hook
        self.assertEqual(self.run_script("release", extra_env=plan).returncode, 0)
        self.assertEqual(self.run_script("hook", stdin="{}").stdout, "")

    def test_a_known_value_still_stops_a_window_the_plan_leaves_out(self):
        self.record(status(five_hour=85.0, seven_day=10.0))
        result = self.run_script("check", extra_env={"KEYTURN_PLAN_WINDOWS": "seven_day"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("5-hour window at 85%", result.stdout)

    def test_release_lifts_a_hard_stop_below_the_soft_limit(self):
        self.record(status(five_hour=92.0))
        limits = {"KEYTURN_SOFT_LIMIT": "95"}
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)
        self.assertEqual(self.run_script("release", extra_env=limits).returncode, 0)
        self.assertEqual(self.run_script("hook", stdin="{}").stdout, "")

    def test_release_says_when_it_cannot_be_recorded(self):
        self.record(status(five_hour=95.0))
        (Path(self.folder.name) / "usage-release.json").mkdir()
        result = self.run_script("release")
        self.assertEqual(result.returncode, 1)
        self.assertIn("the release was not recorded", result.stdout)
        self.assertIn("deny", self.run_script("hook", stdin="{}").stdout)

    def test_plan_windows_must_name_known_windows(self):
        self.record(status())
        for value in ("", "five-hour", "seven_day,weekly", " , ", "SEVEN_DAY"):
            with self.subTest(value=value):
                result = self.run_script("check", extra_env={"KEYTURN_PLAN_WINDOWS": value})
                self.assertEqual(result.returncode, 1)
                self.assertIn("KEYTURN_PLAN_WINDOWS must name", result.stdout)


if __name__ == "__main__":
    unittest.main()
