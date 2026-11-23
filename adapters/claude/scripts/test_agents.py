"""Checks the Claude Code adapter's subagent definitions and permission settings.

`claude plugin validate --strict .` checks that the definitions load. These tests
check what it does not: that every definition is listed in `plugin.json`, that a
preloaded skill is named the only way that loads keyturn's own skill, and that
each subagent's tools are the ones ADR 0035 gives it.
"""

import fnmatch
import json
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parent.parent
ROOT = ADAPTER.parent.parent
AGENTS = ADAPTER / "agents"
PLUGIN = "<path to the keyturn plugin>"  # the placeholder the person replaces, as in statusline-settings.json

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

    def test_only_allow_and_deny_rules(self):
        self.assertEqual(list(self.settings), ["permissions"])
        self.assertEqual(list(self.settings["permissions"]), ["allow", "deny"])
        for kind in ("allow", "deny"):
            rules = self.settings["permissions"][kind]
            self.assertEqual(len(rules), len(set(rules)), kind)
            self.assertTrue(all(rule.startswith(("Bash(", "Edit(", "Write(")) and rule.endswith(")") for rule in rules))

    def test_only_the_github_scripts_are_allowed_by_their_full_path(self):
        # ADR 0052: auto mode judges every command no allow rule matches, and denied task_branch.py (#155). Each rule
        # names one script by the plugin's path, with no wildcard in the path, so a script of the same name elsewhere
        # does not match.
        self.assertEqual(self.settings["permissions"]["allow"], [
            f"Bash(python3 {PLUGIN}/github/scripts/{script} *)"
            for script in ("task_branch.py", "post_findings.py", "merge.py")])
        for rule in self.settings["permissions"]["allow"]:
            path = rule[len("Bash(python3 "):-len(" *)")]
            self.assertNotIn("*", path)
            self.assertTrue((ROOT / path.replace(PLUGIN + "/", "")).is_file(), path)

    def test_the_rules_filled_in_with_a_path_match_the_scripts_and_the_folder_only(self):
        # The person replaces the placeholder with an absolute path (ADR 0052): the Bash rules must then match the
        # scripts there only, and the Edit and Write rules must become absolute ("//"), not relative to the settings file.
        sample = "/Users/me/keyturn"
        allow = [rule.replace(PLUGIN, sample)[len("Bash("):-1] for rule in self.settings["permissions"]["allow"]]
        deny = [rule.replace(PLUGIN, sample) for rule in self.settings["permissions"]["deny"] if PLUGIN in rule]
        def allowed(command):
            return any(fnmatch.fnmatchcase(command, pattern) for pattern in allow)
        for script in ("task_branch.py", "post_findings.py", "merge.py"):
            self.assertTrue(allowed(f"python3 {sample}/github/scripts/{script} delivery-1"), script)
            self.assertFalse(allowed(f"python3 /tmp/keyturn/github/scripts/{script} delivery-1"), script)
        self.assertFalse(allowed(f"python3 {sample}/gates/gate.sh --task delivery-1"))
        # The rules match the text: the same script by a path with ".." does not match, so deliver writes the resolved path.
        self.assertFalse(allowed(f"python3 {sample}/skills/deliver/../../github/scripts/task_branch.py push delivery-1"))
        self.assertEqual(sorted(deny), [f"Edit(/{sample}/**)", f"Write(/{sample}/**)"])
        self.assertTrue(all(rule.split("(", 1)[1].startswith("//") for rule in deny))

    def test_edits_under_the_plugin_folder_are_denied(self):
        # ADR 0052: an allowed script is only as safe as the script, so the file tools (and the shell writes Claude Code
        # checks against these rules) cannot change it. "/" before the path makes it absolute ("//...").
        deny = self.settings["permissions"]["deny"]
        for tool in ("Edit", "Write"):
            self.assertIn(f"{tool}(/{PLUGIN}/**)", deny)

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
        for rule in ("Bash(gh issue comment *)", "Bash(gh alias set *)"):
            self.assertIn(rule, deny)

    def test_the_commands_that_change_credentials_variables_secrets_and_workflows_are_denied(self):
        # ADR 0048: agents run with the agents' token alone, and the detecting workflow, its variables, and its runs
        # stay out of their reach; gh auth token would also hand the token to a command that is not gh.
        patterns = [rule[len("Bash("):-1] for rule in self.settings["permissions"]["deny"] if rule.startswith("Bash(")]
        for command in ("gh auth", "gh auth token", "gh auth login --with-token", "gh auth switch --user someone",
                        "gh auth refresh -s workflow", "gh auth status", "gh variable set KEYTURN_VOUCHED --body x",
                        "gh variable list", "gh secret set TOKEN", "gh workflow disable keyturn-watch.yml",
                        "gh workflow run keyturn-watch.yml", "gh run delete 1", "gh run cancel 1", "gh run rerun 1"):
            self.assertTrue(any(fnmatch.fnmatchcase(command, pattern) for pattern in patterns), command)

    def test_the_os_credential_store_is_denied(self):
        # The maintainer reads the agents' token from the credential store before starting the session; the agents never
        # need it, and the maintainer's own credentials are there too (#119). It stops the plain command only.
        patterns = [rule[len("Bash("):-1] for rule in self.settings["permissions"]["deny"] if rule.startswith("Bash(")]
        for command in ("security", "security find-generic-password -s keyturn -w", "security dump-keychain"):
            self.assertTrue(any(fnmatch.fnmatchcase(command, pattern) for pattern in patterns), command)


if __name__ == "__main__":
    unittest.main()
