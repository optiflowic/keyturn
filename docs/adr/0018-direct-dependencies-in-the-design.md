# 0018. The design lists direct dependencies; the lock file covers the rest

- Status: accepted
- Date: 2026-11-13

## Context

[ADR 0015](0015-dependency-kinds.md) decides which dependencies need the client's approval, by kind, and says that every dependency is checked. It does not say whether that includes indirect (transitive) dependencies: the packages that the project's own dependencies pull in.

Read literally, every package in a lock file needs a row in the design, with its kind and its check. For the worked example's web client that is about 140 npm packages. A trial run of the `security-review` skill reported the missing rows as a high finding. Nobody checks 140 rows by hand with care, the client cannot judge them, and the list changes with every update of a direct dependency.

Indirect dependencies are still a real attack path (a compromised or vulnerable package deep in the tree), so they cannot simply be ignored.

## Options considered

1. **List every package, direct and indirect, in the design.** Complete on paper, but the list is too long to check or approve with care, so it would be approved without reading ("Client attention budget").
2. **List only direct dependencies, and leave indirect ones unchecked.** Short and readable, but a vulnerable indirect package would go unnoticed.
3. **List only direct dependencies, and check indirect ones mechanically through the lock file.** The design stays short; the lock file fixes every indirect version, and a scanner checks all of them on every run.

## Decision

Option 3.

- The design lists only direct dependencies: what the project's manifest names itself, including the peer dependencies that a direct dependency requires (for example, `typescript` for `typescript-eslint`). Each one gets the client's approval by its kind (ADR 0015) and the dependency check, as today.
- Indirect dependencies are not listed in the design. The lock file (`package-lock.json`, `go.sum`, or the stack's equivalent) is always committed, so every indirect version is fixed and reviewable.
- The gate's dependency scan (phase 5) checks every package in the lock file, indirect ones included, for known vulnerabilities. The delivery report gives its result. Until the gate has a dependency scan, the delivery report lists the indirect dependencies under "What was not verified".

## Reasons

- The design keeps only what a person can check and the client can approve: the dependencies the project chose.
- A committed lock file turns "which indirect versions" from a question into a fact, so a scanner can check them and a review can see when they change.
- A scanner checks hundreds of packages the same way every time, which a list in the design never would.

## Consequences

- `docs/DESIGN.md` "Guardrails" 3 says what the design lists, that the lock file is always committed, and how indirect dependencies are checked.
- `templates/internal/design.md`: the libraries table lists direct dependencies only, peer dependencies included, and the lock file is always committed.
- `templates/client/delivery-report.md`: "What was verified" gives the dependency scan's result, indirect dependencies included; "What was not verified" lists them while no scan exists.
- The `design`, `implement`, and `security-review` skills follow this: the architect lists direct and peer dependencies, the developer commits the lock file, and the security role does not report indirect dependencies as missing from the design.
