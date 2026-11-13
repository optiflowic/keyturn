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

    def run_script(self, *args: str, stdin: str = "", now: float = NOW) -> subprocess.CompletedProcess:
        env = dict(os.environ, KEYTURN_USAGE_FILE=str(self.file))
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
        self.assertEqual(saved["windows"]["five_hour"], {"used_percentage": 42.0, "resets_at": NOW + 2 * HOUR})

    def test_statusline_without_rate_limits_records_nothing_known(self):
        result = self.run_script("statusline", stdin=json.dumps({"workspace": {}}))
        self.assertEqual(result.stdout.strip(), "usage: unknown")
        self.assertEqual(json.loads(self.file.read_text())["windows"], {})

    def test_statusline_never_fails_on_bad_input(self):
        result = self.run_script("statusline", stdin="not json")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "usage: unknown"))

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

    def test_limits_must_be_percentages(self):
        result = self.run_script("check", "--soft", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a percentage", result.stderr)


if __name__ == "__main__":
    unittest.main()
