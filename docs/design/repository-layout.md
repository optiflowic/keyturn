# Repository Layout (initial)

```
.claude-plugin/
  plugin.json             # Claude Code plugin manifest (the repository root is the plugin root)
  marketplace.json        # Claude Code marketplace definition
skills/                   # role procedures (shared across tools)
  spec/SKILL.md           # PM: requirements and acceptance criteria
  design/SKILL.md         # architect: design, decisions, threat model
  conventions/SKILL.md    # standards: conventions and tool rules
  implement/SKILL.md      # developer
  qa/SKILL.md             # QA: tests from the specification
  review/SKILL.md         # review against design and readability rules
  security-review/SKILL.md # security review against the threat model
  localize/SKILL.md       # local translation for the client (never committed)
  project-config/SKILL.md # create and check the project configuration
  deliver/SKILL.md        # full pipeline
  resume/SKILL.md         # resume a stopped task from its state file
gates/
  gate.sh                 # runs checks defined by the stack profile (the logic is in gate.py, tested by test_gate.py)
                          # plus guardrail checks (protected paths, suppressions, scope)
profiles/                 # stack profiles (one frontend + one backend first)
templates/
  client/                 # requirements, design summary, test report, acceptance guide, delivery report, decision card, approvals
  internal/               # design, design answers, decisions, handoff, test report, review, task state
hooks/
  hooks.json              # Claude Code plugin hooks (must be at the plugin root); thin, they call adapters/claude/scripts/
adapters/                 # everything only one tool uses (ADR 0020)
  claude/                 # agents/*.md (listed in plugin.json), recommended permission settings
    scripts/              # scripts only Claude Code uses (for example, the usage limits), with their tests
  codex/                  # agents/*.toml, recommended sandbox settings, scripts/
github/                   # scripts that push the task branch, open the pull request, post the reviews, merge, and watch;
                          # workflow templates, the one-time repository setup, labels, project setup
evals/
  requests/               # evaluation requests
scripts/                  # tools for developing keyturn (not run by skills), with their tests
docs/
  DESIGN.md               # index of the design
  design/                 # the design, one file per section
  adr/                    # keyturn's own decision records
  pre-pr-checklist.md     # what the review before a pull request checks
AGENTS.md
README.md
LICENSE                   # MIT
.gitignore                # includes .keyturn/ (local translations and maintainer notes)
```

In a Claude Code plugin, only the manifests go inside `.claude-plugin/`; `skills/`, `hooks/`, etc. must be at the plugin root. The repository root is the plugin root, so `skills/` is shared by Claude Code and Codex. See [ADR 0005](../adr/0005-repository-root-as-plugin-root.md). A file a tool requires at the plugin root, such as `hooks/hooks.json`, stays thin and calls a script in `adapters/<tool>/scripts/` ([ADR 0020](../adr/0020-tool-specific-files-in-adapters.md)).
