# 0015. Which tools and libraries need the client's approval depends on their kind

- Status: accepted
- Date: 2026-11-11

## Context

"Guardrails" in `docs/DESIGN.md` says that a new dependency always needs the client's approval before it is used (2), and that every new dependency is checked for existence, maintenance status, known vulnerabilities, and license (3). `templates/internal/design.md` adds that a dependency the stack profile suggests is still new the first time a project adds it.

Read literally, this covers everything a project needs from outside, and that turned up three problems while the phase 3 skills were written:

- The `conventions` skill needs a linter, a formatter, and their plugins in the project's manifest (for example ESLint, `typescript-eslint`, and Prettier in `package.json`), and QA needs test tools (for example Vitest and Playwright). Under the current rule each one is a decision the client must agree to. The worked example does not follow the rule: its design approves only `react`, `react-dom`, and `vite`, while its delivery report lists ESLint, Vitest, and Playwright.
- An independent run of the `design` skill treated the Go toolchain itself as an unchecked dependency, so without network access nothing could be built.
- The gate's scanners (Semgrep, gitleaks, Trivy) are not in the project at all, so it is unclear whether they count.

What constrains the answer:

- The client does not read code. A list of development tools is not something they can judge, so asking them to approve it turns into approving without reading ("Client attention budget").
- Dependencies are a real attack path: AI agents sometimes suggest packages that do not exist or imitate popular ones ("Guardrails", 3). Skipping the client's approval must not mean skipping the check.
- Libraries that end up in the deliverable, such as React or Vite, shape what the client receives, and stay a client decision.

## Options considered

1. **Every kind counts as a dependency.** The architect lists the development tools in the design and the design summary, and the client approves them with the rest. Consistent with today's wording, but the client is asked about things they cannot judge, which trains them to approve without reading.
2. **Every tool a stack profile names is approved by the profile.** Fewer questions, but it would also cover runtime libraries a profile recommends, which end up in the deliverable and should stay a client decision.
3. **Every tool is installed by the gate, outside the project.** No approval needed, but linter plugins and test tools that parse the project's code (for example ESLint with TypeScript) work badly outside the project's manifest.
4. **Decide by kind**: what the client approves, and what is only checked, depends on what the item is and where it ends up.

## Decision

Option 4. Each kind is handled as follows:

| Kind | Examples | Counts as a dependency | Client approval | Mechanical check |
|---|---|---|---|---|
| Language toolchain and standard library | Go, Node.js, Python | no | covered by approving the stack | no |
| Gate scanners | Semgrep, gitleaks, Trivy | no: installed by the gate, never added to the project | no | the gate's own responsibility |
| Development tools the stack profile names | linters, formatters, test tools | yes | no: approved by the profile | yes, every time, recorded |
| Everything else | runtime libraries (React, Vite), tools no profile names | yes | yes, as today | yes, every time, recorded |

- "Development tools the stack profile names" means tools that only check, format, or test the code and are not part of the deliverable. A runtime library is never in this kind, even if a profile recommends it.
- Development tools approved by the profile appear in `design-summary.md` for information, not under "Must agree".
- Any tool or library not covered by a profile, including the defaults a role assumes while no profile exists, falls under "Everything else".

## Reasons

- The client is asked only about what they can judge and what reaches them: the stack, and the libraries and services in the deliverable. A short list they can read beats a long list they approve blindly.
- The mechanical check is what catches a package that does not exist or imitates a popular one. Keeping it for every development tool, every time, keeps that protection without the client's attention.
- Approving the stack already means approving its toolchain; counting the toolchain again adds a question with no new information.
- Installing the scanners in the gate keeps the project free of tools that check the project, and keeps the developer from changing them ("Guardrails", 1).

## Consequences

- `docs/DESIGN.md` "Guardrails" 2 and 3 say which kinds need approval and that every dependency is still checked.
- `templates/internal/design.md`: the libraries table marks each item's kind; the comment that a profile's suggestion is still new is narrowed to runtime libraries.
- `templates/client/design-summary.md`: an informational list of development tools approved by the profile, outside "Must agree".
- The worked example: its design lists its development tools (golangci-lint, ESLint with its TypeScript rules, Prettier, Vitest, and Playwright) with their check results, so it matches the delivery report and its conventions.
- The `design`, `conventions`, and `qa` skills follow the table. Until stack profiles exist (phase 4), no development tool is approved by a profile, so the tools a role assumes still need the client's approval.
- Stack profiles (phase 4) list their development tools and are reviewed in keyturn's own pull requests, since that review is what stands in for the client's approval.
