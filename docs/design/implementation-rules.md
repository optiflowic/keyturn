# Implementation Rules

- Follow the readability principle ([Design Principles](principles.md) 3) in all code, including keyturn's own scripts.
- Skill frontmatter uses only `name` and `description`, for portability across tools.
- `AGENTS.md` and each `SKILL.md` stay within their size limits, which a test checks ([ADR 0071](../adr/0071-size-limits-for-agents-md-and-skills.md)). Reword before adding a condition, and put steps a role rarely takes in the skill's `references/`.
- Do not build a generator for subagent definitions until the set of roles is stable.
