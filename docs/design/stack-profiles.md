# Stack Profiles

A stack profile defines what "verified" means for one tech stack. Gates read the profile instead of hard-coding tools.

Each profile defines:

- How to build, run, and test
- Linters and formatters
- Security checks (SAST rules, dependency scanning, secret scanning)
- Recommended project structure and design patterns for different project sizes
- Secure defaults and patterns to avoid
- Where QA's tests live, as a folder of their own (see [ADR 0017](../adr/0017-qa-tests-in-their-own-folder.md))
- What cannot be checked mechanically for this stack (this goes into the delivery report as a known gap)

Profiles live in `profiles/<stack>/`. Add one profile at a time, and only after the previous ones work well. Some stacks have much weaker mechanical security checks than others (e.g., Neovim plugins); the profile must say so honestly rather than pretend coverage exists.

## Planned profiles

| Area | Profiles |
|---|---|
| Frontend | React (SPA), Next.js, React Router v7+ |
| Backend | Go, Python, Rust |
| Other | Neovim plugin (Lua), Rust CLI/TUI |

Start with **one frontend profile and one backend profile**, enough to validate new-project mode end to end on a web application (see phase 6 in [Phases](phases.md)). Add the rest one at a time.
