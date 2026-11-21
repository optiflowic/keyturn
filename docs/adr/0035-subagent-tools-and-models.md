# 0035. Each role's subagent preloads its skill, and gets only the file tools and the shell, on a model set by its tier

- Status: accepted
- Date: 2026-11-21

## Context

`deliver` runs every role in a context of its own, and leaves who runs it to each tool's adapter ("Separate the 'what' from the 'who'" in `docs/design/architecture.md`). For Claude Code, that is a subagent definition in `adapters/claude/agents/`, listed in `plugin.json` ([ADR 0020](0020-tool-specific-files-in-adapters.md)). The roles that run in a context of their own are the seven role skills (`spec`, `design`, `conventions`, `implement`, `qa`, `security-review`, `review`) and the last step of `deliver`, which writes the acceptance guide and the delivery report ([ADR 0033](0033-delivery-documents-from-the-records.md)).

Each definition has to say three things: how the subagent gets its skill, which tools it may use, and which model it runs on. What constrains the answer:

- A subagent without a `tools` list inherits every tool of the session, including web access and any MCP server's tools (for example, one that can push to GitHub or merge a pull request).
- `tools` takes tool names only. It cannot limit a tool to some paths or commands: a reviewer that may write its report may write any file. What a role may change is limited by its skill's rules, by the checks `deliver` makes after each step, and by the gate.
- Claude Code ignores `hooks`, `mcpServers`, and `permissionMode` in a plugin's subagents. Permission rules from the person's settings, and the plugin's hooks, still apply inside them.
- A skill is preloaded with `skills`. Tried with Claude Code 2.1.323 (`claude -p` with the plugin loaded from a working copy): a subagent preloads a plugin's skill only under its namespaced name (`keyturn:review`), and then also gets the skill's folder, which the skill's relative paths need. The bare name `review` loaded Claude Code's own `/review` command instead. A subagent started as the main session (`claude --agent keyturn:reviewer`) did not preload it at all.
- `spec` and `design` translate with the `localize` skill in English-only mode, and `localize` asks for a context that has not seen the original for a back-translation. Tried the same way: a plugin subagent with `Agent` in its `tools` started a subagent of its own.
- `deliver` names no subagent: who runs a role is the adapter's ("Separate the 'what' from the 'who'"). Claude Code chooses a subagent for a task by its `description`.
- "Model Tiers" in `docs/design/model-tiers.md`: lower-tier models for well-defined work (implementation of a clear design, test writing), higher-tier models for what needs judgment (requirements, design, and reviews).

## Options considered

1. **Each subagent preloads its one skill by its namespaced name, and gets the file tools and the shell (`Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`) and nothing else; `pm` and `architect` also get `Skill` and `Agent`, for `localize` (and `Skill` for `project-config`). The model follows the role's tier.** Every role can read, write its outputs, run the skills' scripts and Git, and commit, which every role does. No role has a web tool or an MCP server's tools, or can hand its work to another agent, except for the translation the two document roles need. (The shell can still reach the network; the architect checks dependencies through it.)
2. **No `tools` list: every subagent inherits the session's tools.** Nothing a role might need is missing, but a role gets web access and every MCP tool the person has, which no role needs and which widen what a prompt injection in the reviewed code or a document can do.
3. **Read-only tools for the reviewing roles (`security`, `reviewer`): no `Edit`, `Write`, or `Bash`.** They could not change code, but they could not write and commit their reports, run Git to read the range, or run the scripts their skills use either: the skills need the shell.
4. **The skill read through the `Skill` tool instead of preloaded.** Works without depending on how `skills` resolves names, but the subagent would have to choose to load it first, and every role would get `Skill`, which can load any other skill.

## Decision

Option 1. The definitions are:

| Subagent | Runs | Tools | Model |
|---|---|---|---|
| `pm` | `spec` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `Agent`, `Skill` | `opus` |
| `architect` | `design` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `Agent`, `Skill` | `opus` |
| `standards` | `conventions` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` | `sonnet` |
| `developer` | `implement` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` | `sonnet` |
| `qa` | `qa` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` | `sonnet` |
| `security` | `security-review` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` | `opus` |
| `reviewer` | `review` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` | `opus` |
| `pm-delivery` | the last step of `deliver` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` | `opus` |

Each of the first seven preloads its skill as `keyturn:<skill>`. `pm-delivery` preloads none: `deliver` gives it everything it writes from. `pm` and `architect` use `Skill` only for `localize` and `project-config`, and `Agent` only where `localize` asks for a context of its own.

## Reasons

- Every role commits its outputs and runs scripts, so the shell is the one tool no role can do without; leaving out the rest of the session's tools is what keeps a role from reaching outside the repository through a tool, while the sandbox is not there yet (`docs/design/guardrails.md` 4).
- A role cannot spawn another agent, so its work stays in the context `deliver` started, with only what `deliver` gave it, as "Each role in its own context" requires. The exception is the translation, which needs a context of its own by the `localize` skill's rules.
- Preloading puts the whole skill in the context before the first turn, so the role follows the procedure from the start, without a tool it might skip. The namespaced name is the only one that loads keyturn's skill.
- Requirements, design, and the two reviews need judgment; implementation of an approved design, tests from the requirements, and conventions from a stack profile are well defined (`docs/design/model-tiers.md`). The client documents are what the client decides from, so they get the higher tier too.

## Consequences

- The paths a role may change are not limited by its tools. A role that writes outside its outputs is caught by the checks `deliver` makes after each step and by the gate, not stopped before the write; the sandbox (enhancement, #119) is what can stop it.
- The shell gives every role network access through commands (for example, `curl`, or installing a dependency). The minimal permission rules ([ADR 0036](0036-minimal-permission-rules.md)) block pushes and destructive commands, not the network.
- The model is fixed per role in the plugin. `deliver` (or a person) can still pass another model when it starts a subagent; making the model a per-project setting, and recording usage per role (`docs/design/model-tiers.md`), are left for after the MVP. On a Pro plan, the `opus` roles use the windows faster; the usage limits still stop the run before they are used up.
- Roles must be run as subagents, not as the main session with `claude --agent`, or their skill is not loaded.
- Each description names the step of `deliver` it is for, and says to start it rather than a general-purpose subagent. That is how `deliver` gets the right one; whether it always does is checked in the end-to-end run (#63). A general-purpose subagent in its place would have every tool and no preloaded skill.
- The subagent `pm` or `architect` starts for a translation is not one of these definitions, so it may have every tool of the session, web and MCP tools included, while it reads the client's words. Until the translation subagent (#119) exists, that is a known gap.
- Using a skill other than `localize` and `project-config` through `Skill`, or a translation on a lower-tier model, is not given to these roles: forward translations in `spec` and `design` run on their model until #119.
- The translation subagent (#119) and the Codex adapter's definitions (phase 10) follow the same rules when they are added.
