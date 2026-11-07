# keyturn

keyturn turns AI coding agents into a contractor team, with you as the client. You do not read the code: you approve the requirements and acceptance criteria, read the reports, and do the final hands-on check yourself. The agents handle everything else, from specification and design to implementation, verification, and delivery.

A deliverable ships only because it passed mechanical checks (tests, static analysis, dependency and secret scanning), not because an AI said it was fine.

The name comes from a turnkey contract, where the contractor delivers something that is ready to use as soon as the client receives it.

> [!NOTE]
> keyturn is a work in progress. Only `localize` can be used today, and it is experimental. The full design, and the order in which it is built, are in [`docs/DESIGN.md`](docs/DESIGN.md). Progress on each phase is tracked in the [milestones](https://github.com/optiflowic/keyturn/milestones).

## Why

When the client never reads the code, a serious problem in production lands directly on them. So keyturn treats security and quality assurance as mandatory, and every delivery says **what was verified and what remains unverified**.

- **Specifications and evidence, not code**: the client reviews numbered requirements, acceptance criteria, and reports.
- **Separate judges**: QA and security run in their own contexts and never see the developer's reasoning.
- **Mechanical ship/no-ship decisions**: gates decide; agents read the results and fix problems.
- **Agents cannot weaken their own checks**: the developer cannot change the gates, conventions, or tests it is judged by.
- **Work can always be resumed**: task state lives in the repository, not in a session.

Deliverables are not limited to applications. Anything that can be specified, built, and verified is in scope, in new projects and existing repositories.

## localize

`localize` lets you read a repository's English documents in your own language, as local files. The translations are never committed. It works on any Git repository, including ones that do not use keyturn.

Install it as a Claude Code plugin:

```sh
claude plugin marketplace add optiflowic/keyturn
claude plugin install keyturn@keyturn
```

Then, in the repository you want to read, ask for a file in your language, for example: "Translate docs/DESIGN.md into Japanese."

Translations are written to `.keyturn/i18n/<lang>/`, at the same paths as the originals. When a document changes, only the changed sections are translated again. The full procedure is in [`skills/localize/SKILL.md`](skills/localize/SKILL.md).

## Supported tools

keyturn is not tied to one AI tool. Support comes in layers:

1. **Skills** (`skills/`) follow the [Agent Skills](https://agentskills.io) standard, so any tool that supports it can use them.
2. **`AGENTS.md`** is the instructions file, and many tools read it as it is.
3. **Plugin packaging**, which installs everything at once, is provided for Claude Code first. Codex follows in a later phase, and other tools are added the same way as needed.
4. **Tool-specific parts**, such as subagents and safety hooks, are handled by a thin adapter per tool in `adapters/`.

See [ADR 0005](docs/adr/0005-repository-root-as-plugin-root.md) for how one `skills/` folder serves every tool.

## Documentation

- [`docs/DESIGN.md`](docs/DESIGN.md): design principles, architecture, and phases
- [`docs/adr/`](docs/adr/): decisions about keyturn itself
- [`AGENTS.md`](AGENTS.md): instructions for AI agents working on this repository
- [`.github/SECURITY.md`](.github/SECURITY.md): how to report a vulnerability

## License

[MIT](LICENSE)
