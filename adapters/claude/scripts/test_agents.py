"""Checks the Claude Code adapter's subagent definitions and permission settings.

`claude plugin validate --strict .` checks that the definitions load. These tests
check what it does not: that every definition is listed in `plugin.json`, that a
preloaded skill is named the only way that loads keyturn's own skill, and that
each subagent's tools are the ones ADR 0035 gives it.
"""

import json
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parent.parent
ROOT = ADAPTER.parent.parent
AGENTS = ADAPTER / "agents"

FILE_TOOLS = ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]
TOOLS = {
    "pm": FILE_TOOLS + ["Agent", "Skill"],
    "architect": FILE_TOOLS + ["Agent", "Skill"],
    "standards": FILE_TOOLS,
    "developer": FILE_TOOLS,
    "qa": FILE_TOOLS,
    "security": FILE_TOOLS,
    "reviewer": FILE_TOOLS,
    "pm-delivery": FILE_TOOLS,
}
SKILLS = {
    "pm": ["keyturn:spec"],
    "architect": ["keyturn:design"],
    "standards": ["keyturn:conventions"],
    "developer": ["keyturn:implement"],
    "qa": ["keyturn:qa"],
    "security": ["keyturn:security-review"],
    "reviewer": ["keyturn:review"],
    "pm-delivery": [],
}


def frontmatter(path):
    """Returns the frontmatter's fields: strings, and lists for `- item` lines."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path.name}: no frontmatter")
    fields, key = {}, None
    for line in lines[1:]:
        if line == "---":
            return fields
        if line.startswith("  - ") and key is not None:
            fields.setdefault(key, []).append(line[4:].strip())
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if value.strip():
            fields[key] = value.strip()
    raise ValueError(f"{path.name}: frontmatter not closed")


class AgentDefinitions(unittest.TestCase):
    def setUp(self):
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.listed = manifest.get("agents", [])

    def test_every_definition_is_listed_and_every_listed_file_exists(self):
        on_disk = sorted(f"./adapters/claude/agents/{p.name}" for p in AGENTS.glob("*.md"))
        self.assertEqual(sorted(self.listed), on_disk)
        self.assertEqual(sorted(p.stem for p in AGENTS.glob("*.md")), sorted(TOOLS))

    def test_fields(self):
        for path in sorted(AGENTS.glob("*.md")):
            with self.subTest(agent=path.stem):
                fields = frontmatter(path)
                self.assertEqual(fields.get("name"), path.stem)
                self.assertTrue(fields.get("description"))
                self.assertIn(fields.get("model"), {"opus", "sonnet"})
                tools = [t.strip() for t in fields.get("tools", "").split(",") if t.strip()]
                self.assertEqual(tools, TOOLS[path.stem])
                self.assertNotIn("disallowedTools", fields)

    def test_skills_are_namespaced_and_exist(self):
        for path in sorted(AGENTS.glob("*.md")):
            with self.subTest(agent=path.stem):
                skills = frontmatter(path).get("skills", [])
                self.assertEqual(skills, SKILLS[path.stem])
                for name in skills:
                    plugin, _, skill = name.partition(":")
                    self.assertEqual(plugin, "keyturn", "a bare name can load another skill")
                    self.assertTrue((ROOT / "skills" / skill / "SKILL.md").is_file(), name)


class PermissionSettings(unittest.TestCase):
    def setUp(self):
        self.settings = json.loads((ADAPTER / "permission-settings.json").read_text(encoding="utf-8"))

    def test_only_deny_rules(self):
        self.assertEqual(list(self.settings), ["permissions"])
        self.assertEqual(list(self.settings["permissions"]), ["deny"])
        deny = self.settings["permissions"]["deny"]
        self.assertEqual(len(deny), len(set(deny)))
        self.assertTrue(all(rule.startswith("Bash(") and rule.endswith(")") for rule in deny))

    def test_every_push_is_denied(self):
        self.assertIn("Bash(git push *)", self.settings["permissions"]["deny"])

    def test_the_pull_request_commands_are_denied_so_the_scripts_are_the_only_way(self):
        # ADR 0041: agents push, open, and post only through keyturn's scripts in github/scripts/; and ADR 0044:
        # a closed pull request is never reopened outside them.
        deny = self.settings["permissions"]["deny"]
        for command in ("merge", "create", "edit", "ready", "close", "review", "comment", "reopen", "update-branch", "lock"):
            self.assertIn(f"Bash(gh pr {command} *)", deny)
        # ADR 0045: gh api would post on the pull request around post_findings.py.
        self.assertIn("Bash(gh api *)", deny)
        # A pull request is also an issue, an alias could name gh api, and the token reaches the API without gh.
        for rule in ("Bash(gh issue comment *)", "Bash(gh alias set *)", "Bash(gh auth token*)"):
            self.assertIn(rule, deny)


if __name__ == "__main__":
    unittest.main()
