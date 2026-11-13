# keyturn Design Principles

This document describes how keyturn is designed. All implementation work should follow it.

## Concept

keyturn turns AI agents into a contractor team, with the human as the client.

- The client (human) does not read code. They review requirements, acceptance criteria, and reports, and do the final hands-on check themselves.
- The contractor (AI) is a team of role-based agents that handles everything from specification and design to implementation, verification, and delivery.
- Deliverables are not limited to applications. Anything that can be specified, built, and verified is in scope (apps, libraries, editor plugins, CLI tools, infrastructure, documentation, etc.).
- keyturn works on both new projects and existing repositories.
- The name comes from a turnkey contract: the client receives something that works as soon as they "turn the key".

Since the client never reads the code, the consequences of a serious problem in production fall directly on them. **Security and quality assurance are mandatory.** A deliverable ships because it passed mechanical checks, not because an AI said it was fine.

Absolute safety cannot be guaranteed. The goal is to always be able to explain **what was verified and what remains unverified**, and to hand that to the client in a report.

## Design Principles

1. **The client reviews specifications and evidence, not code**
   Review shifts from code to requirements, acceptance criteria, and reports.
2. **Always choose the best practice, and show why**
   For every meaningful decision (architecture, libraries, data model, security approach), consider the alternatives, pick the one that best fits the requirements and the scale of the project, and record the reasoning. "Best" depends on context: a small tool and a multi-tenant service need different designs. Over-engineering is as much a failure as under-engineering.
3. **Readable code is mandatory**
   All code follows the ideas of *The Art of Readable Code*: clear names, simple control flow, small focused functions, and comments that explain why. No unused abstractions or speculative extension points. This applies to keyturn itself and to everything it builds.
4. **Roles hand off work through documents**
   Not through conversation context. Each handoff uses a defined template, which keeps work traceable and limits what each agent needs to read.
5. **The developer and the judges run in separate contexts**
   QA and security run in separate contexts (subagents or separate processes) and never see the developer's reasoning. QA writes tests from the specification only.
6. **Ship/no-ship decisions are mechanical**
   Tests, static analysis, dependency scanning, and secret scanning act as gates. LLMs read the results and fix problems; they do not decide whether something passes.
7. **Rework loops have a limit**
   When the limit is reached, stop and report to the client what could not be resolved. This also keeps costs under control.
8. **Every stack has an explicit definition of "verified"**
   Stacks are supported through stack profiles (see below). Work on a stack without a profile is still possible, but the delivery report must state that gate coverage is limited.
9. **No lock-in to a single AI tool**
   keyturn is meant to work with any AI coding agent. The shared parts follow open conventions (Agent Skills, `AGENTS.md`), and each tool gets a thin adapter. Claude Code and Codex are the first adapters; others can be added the same way.
10. **Autonomy never bypasses the gates**
    Agents may run unattended, but they cannot merge or release anything that has not passed the gates.
11. **Agents cannot change the rules they are judged by**
    The developer cannot weaken gates, conventions, or tests to make its own work pass. See Guardrails.
12. **Work can always be resumed**
    Whatever stops a task (usage limits, a crash, a question to the client, the rework limit), it can be resumed at any time from where it stopped. See Resuming Work.

## Language

There are two different contexts: this repository itself, and the projects that use keyturn.

### This repository

- Everything in the keyturn repository (code, skills, templates, docs, README) is written in English.
- The maintainer reads it in their own language through local translations (see `localize` below). Translations are never committed.

### Projects that use keyturn

- Conversation with the client happens in the client's language.
- **Client-facing documents** are written in the client's language by default.
- **Internal documents** (agent-to-agent) are written in English.
- A project can choose **English-only mode** instead, for example a public OSS project whose published content should all be in English. In this mode, client-facing documents, issues, PRs, and comments are all in English, and the client reads them through local translations.

The language settings are stored per project in keyturn's project configuration, `keyturn/config.json`: the client's language and whether the project uses English-only mode. Every role checks the file with a script before reading it, and stops if it is missing or invalid. Other settings are added by the role that first needs them. See [ADR 0014](adr/0014-project-configuration-in-json.md).

### Local translations (`localize`)

Used for this repository and for projects in English-only mode.

#### Reading: English → client's language

