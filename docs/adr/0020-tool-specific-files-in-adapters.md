# 0020. Everything one tool uses lives in its adapter folder; files the tool needs at the plugin root stay thin

- Status: accepted
- Date: 2026-11-15
- Supersedes: [0005](0005-repository-root-as-plugin-root.md), only its consequence on what `adapters/claude/` holds

## Context

[ADR 0005](0005-repository-root-as-plugin-root.md) makes the repository root the plugin root, and says, as a consequence, that `adapters/claude/` holds only Claude Code specific files: subagent definitions and recommended permission settings.

The usage limits ("Subscription usage limits" in `docs/DESIGN.md`) need more than that from Claude Code: a script that records the plan's usage from the status line and answers whether a step may start, its tests, and a PreToolUse hook that stops tool calls at the hard limit. The script and its tests are used only with Claude Code. The hook must be declared in `hooks/hooks.json` at the plugin root, because Claude Code reads plugin hooks only from there, and ADR 0005 keeps the repository root as the plugin root.

The question is where tool-specific scripts go, and how files that a tool requires at the plugin root relate to `adapters/<tool>/`.

## Options considered

1. **Everything one tool uses goes in `adapters/<tool>/`, including scripts and their tests; files the tool requires at the plugin root stay at the root, are kept thin, and call the scripts in `adapters/<tool>/`.** One place to look for each tool's parts, and the shared parts stay free of them. The root gets a few small tool-specific files that the tool requires there.
2. **Tool-specific scripts go in `scripts/` at the root.** `scripts/` is for developing keyturn, not for what an installed plugin runs (`AGENTS.md`, "Where things live"), so it would mix the two and blur the version rule.
3. **Tool-specific scripts go next to the hook, in `hooks/`.** Keeps the hook and its code together, but `hooks/` is Claude Code's, so another tool's parts would need another root folder, and each tool's parts would be spread across the root.

## Decision

Option 1. `adapters/<tool>/` holds everything that only that tool uses: subagent definitions, permission settings, and scripts with their tests (in `adapters/<tool>/scripts/`). A file that a tool requires at the plugin root (for Claude Code, `hooks/hooks.json`) stays at the root, holds only what the tool needs to find the work, and calls a script in `adapters/<tool>/` for the work itself. This replaces only ADR 0005's consequence on what `adapters/claude/` holds; the repository root stays the plugin root.

## Reasons

- Each tool's parts are in one folder, so adding or removing a tool touches that folder and the few root files the tool requires.
- Keeping the root files thin means their behavior is in a script that has tests, not in configuration that has none.
- `scripts/` keeps its meaning: tools for developing keyturn, which no installed plugin runs.

## Consequences

- ADR 0005 stays accepted for the plugin root; its status line points here for what `adapters/claude/` holds.
- `adapters/claude/` holds `scripts/usage.py` and its tests, and `hooks/hooks.json` calls it.
- The "Repository Layout" in `docs/DESIGN.md` lists `hooks/` and `adapters/<tool>/scripts/`, and "Where things live" in `AGENTS.md` says the same.
- A script in `adapters/<tool>/scripts/` is something an installed plugin runs, so changing it follows the plugin version rule in `AGENTS.md`.
- The Codex adapter (phase 10) follows the same rule for whatever Codex requires at the plugin root.
