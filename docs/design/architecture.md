# Architecture

## Separate the "what" from the "who"

- **Skills (SKILL.md) = what a role does**: inputs, procedure, and outputs. Written to the Agent Skills open standard (agentskills.io) so they work across tools.
- **Subagents = who runs it**: a thin definition that runs a skill in its own context. This is the only part written per tool.
  - Claude Code: Markdown (agents/*.md)
  - Codex: TOML (.codex/agents/*.toml)
- On tools without subagents, run the skill in a separate process (e.g., `claude -p`, `codex exec`) to keep contexts separate.

## Agent instruction files

- `AGENTS.md` is the only committed instructions file, in this repository and in every project keyturn works on.
- Tools that look for a different file name (e.g., `CLAUDE.md` for Claude Code) get a **local symbolic link** to `AGENTS.md`, created by each user for the agent they use and excluded from Git with `.git/info/exclude`. Committed files stay free of tool-specific names.
- Each adapter's setup step creates the link and the exclude entry for its tool, so users do not have to do it by hand.

## Gates

- Quality gates are not implemented as hooks (safety guardrails are; see [Guardrails](guardrails.md)). Plugin hooks are always active once the plugin is enabled, which would interfere with standalone use and manual work. The pipeline skill (`deliver`) calls `gates/gate.sh` explicitly, and so does CI.
- `gate.sh` is a plain CLI that does not depend on Claude Code or Codex.
- It reads the stack profile to decide which checks to run.
- It checks whether external tools are installed and explains how to install them if not.