- Translations are generated into a local, git-ignored folder (e.g., `.keyturn/i18n/<lang>/`), mirroring the original paths.
- Each translation records the hash of its source, so it is regenerated when the source changes and stale translations are never shown.
- This works for documents in the repository and for GitHub content (issues, PRs, comments) fetched on demand.
- The client portal shows the client's language by default, with the English original one click away.

#### Writing: client's language → English

- When the client writes in their language (a request, an answer to a question, a comment), agents translate it into English before posting.
- For anything that changes what will be built (requirements, answers to questions), the client confirms the translated meaning before it is posted.
- The client confirms by reading the English translated back into their language, from the English alone, so that a mistranslation shows up in their own language. Requirements are confirmed through their approval (see below), so a request is not confirmed twice. Short replies, thanks, and general comments are posted without a confirmation, so the client is not asked more than needed. The client's original stays local, under `.keyturn/i18n/inbound/`, and only the English is committed or posted. See [ADR 0013](adr/0013-confirming-translations-into-english.md).

#### Approving translated content

Mistranslation in requirements is a real risk, because the client approves what they read in their own language, not the English source.

- Requirements and acceptance criteria are numbered (e.g., `R-3`, `AC-5`), and the numbers are identical in the original and the translation, so every item can be matched 1:1.
- The approval records which translation (by source hash) the client read, in a separate approval file (`approvals.md`), so that recording it does not change the approved document. See [ADR 0008](adr/0008-approval-records-in-a-separate-file.md).
- An approval whose source hash does not match the current document is stale, and the new version needs a new approval.
- So that an unchanged approval stays current in every checkout, client-facing documents are always checked out with LF (`keyturn/client/*.md text eol=lf` in `.gitattributes`), and a hash is recorded only for the committed version. The approved translation is kept, unchanged, next to the current translation, so its links still work. See [ADR 0012](adr/0012-stable-approval-hashes.md).

#### Keeping the cost down

- Translate on demand, when the client opens something, not everything in advance.
- Translate only what the client reads (client-facing documents, PR and issue summaries), not code or internal documents unless asked.
- Use the source hash to skip unchanged files, and retranslate only the changed sections of a changed file.
- Use a small, inexpensive model for translation. Translation is a simple task compared with design or implementation.
- Keep a short glossary per project so terms stay consistent without long context.
- Record translation tokens as a separate role in the cost data.

#### Standalone use

Translation is also a standalone skill (`localize`). It works on any repository, including ones that do not use the rest of keyturn, and it only reads the repository, so it is safe to use from the start.

## Stack Profiles

A stack profile defines what "verified" means for one tech stack. Gates read the profile instead of hard-coding tools.

Each profile defines:

- How to build, run, and test
- Linters and formatters
- Security checks (SAST rules, dependency scanning, secret scanning)
- Recommended project structure and design patterns for different project sizes
- Secure defaults and patterns to avoid
- What cannot be checked mechanically for this stack (this goes into the delivery report as a known gap)

Profiles live in `profiles/<stack>/`. Add one profile at a time, and only after the previous ones work well. Some stacks have much weaker mechanical security checks than others (e.g., Neovim plugins); the profile must say so honestly rather than pretend coverage exists.

### Planned profiles

| Area | Profiles |
|---|---|
| Frontend | React (SPA), Next.js, React Router v7+ |
| Backend | Go, Python, Rust |
| Other | Neovim plugin (Lua), Rust CLI/TUI |

Start with **one frontend profile and one backend profile**, enough to validate new-project mode end to end on a web application (see phase 6 in Phases). Add the rest one at a time.

## Modes

- **New project**: start from a client request. The PM writes requirements from scratch and the architect designs from scratch.
- **Existing repository**: start with onboarding. Agents read the repository and produce internal documents (current architecture, how to build and test, matching stack profile, known gaps) before taking any task. Existing behavior and conventions are treated as the baseline unless a task says otherwise.

New-project mode is built and validated first. Existing-repository mode comes after keyturn has proven itself on new projects.

## Repository Structure

keyturn supports both single-repository and multi-repository projects. Which one to use is a design decision based on the size and nature of the project, not a fixed rule.

### Flow

1. The PM gathers requirements from the client, including the expected size and how the project may grow.
2. The architect decides the repository structure (one repository, a monorepo, or several repositories) and records it as an ADR, with the reasons and the alternatives.
3. keyturn gives the client a short setup guide: the repositories to create, their names, visibility, and the required settings (e.g., branch protection, labels).
4. **The client creates the repositories.** Agents do not create repositories, in line with least privilege.
5. keyturn verifies the setup (access, settings, labels) and reports anything missing before starting work.

