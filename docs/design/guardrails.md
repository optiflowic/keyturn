# Guardrails

Agents must not run out of control. Guardrails work in layers, so that no single failure lets an agent cause serious harm.

## 1. Agents cannot weaken their own checks

The most likely failure is not malice but an agent "making the checks pass" instead of fixing the problem. The gate detects this mechanically and fails the change:

- Changes by the developer to protected paths: gate scripts, stack profiles, the CI jobs that run the gates, linter configs, conventions, and tests written by QA (other CI/CD work is allowed when the approved requirements include it). QA's tests live in their own folders, named in the design and kept out of the areas the developer may change, so that the path alone protects them; the developer's own unit tests stay in the developer's areas. See [ADR 0017](../adr/0017-qa-tests-in-their-own-folder.md).
- New suppression comments (e.g., `//nolint`, `eslint-disable`, `# nosec`, `#[allow(...)]`) without an approved decision record
- A drop in the number of tests or in coverage
- Skipped or disabled tests

## 2. Scope is limited to what was approved

- The developer works only on what the approved requirements and design cover.
- The gate compares the changed files with the areas listed in the design and flags changes outside them.
- Some changes always require client approval before they are made: new external services, changes to authentication, authorization, or data handling, and anything that deletes data. New dependencies require it according to their kind.
- Which dependencies need that approval depends on their kind. The language toolchain and standard library are covered by approving the stack. The gate's scanners are installed by the gate and never added to the project. Development tools the stack profile names (linters, formatters, test tools that are not part of the deliverable) are approved by the profile, and the client sees them in the design summary for information only. Everything else, including every runtime library and any tool no profile names, needs the client's approval. See [ADR 0015](../adr/0015-dependency-kinds.md).

## 3. New dependencies are checked

AI agents sometimes suggest packages that do not exist or that imitate popular ones. Every new direct dependency is checked for existence, maintenance status, known vulnerabilities, and license, and the result is recorded. This includes the development tools approved by the stack profile: not needing the client's approval never means skipping the check. The design lists only direct dependencies, including the peer dependencies they require; indirect ones are fixed by the lock file, which is always committed, and checked for known vulnerabilities by the gate's dependency scan, whose result, indirect dependencies included, is in the delivery report. Until the gate has a dependency scan, nothing checks the indirect dependencies, and the delivery report lists them under "What was not verified". See [ADR 0018](../adr/0018-direct-dependencies-in-the-design.md).

## 4. The environment limits the damage

- Agents run in a sandbox (container or the tool's sandbox mode) with only the access they need.
- No production credentials. Network access is limited to what the task needs.
- Destructive commands and direct pushes to the default branch are blocked.

These are safety guardrails that must always be on, so unlike quality gates they **are** enforced with each tool's own mechanisms (permission rules, sandbox settings, and hooks). The adapters ship recommended settings for each tool.

During the MVP ([Phases](phases.md#mvp), [ADR 0025](../adr/0025-mvp-first.md)), agents run without a sandbox: the adapter ships only permission rules that block direct pushes to the default branch and destructive commands, and network access and credentials are limited only by how the person runs it. Every delivery report made during that time says so under "What was not verified".

## 5. Budgets and escalation

- Every task has limits: rework count, token budget, time, and number of changed files.
- When a limit is reached, or the agent is unsure (ambiguous requirements, conflicting constraints), it stops and asks the client instead of guessing.

### Subscription usage limits

When keyturn runs on a subscription plan, it must not use up the plan's usage windows.

- Claude Code exposes plan usage to the status line as `rate_limits.five_hour` and `rate_limits.seven_day` (`used_percentage`, `resets_at`) on Pro and Max plans.
- A status line script writes these values to a local file. keyturn reads the file:
  - **Soft stop (default 80%)**: the pipeline does not start a new step. The current state is saved (see [Resuming Work](resuming-work.md)) so work can resume after `resets_at`.
  - **Hard stop (default 90%)**: a safety hook blocks further tool calls, in case a single step runs long.
- Both thresholds apply to the 5-hour and the 7-day window, and are configurable.
- A person can release a stop until the window resets, by running a command themselves; the next window stops again at the same limits. A release of the hard stop lets that window be used up. The safety hook denies the plain ways an agent could try to release its own stop through a tool ([ADR 0023](../adr/0023-releasing-usage-stops.md)).
- Some plans have no 5-hour window. A window counts as one the plan does not have only when a person says so in a setting, never because the value is missing: a missing window may only mean it has not arrived yet. A value that is sent still counts ([ADR 0024](../adr/0024-windows-a-plan-has-are-a-setting.md)).
- Things to verify during implementation: the values only appear after the first API response in a session, and may not be available in headless runs (`claude -p`) or subagents. If the value is missing, keyturn must treat it as unknown and stop at step boundaries rather than assume there is room.
- Codex needs its own usage source; until one is available, the Codex adapter relies on the task budgets above.

## 6. Everything is traceable

Every action leaves a record: commits, PRs, comments, gate logs, and decision records. The delivery report lists any guardrail that was triggered during the task, and the models and tool versions that were used.
