# Stack Profiles

A stack profile defines what "verified" means for one tech stack. Gates read the profile instead of hard-coding tools.

Each profile defines:

- How to build, run, and test
- Linters and formatters
- Security checks (SAST rules, dependency scanning, secret scanning)
- Recommended project structure and design patterns for different project sizes
- Secure defaults and patterns to avoid
- Where QA's tests live, as a folder of their own (see [ADR 0017](../adr/0017-qa-tests-in-their-own-folder.md))
- For a stack with screens, the E2E tool QA checks the screens with in a real browser, as the best practice at the time the profile is written, with where its browser comes from and how QA checks that ([ADR 0069](../adr/0069-qa-checks-the-screens-end-to-end-in-a-browser.md)). keyturn fixes that QA checks the screens end to end and keeps evidence, not the tool: a project's design may choose another with the client
- For a stack with screens, how the pages use the design's tokens: one token file holds every token, no literal value of the kinds it holds appears elsewhere in any form, and a UI library's theme takes the values the tokens decide from it; and a default styling method, as the best practice at the time the profile is written, with the token file's place and form ([ADR 0072](../adr/0072-profiles-fix-styling-principles-not-the-tool.md)). keyturn fixes how the pages use the tokens, not the styling tool: a project's design chooses the method with the client among the realistic options. The names of styling tools appear only in the profiles
- What cannot be checked mechanically for this stack (this goes into the delivery report as a known gap)

Profiles live in `profiles/<stack>/`, each as a `profile.json` that the gate reads ([ADR 0028](../adr/0028-gate-interface.md)). A project names the profile of each of its folders in `keyturn/config.json` (`parts`). Add one profile at a time, and only after the previous ones work well. Some stacks have much weaker mechanical security checks than others (e.g., Neovim plugins); the profile must say so honestly rather than pretend coverage exists.

A profile names no fixed version of its runtime or its tools. Every version is the newest stable release at the time it is chosen that is older than the waiting period, the runtime's the newest LTS release (or the newest stable one when it has none), confirmed from its official source; the design names one runtime version per part and checks each dependency against it, and an older version has its reason in an ADR ([ADR 0054](../adr/0054-newest-stable-versions-checked-against-the-runtime.md)).

## Planned profiles

| Area | Profiles |
|---|---|
| Frontend | React (SPA), Next.js, React Router v7+ |
| Backend | Go, Python, Rust |
| Other | Neovim plugin (Lua), Rust CLI/TUI |

Start with **one frontend profile and one backend profile**, enough to validate new-project mode end to end on a web application (see phase 6 in [Phases](phases.md)). Add the rest one at a time.

The MVP's `go` and `react-spa` profiles ([Phases](phases.md#mvp)) define only building, running, testing, linting, counting the tests, and where QA's tests live, and, for `react-spa`, the E2E tool QA checks the screens with, which the gate does not run ([ADR 0069](../adr/0069-qa-checks-the-screens-end-to-end-in-a-browser.md)), and how the pages use the tokens, with a default styling method, which the gate does not check ([ADR 0072](../adr/0072-profiles-fix-styling-principles-not-the-tool.md)). They have no security checks (SAST, dependency scanning, secret scanning) until phase 5, and each delivery report made with them lists that under "What was not verified", as a known gap of the profile.