### Multi-repository projects

- **One home repository** holds the project-wide documents: requirements, ADRs, the project-wide design, task state, and client-facing reports. It can be the main application repository or a dedicated repository, decided by the architect.
- Each repository holds its own code, its own internal documents, and its own gate.
- **Contracts between repositories** (e.g., API schemas, message formats) are defined in the home repository and versioned. Each repository tests against the contract.
- A task that spans repositories has one issue in the home repository and one pull request per affected repository, linked together. It is delivered only when every pull request passes its gate and the contract tests pass.
- Resuming, cost tracking, and the client portal treat the project as a whole, using the home repository as the entry point.

## Delivery Scope

- **Delivery ends at a merged pull request.** Deployment and release are done by the human.
- keyturn **does** build the CI/CD setup when the requirements ask for it: build and test workflows, deployment workflows, and a deployment runbook (a client-facing document explaining how to deploy and how to roll back).
- keyturn never holds production credentials and never triggers a deployment. Deployment workflows are designed so that a human starts them (e.g., manual approval or a release tag).

## Changing Requirements

Requirements change during development, as in agile development. keyturn treats requirements as a living, versioned document rather than a fixed contract.

- **Stable IDs.** Every requirement and acceptance criterion has an ID (e.g., `R-3`, `AC-5`) that never changes or gets reused. Removed items are marked as removed, not deleted.
- **Traceability.** Tests, design decisions, and deliveries reference the IDs they cover, so a change to one item shows what else is affected.
- **Change requests are issues.** Each change goes through the PM, who updates the requirements and writes an impact summary for the client: what changes, what is affected, and whether it conflicts with existing requirements.
- **Conflicts are surfaced, not resolved silently.** If a new request contradicts an approved requirement, the client decides.
- **History is kept.** requirements.md has a short changelog, and git keeps the full history.
- **Small increments.** Work is delivered in small pieces, which keeps each acceptance check short (see Client attention budget) and makes changes cheaper.

## Documents

All specifications, designs, and reports are Markdown documents. There are two tiers with different goals.

### Client-facing documents

The client reads these to make decisions and to do the final check. They must be easy to read and make it obvious where to look.

| Document | Purpose |
|---|---|
| requirements.md | What will be built and how it will be judged. Each requirement has a priority, Must or Nice to have: the PM proposes it, and the client decides it. The client approves this before work starts. |
| design-summary.md | The main design decisions in plain language, with the reason for each and the alternatives considered. |
| acceptance-guide.md | What the client should check by hand, in priority order, with steps and expected results. |
| delivery-report.md | What was delivered, what was verified, what was not, and the remaining risks. |
| approvals.md | Which version of the requirements the client approved, in which language, identified by the source hash. |
| decision-card.md | One question to the client: the context, the options, a recommendation, and what happens if the client does not answer. |

Writing rules:

- Start with a short summary (3 lines or so) that states the conclusion.
- Put what the client needs to do or decide first, and mark it clearly.
- Mark priority explicitly (e.g., "Must check" / "Optional").
- No code and no unexplained jargon. Write for someone who will not read the code.
- Keep it short. Move details into internal documents and link to them if needed.

### Client attention budget

If the client is asked too often, or given too much at once, they stop reading and start approving blindly, and the whole model fails. Both the number of requests and the size of each request are limited.

- **Batch requests.** Questions and approvals are collected and sent together, not one by one.
- **Keep each request small.** One request should take a few minutes to read. Each question is a short "decision card": the context, the options, a recommendation, and what happens if the client does not answer.
- **Limit "Must check" items.** An acceptance guide has only a few "Must check" items (around five). If a delivery needs more, it is too big and must be split into smaller deliveries.
- **Ask only when it matters.** Low-risk changes that stay within approved requirements do not need extra approval. The changes listed in Guardrails always do.
- **No answer is not consent.** An unanswered card is never decided on the client's behalf, not even with its recommendation. Work that depends on the answer waits and everything else goes on; if nothing else can be done, the task stops with the card as an open question (see Resuming Work). See [ADR 0009](adr/0009-no-answer-is-not-consent.md).
- Track how many requests the client receives and how long they wait, as part of the cost data.

### Internal documents

Agents use these to hand off work. They can be as detailed as needed.

