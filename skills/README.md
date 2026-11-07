# Skills

Each role's procedure lives here as `skills/<name>/SKILL.md`, written to the [Agent Skills](https://agentskills.io) open standard so the same file works in Claude Code and Codex.

- Frontmatter uses only `name` and `description`.
- A skill says what a role does (inputs, procedure, outputs). Who runs it is defined per tool in `adapters/`.

See "Architecture" in [`docs/DESIGN.md`](../docs/DESIGN.md) and [ADR 0005](../docs/adr/0005-repository-root-as-plugin-root.md).
