# 0005. Repository root as the plugin root

- Status: accepted
- Date: 2026-11-08

## Context

keyturn is distributed as a Claude Code plugin first and as a Codex plugin later (phase 10). Both tools must load the same skills from `skills/`, because skills are the shared, tool-neutral part (see "Architecture" in `docs/DESIGN.md`).

The tools put these constraints on the layout:

- Claude Code reads `.claude-plugin/plugin.json` at the plugin root. Every other plugin file (`skills/`, `hooks/`, and so on) must also be at the plugin root. Component paths in the manifest must start with `./` and stay inside the plugin root.
- When Claude Code installs a plugin from a marketplace, it copies only the plugin directory into its cache. Files outside the plugin directory, such as `../skills`, are not available to the installed plugin.
- The marketplace definition lives in `.claude-plugin/marketplace.json` at the repository root. A plugin entry may use `"source": "./"` for a plugin at the repository root.
- Codex reads a portable plugin manifest from `plugin.json` at the plugin root and discovers skills from the root `skills/` directory. Codex also reads skills from `.agents/skills/` in a repository.

The initial layout in `docs/DESIGN.md` placed `plugin.json` in `adapters/claude/`, which these constraints do not allow while `skills/` stays at the repository root.

## Options considered

1. **The repository root is the plugin root**: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` at the root, with `"source": "./"`. `skills/` sits at the root where both tools look for it. The installed copy also contains docs and other files the plugin does not need, which costs some disk space but nothing else.
2. **The plugin root is `adapters/claude/`**: matches the initial layout, but `skills/` would have to move under `adapters/claude/` or be reached through a symbolic link. Moving it ties the shared skills to one tool. Links that leave the plugin directory are not copied on install.
3. **A build step that assembles a plugin directory**: keeps the source layout free, but adds a generated directory to keep in sync, and a step that can be forgotten. Too much machinery for one plugin.

## Decision

The repository root is the plugin root for Claude Code (option 1), and later for Codex. `plugin.json` and `marketplace.json` live in `.claude-plugin/` at the root.

## Reasons

- `skills/` stays in one place and is read directly by both tools, with no copies, links, or build step.
- It is the layout both tools document for a plugin that lives in its own repository.
- The extra files in the installed copy are harmless; the plugin only loads what is in its component directories.

## Consequences

- `adapters/claude/` holds only Claude Code specific files: subagent definitions and recommended permission settings. Claude Code does not scan it on its own, so phase 3 lists each `adapters/claude/agents/*.md` file in the `agents` field of `plugin.json` (the field accepts files, not directories).
- The plugin has a `version` in `plugin.json`. Installed copies update only when it is bumped, so a release that changes a skill must bump it.
- The Codex adapter (phase 10) adds a root `plugin.json` for Codex next to `.claude-plugin/`. Using skills inside this repository from Codex, without installing the plugin, would need `.agents/skills/` pointing at `skills/`; that is decided in phase 10.
- The marketplace and the plugin are both named `keyturn`, so the plugin installs as `keyturn@keyturn`.