- Design document and threat model
- Architecture decision records (see below)
- Onboarding notes (existing repositories)
- Handoff notes between roles
- Detailed test report (results per acceptance criterion, untested areas)
- Review findings
- Gate logs (raw tool output and summaries)

### Where documents live in a project

Separate the two tiers so the client knows which folder is theirs.

```
keyturn/
  config.json # project configuration (language settings)
  client/     # client-facing documents
  internal/   # agent-to-agent documents
    adr/      # architecture decision records
    state/    # one state file per task (see Resuming Work)
```

When GitHub integration is used, client-facing content also appears in issues and pull requests (see below). The files in the repository remain the source of truth. In a multi-repository project, the project-wide documents live in the home repository (see Repository Structure).

### Architecture decision records

Every meaningful decision is recorded as an ADR, so that the same question is not discussed again and again.

- One decision per file: `adr/NNNN-short-title.md`, with the context, the options considered, the decision, the reasons, and the consequences.
- Each ADR has a status: proposed, accepted, or superseded.
- **Check before deciding.** Before making a decision, every role searches the existing ADRs. If an accepted ADR already covers the question, follow it instead of reconsidering.
- **Change by superseding.** An accepted decision is changed only by a new ADR that explains what changed and links to the one it replaces. ADRs are never edited after acceptance, except to mark them superseded.
- ADRs that need the client's agreement (e.g., a choice that affects cost, scope, or how the client works) are summarized in plain language in `design-summary.md`.
- The reviewer flags changes that contradict an accepted ADR.
- keyturn's own development follows the same rule: its decisions are recorded as ADRs in `docs/adr/`.

## Roles

### Phase 1 roles

| Role | Skill | Input | Output |
|---|---|---|---|
| PM | spec | Client request | requirements.md (client), acceptance criteria |
| Architect | design | requirements.md, stack profile | Design document, decision records, threat model, design-summary.md (client) |
| Standards | conventions | Stack profile, design document | conventions.md, linter and formatter configs, custom rules |
| Developer | implement | requirements.md, design document, conventions | Deliverable, handoff notes |
| QA | qa | requirements.md (never the implementation) | Tests, detailed test report |
| Security | security-review | Threat model, git diff, gate scan results | Security findings, triage of scan results |
| Reviewer | review | git diff, design document, conventions.md | Review findings |

The `deliver` pipeline runs these in order and ends by producing `acceptance-guide.md` and `delivery-report.md` for the client.

### Architect

The architect turns requirements into a design that fits their size and nature.

- Chooses the tech stack (within the available profiles), structure, data model, and libraries.
- For each meaningful decision, lists the realistic alternatives, picks one, and records why.
- Scales the design to the project: a small tool gets a simple structure; a larger or multi-user system gets the separation, boundaries, and security controls it needs.
- Writes a threat model covering how the deliverable could be attacked or misused.
- The reviewer checks the implementation against these decisions and against the readability rules.

### Who checks what

Quality and security checks are split between mechanical gates and separate roles, each in its own context:

| Check | Done by |
|---|---|
| Tests pass, lint, formatting, complexity limits | Gate (mechanical) |
| Known vulnerability patterns (SAST), vulnerable dependencies (SCA), leaked secrets | Gate (mechanical) |
| Behavior matches the requirements | QA |
| Security issues tools cannot find (authorization logic, data isolation between users, business-logic abuse), and whether the threat model's mitigations are implemented | Security |
| Design fit, readability, conventions | Reviewer |

The developer fixes what any of them report; none of them fix the code themselves.

### Security

The security role reviews the deliverable from an attacker's point of view, in a context separate from the developer and the reviewer.

- Checks the change against the architect's threat model: every listed threat must have a mitigation that is actually implemented.
- The only exception is a risk the client accepted. The client may accept the risk of a low threat, or of the part of a threat that its mitigation does not cover, on a decision card that also offers mitigating it. The security role confirms that the threat is low. A threat that could let someone get in, get more rights, or read, change, or delete data they should not, or that comes through a dependency or an external service, is never accepted. Learning whether an account exists counts as reading data, unless the approved requirements make it public on purpose ([ADR 0016](adr/0016-account-existence-is-data.md)). Every accepted risk is listed under "Remaining risks" in each delivery report. See [ADR 0010](adr/0010-accepting-the-risk-of-a-low-threat.md).
- Looks for what scanners usually miss: missing authorization checks, one user reaching another user's data, insecure handling of tokens and sessions, and abuse of business logic.
- Triages scan results from the gate. A finding can only be marked as a false positive by the security role, with a recorded reason; the developer cannot dismiss findings.
- Reports findings with a severity. High-severity findings block delivery like a failing gate.

