"""Size limits of the files every session or every role run loads (ADR 0071).

Run from the repository root: python3 -m unittest discover -s scripts

AGENTS.md is loaded into every session, and a role's SKILL.md into every run of that role.
A file over its limit fails here. Before raising a limit, reword what is there, or move what
only some sessions need out of the file (AGENTS.md "Keeping this file current").
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENTS_MD_LIMIT = 20_000
SKILL_MD_LIMIT = 30_000

# Until #208 shrinks them: each skill's size on 2026-11-28 plus 5,000 bytes, rounded up to
# the next 1,000. Lower an entry as its skill shrinks, and remove it once the skill is at
# SKILL_MD_LIMIT or less. Raise one only with the reason in the pull request.
INTERIM_SKILL_MD_LIMITS = {
    "deliver": 108_000,
    "design": 66_000,
    "qa": 50_000,
    "security-review": 48_000,
    "review": 40_000,
    "resume": 38_000,
    "spec": 36_000,
}


def size_in_bytes(path: Path) -> int:
    return len(path.read_bytes())


def skill_files() -> dict[str, Path]:
    return {path.parent.name: path for path in sorted(ROOT.glob("skills/*/SKILL.md"))}


def skill_limit(name: str) -> int:
    return INTERIM_SKILL_MD_LIMITS.get(name, SKILL_MD_LIMIT)


class DocSizeTest(unittest.TestCase):
    def test_agents_md_is_within_its_limit(self):
        size = size_in_bytes(ROOT / "AGENTS.md")
        self.assertLessEqual(
            size,
            AGENTS_MD_LIMIT,
            f"AGENTS.md is {size} bytes, over its limit of {AGENTS_MD_LIMIT}",
        )

    def test_each_skill_md_is_within_its_limit(self):
        skills = skill_files()
        self.assertTrue(skills, "no skills/*/SKILL.md found")
        for name, path in skills.items():
            with self.subTest(skill=name):
                size = size_in_bytes(path)
                limit = skill_limit(name)
                self.assertLessEqual(
                    size,
                    limit,
                    f"skills/{name}/SKILL.md is {size} bytes, over its limit of {limit}",
                )

    def test_interim_limits_name_existing_skills_and_stay_above_the_final_limit(self):
        skills = skill_files()
        for name, limit in INTERIM_SKILL_MD_LIMITS.items():
            with self.subTest(skill=name):
                self.assertIn(name, skills, f"interim limit for a skill that does not exist: {name}")
                self.assertGreater(
                    limit,
                    SKILL_MD_LIMIT,
                    f"the interim limit for {name} is not above {SKILL_MD_LIMIT}: remove the entry",
                )


if __name__ == "__main__":
    unittest.main()