### Standards

The standards role defines the coding conventions for a project and makes them checkable.

- Starts from the stack profile's defaults and adapts them to the project's design and size.
- **Anything that can be checked mechanically becomes a tool rule**: formatter, linter settings, complexity and function-length limits, dependency boundaries between modules, and custom static-analysis rules (e.g., Semgrep) for project-specific patterns. These run in the gate.
- Only what cannot be checked mechanically (naming quality, whether a comment explains why, whether the structure matches the design) goes into `conventions.md` as a checklist for the reviewer.
- Conventions change only through a recorded decision. The developer cannot change them.

### Requirements must cover misuse

The PM and the architect must consider how a deliverable could be misused, not only how it should be used. This matters especially for security tools: a vulnerability scanner must only scan targets the user is authorized to test (e.g., by verifying domain ownership), and this must appear in the requirements.

### Later roles

- Onboarder: reads an existing repository and documents it (existing-repository mode)
- Operations: dependency vulnerability monitoring after release, opening fix issues

### Roles are usable on their own

Each role works as part of the full pipeline and on its own (e.g., the human writes the code by hand and only asks for a review, a design, or a security check).

- Roles depend on **artifacts** (documents, git diff, repository), not on each other.
- Each skill defines what to do when its input documents are missing (e.g., review compares against the design document if one exists, otherwise reviews the diff only).
- When QA runs without a specification, the report must state that the tests treat the current behavior as correct.

## GitHub Integration

Tasks are managed on GitHub so the client can follow progress without opening a terminal.

### Mapping

| keyturn | GitHub |
|---|---|
| Client request / task | Issue |
| Progress board | Project (columns follow the pipeline stages) |
| Stage of a task | Labels and Project status |
| Delivery unit | Pull request |
| Gates | GitHub Actions running `gate.sh` |
| Client-facing reports | PR description (delivery report summary and acceptance guide) |
| Questions to the client | Issue comments that mention the client. Work that depends on the answer waits; the task pauses only when nothing else can be done |

### Flow

1. The client opens an issue (or keyturn drafts one from a conversation).
2. The PM writes requirements and posts the summary on the issue. Work does not start until the client approves.
3. The architect posts the design summary. Major decisions can be confirmed by the client if needed.
4. Agents work on a branch and open a pull request.
5. GitHub Actions runs the gates. Failures send work back to the developer, up to the rework limit.
6. When the gates pass, the PR description contains the delivery report summary and the acceptance guide.
7. The client does the hands-on check and merges.

Agents can run unattended (scheduled or triggered by issue events), and the Project board shows where every task is.

### Security requirements

Unattended agents with write access to a repository are a security risk in themselves. These rules are mandatory.

- **Merging is the client's action.** Agents never merge to the default branch. Use branch protection with required gate checks.
- **Least privilege.** Agents use a token or GitHub App scoped to the repositories and permissions they need. Secrets are never exposed to agent prompts.
- **Untrusted input.** Issue and comment text is data, not instructions. On public repositories, agents only act on issues that the client has explicitly approved (e.g., by applying a label that only maintainers can apply). This prevents prompt injection from outside contributors.
- **Every agent action is traceable** through commits, PRs, and comments.

## Guardrails

Agents must not run out of control. Guardrails work in layers, so that no single failure lets an agent cause serious harm.

### 1. Agents cannot weaken their own checks

The most likely failure is not malice but an agent "making the checks pass" instead of fixing the problem. The gate detects this mechanically and fails the change:

- Changes by the developer to protected paths: gate scripts, stack profiles, the CI jobs that run the gates, linter configs, conventions, and tests written by QA (other CI/CD work is allowed when the approved requirements include it)
- New suppression comments (e.g., `//nolint`, `eslint-disable`, `# nosec`, `#[allow(...)]`) without an approved decision record
- A drop in the number of tests or in coverage
- Skipped or disabled tests

### 2. Scope is limited to what was approved

- The developer works only on what the approved requirements and design cover.
- The gate compares the changed files with the areas listed in the design and flags changes outside them.
- Some changes always require client approval before they are made: new external services, changes to authentication, authorization, or data handling, and anything that deletes data. New dependencies require it according to their kind.
- Which dependencies need that approval depends on their kind. The language toolchain and standard library are covered by approving the stack. The gate's scanners are installed by the gate and never added to the project. Development tools the stack profile names (linters, formatters, test tools that are not part of the deliverable) are approved by the profile, and the client sees them in the design summary for information only. Everything else, including every runtime library and any tool no profile names, needs the client's approval. See [ADR 0015](adr/0015-dependency-kinds.md).

### 3. New dependencies are checked

AI agents sometimes suggest packages that do not exist or that imitate popular ones. Every new dependency is checked for existence, maintenance status, known vulnerabilities, and license, and the result is recorded. This includes the development tools approved by the stack profile: not needing the client's approval never means skipping the check.

### 4. The environment limits the damage

- Agents run in a sandbox (container or the tool's sandbox mode) with only the access they need.
- No production credentials. Network access is limited to what the task needs.
- Destructive commands and direct pushes to the default branch are blocked.

These are safety guardrails that must always be on, so unlike quality gates they **are** enforced with each tool's own mechanisms (permission rules, sandbox settings, and hooks). The adapters ship recommended settings for each tool.

### 5. Budgets and escalation

- Every task has limits: rework count, token budget, time, and number of changed files.
- When a limit is reached, or the agent is unsure (ambiguous requirements, conflicting constraints), it stops and asks the client instead of guessing.

#### Subscription usage limits

When keyturn runs on a subscription plan, it must not use up the plan's usage windows.

- Claude Code exposes plan usage to the status line as `rate_limits.five_hour` and `rate_limits.seven_day` (`used_percentage`, `resets_at`) on Pro and Max plans.
- A status line script writes these values to a local file. keyturn reads the file:
  - **Soft stop (default 80%)**: the pipeline does not start a new step. The current state is saved (see Resuming Work) so work can resume after `resets_at`.
  - **Hard stop (default 90%)**: a safety hook blocks further tool calls, in case a single step runs long.
- Both thresholds apply to the 5-hour and the 7-day window, and are configurable.
- Things to verify during implementation: the values only appear after the first API response in a session, and may not be available in headless runs (`claude -p`) or subagents. If the value is missing, keyturn must treat it as unknown and stop at step boundaries rather than assume there is room.
- Codex needs its own usage source; until one is available, the Codex adapter relies on the task budgets above.

### 6. Everything is traceable

Every action leaves a record: commits, PRs, comments, gate logs, and decision records. The delivery report lists any guardrail that was triggered during the task, and the models and tool versions that were used.

## Resuming Work

A task can stop at any point: a usage limit, a closed terminal, a crash, a question waiting for the client, or the rework limit. It must always be possible to resume it later without losing work or repeating finished steps.

- **State lives outside the session.** Each task has a state file, `keyturn/internal/state/<task>.md`, recording the current step, completed steps, open questions, and why it stopped ([ADR 0011](adr/0011-task-state-file.md)). GitHub (issue labels, PR status) reflects the same state when integration is used.
- **Checkpoint at every step boundary.** When a step finishes, its outputs are written to documents and committed to the task branch, and the state file is updated. A stop never loses more than the step in progress.
- **Steps are safe to rerun.** If a stop happens in the middle of a step, resuming reruns that step from its inputs. Steps must not depend on anything that exists only in the previous session's context.
- **One command resumes.** A `resume` skill reads the state file and continues from the right step. With no argument, it lists the tasks that can be resumed.
- **Resume anywhere.** Because state is in the repository, a task can be resumed in a new session, on another machine, or with the other supported AI tool.
- When work stops because of a usage limit, the state file records when the limit resets, so the client knows when it can continue. (Automatic resumption after a reset belongs to the future autonomous mode.)

## Model Tiers

Not every step needs the most capable model.

- **Lower-tier models do the bulk of the work** where the task is well defined: implementation of a clear design, test writing, translation, routine fixes.
- **Higher-tier models evaluate** what needs judgment: requirements, design, and the review of the lower-tier model's output (design fit, readability, things the tools cannot check).
- **Escalate on failure.** If a lower-tier model fails the same step repeatedly, the step is retried with a higher-tier model before the rework limit is reached.
- This does not replace the mechanical gates. The higher-tier review covers what the tools cannot check; pass/fail still comes from the gates.
- The model for each role is configurable per project. Usage is recorded per role so the tiering can be tuned with real data.

## External Services

By default, keyturn sends code and documents nowhere except to the AI tool the client already uses (Claude Code or Codex, under whatever plan or contract the client has).

- Gates run locally (e.g., Semgrep, gitleaks, Trivy run on the machine or in CI).
- Some checks need public data, such as vulnerability databases (e.g., OSV). These send only package names and versions, never code.
- Translation (`localize`) is done by the AI tool itself. No translation service is used.
- Any other external service (e.g., hosted scanners, cloud rule registries) is opt-in, off by default, and listed in the README with exactly what it sends.

## Architecture

### Separate the "what" from the "who"

- **Skills (SKILL.md) = what a role does**: inputs, procedure, and outputs. Written to the Agent Skills open standard (agentskills.io) so they work across tools.
- **Subagents = who runs it**: a thin definition that runs a skill in its own context. This is the only part written per tool.
  - Claude Code: Markdown (agents/*.md)
  - Codex: TOML (.codex/agents/*.toml)
- On tools without subagents, run the skill in a separate process (e.g., `claude -p`, `codex exec`) to keep contexts separate.

### Agent instruction files

- `AGENTS.md` is the only committed instructions file, in this repository and in every project keyturn works on.
- Tools that look for a different file name (e.g., `CLAUDE.md` for Claude Code) get a **local symbolic link** to `AGENTS.md`, created by each user for the agent they use and excluded from Git with `.git/info/exclude`. Committed files stay free of tool-specific names.
- Each adapter's setup step creates the link and the exclude entry for its tool, so users do not have to do it by hand.

### Gates

- Quality gates are not implemented as hooks (safety guardrails are; see Guardrails). Plugin hooks are always active once the plugin is enabled, which would interfere with standalone use and manual work. The pipeline skill (`deliver`) calls `gates/gate.sh` explicitly, and so does CI.
- `gate.sh` is a plain CLI that does not depend on Claude Code or Codex.
- It reads the stack profile to decide which checks to run.
- It checks whether external tools are installed and explains how to install them if not.

## Repository Layout (initial)

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
  gate.sh                 # runs checks defined by the stack profile
                          # plus guardrail checks (protected paths, suppressions, scope)
profiles/                 # stack profiles (one frontend + one backend first)
templates/
  client/                 # requirements, design summary, acceptance guide, delivery report, decision card, approvals
  internal/               # design, decisions, handoff, test report, review, task state
adapters/
  claude/                 # agents/*.md (listed in plugin.json), recommended permission settings
  codex/                  # agents/*.toml, recommended sandbox settings
github/                   # workflow templates, labels, project setup
evals/
  requests/               # evaluation requests
docs/
  DESIGN.md               # this document
  adr/                    # keyturn's own decision records
AGENTS.md
README.md
LICENSE                   # MIT
.gitignore                # includes .keyturn/ (local translations and maintainer notes)
```

In a Claude Code plugin, only the manifests go inside `.claude-plugin/`; `skills/`, `hooks/`, etc. must be at the plugin root. The repository root is the plugin root, so `skills/` is shared by Claude Code and Codex. See [ADR 0005](adr/0005-repository-root-as-plugin-root.md).

## Evaluation

keyturn is also built by AI, so keyturn itself needs regression testing: a change to a skill, gate, profile, or template must not make results worse.

- Keep evaluation requests in `evals/requests/` and run them end to end after changes.
- Keep a **baseline** of results and compare every run against it. Metrics include: gate pass rate, planted vulnerabilities caught, acceptance criteria met, rework count, tokens, client requests per task, and the readability of client-facing documents (judged by a higher-tier model against the writing rules).
- Run the full suite when skills, gates, profiles, or templates change, and when the model or tool version changes.
- A change that makes any metric clearly worse is not merged until the reason is understood.
- Changes to requirements during a task are part of the evaluation too: include at least one request with a mid-task change.
- Include requirements that commonly lead to vulnerabilities (per-user data isolation, role-based permissions, file uploads).
- Include requests of different sizes, to check that the architect scales the design instead of always choosing the same structure.
- Include at least one request that is not an application.
- Record token usage, time, and rework count per role and per task, to see where the cost goes and to build estimation data for the future.

## Client Portal (planned)

A GUI for the client side of keyturn. keyturn produces many documents, so the client needs one place to see and act on them across repositories:

- Requirements waiting for approval, and approving them
- Answering questions from agents
- Acceptance guides as checklists, recording the result of each check
- Delivery reports and task progress
- Cost per task and per role (token usage, rework count)

The portal is not a second source of truth. Documents stay in the repositories and tasks stay on GitHub; the portal reads and writes through GitHub (e.g., approval applies a label, an answer posts a comment). It is built with keyturn itself, after the GitHub integration.

## Phases

keyturn is developed by using it. New-project mode is validated on real applications first (no throwaway sample apps), and existing-repository mode comes after that.

Stop at the end of each phase and report to the human whether the completion criteria are met.

1. **Foundation**: README, LICENSE (MIT), AGENTS.md, directory layout, and the `localize` skill
   - Done when: the first lines of the README explain the concept clearly, and `localize` can translate keyturn's own documents (and those of any existing repository) into the maintainer's language locally without committing anything.
2. **Document templates**: client-facing and internal templates
   - Done when: the templates can be filled in by hand for one evaluation request, and the client-facing ones make it obvious what the client needs to check.
3. **Phase 1 skills and the Claude Code adapter**: spec, design, conventions, implement, qa, security-review, review, deliver, resume, plus the recommended sandbox and permission settings
   - Done when: one small evaluation request runs from request to delivery inside the sandbox, and a run that is stopped in the middle can be finished with `resume` in a new session.
4. **Gate and the first two stack profiles**: gate.sh with one frontend and one backend profile (tests, linters, and the guardrail checks)
   - Done when: a failing test sends work back to the developer, the loop stops at the limit, and a developer change that deletes a test or adds a suppression is rejected.
   - Also: record the first evaluation baseline and make the eval suite runnable with one command.
5. **Security checks in the profiles**: add SAST, dependency scanning, and secret scanning
   - Done when: the vulnerabilities planted in the evaluation requests are caught by the gate.
6. **Validation on a real application**: validate new-project mode end to end on a real (not sample) application, using the first two stack profiles. Which application is used follows the maintainer's local plan (see Maintainer Notes).
   - Done when: the client can accept it using only the client-facing documents, without reading the code.
7. **GitHub integration**: issues, Project board, labels, Actions, PR-based delivery
   - Done when: a task moves from issue to merged PR with the client only approving requirements and doing the final check.
8. **Client portal**: build it with keyturn, on top of the GitHub integration
   - Done when: the client can approve requirements, answer questions, and do acceptance checks from the portal alone.
9. **More profiles**, one at a time
10. **Codex adapter**
    - Done when: the same evaluation requests run on Codex as on Claude Code.
11. **Existing-repository mode**: onboarding, then the first real issue on an existing repository
    - Done when: the delivery report and acceptance guide are good enough for the client to merge without reading the code.
12. Later: security and operations roles; DAST (OWASP ZAP); scheduled unattended runs

## Future Vision (not in scope yet)

These are enhancements for later. They are written down so that current decisions do not block them, not to be built now.

- **Fully autonomous operation**: keyturn works on its own, and the client only reviews what has piled up (approvals, questions, acceptance checks), for example once every morning in the client portal.
- **Deadline-driven planning**: the client says what they want and by when. keyturn interviews the client for the information it needs, breaks the work into tasks, builds a schedule, and runs the work automatically based on the schedule and the available usage (rate limits, budget), so that deliverables are ready on time.

What to do now to keep this possible:

- Keep all task state on GitHub and in repository documents, never only in a session.
- Record actual results for every task (tokens, wall-clock time, rework count, number of client questions). Future scheduling needs this data to estimate realistically.
- Keep the escalation rules strict. Autonomy is only safe if agents reliably stop and ask.

## Implementation Rules

- Follow the readability principle above in all code, including keyturn's own scripts.
- Skill frontmatter uses only `name` and `description`, for portability across tools.
- Do not build a generator for subagent definitions until the set of roles is stable.

## Maintainer Notes

This document is about keyturn itself and stays independent of any one person's projects. A maintainer's own plans (which applications to build, which repositories to bring in, development budget) live in a local, git-ignored file: `.keyturn/local/PLAN.md`. If that file exists, read it together with this document. Never copy its contents into committed files.

## Decisions

Decisions about keyturn itself are recorded as ADRs. See the index in [`docs/adr/README.md`](adr/README.md). New decisions go straight into ADRs.
