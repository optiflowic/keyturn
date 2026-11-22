# Roles

## Phase 1 roles

| Role | Skill | Input | Output |
|---|---|---|---|
| PM | spec | Client request | requirements.md (client), acceptance criteria |
| Architect | design | requirements.md, stack profile | Design document, decision records, threat model, design-summary.md (client) |
| Standards | conventions | Stack profile, design document | conventions.md, linter and formatter configs, custom rules |
| Developer | implement | requirements.md, design document, conventions | Deliverable, handoff notes |
| QA | qa | requirements.md (never the implementation) | Tests, detailed test report |
| Security | security-review | Threat model, git diff, gate scan results | Security findings, triage of scan results |
| Reviewer | review | git diff, design document, conventions.md | Review findings |

The `deliver` pipeline runs these in order and ends by producing `acceptance-guide.md` and `delivery-report.md` for the client, written in a context of their own from the committed records, with the gate's log of the final head ([ADR 0033](../adr/0033-delivery-documents-from-the-records.md)).

Each role runs in a context of its own, and `deliver` checkpoints every step in the task state file. After each `implement` step, `deliver` runs the gate; when it passes, QA, the security role, and the reviewer all run before anything goes back. A failing gate, a failing test, or a high or medium finding (except a medium one whose risk the client accepted on a decision card, [ADR 0042](../adr/0042-pm-merges-on-machine-checked-conditions.md)) sends the work back to the developer with every open finding, up to a rework limit (3 rounds by default, set in `keyturn/config.json`); low findings alone are listed in the delivery report ([ADR 0030](../adr/0030-deliver-rework-loop.md)). During the MVP, one task runs at a time (a new one also waits while a task branch is not merged, unless the person says to start anyway, [ADR 0034](../adr/0034-new-task-waits-for-unmerged-task-branches.md)), and its requirements, design, and conventions are fixed once `implement` starts: the design step waits until the client has answered everything it asked, and a later need to change them stops the task for the maintainer ([ADR 0031](../adr/0031-documents-fixed-once-implement-starts.md)).

The work is delivered as a pull request: `deliver` pushes the task branch and opens it, the security role and the reviewer post their findings on it, and the PM merges it once the client has accepted the delivery and the machine checks pass ([ADR 0041](../adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0042](../adr/0042-pm-merges-on-machine-checked-conditions.md)).

## Architect

The architect turns requirements into a design that fits their size and nature.

- Chooses the tech stack (within the available profiles), structure, data model, and libraries.
- For each meaningful decision, lists the realistic alternatives, picks one, and records why.
- Scales the design to the project: a small tool gets a simple structure; a larger or multi-user system gets the separation, boundaries, and security controls it needs.
- Writes a threat model covering how the deliverable could be attacked or misused.
- The reviewer checks the implementation against these decisions and against the readability rules.

## Who checks what

Quality and security checks are split between mechanical gates and separate roles, each in its own context:

| Check | Done by |
|---|---|
| Tests pass, lint, formatting, complexity limits | Gate (mechanical) |
| Known vulnerability patterns (SAST), vulnerable dependencies (SCA), leaked secrets | Gate (mechanical) |
| Behavior matches the requirements | QA |
| Security issues tools cannot find (authorization logic, data isolation between users, business-logic abuse), and whether the threat model's mitigations are implemented | Security |
| Design fit, readability, conventions | Reviewer |

The developer fixes what any of them report; none of them fix the code themselves.

## Security

The security role reviews the deliverable from an attacker's point of view, in a context separate from the developer and the reviewer.

- Checks the change against the architect's threat model: every listed threat must have a mitigation that is actually implemented.
- The only exception is a risk the client accepted. The client may accept the risk of a low threat, or of the part of a threat that its mitigation does not cover, on a decision card that also offers mitigating it. The security role confirms that the threat is low. A threat that could let someone get in, get more rights, or read, change, or delete data they should not, or that comes through a dependency or an external service, is never accepted. Learning whether an account exists counts as reading data, except for an identifier the approved requirements make public on purpose, such as a unique username; a private identifier, such as an email address, is never covered ([ADR 0016](../adr/0016-account-existence-is-data.md)). Every accepted risk is listed under "Remaining risks" in each delivery report. See [ADR 0010](../adr/0010-accepting-the-risk-of-a-low-threat.md). Under the same conditions, the client may also accept the risk of a medium finding of either review, on a card that also offers fixing it; the report then marks it accepted, and it neither sends the work back nor stops the merge ([ADR 0042](../adr/0042-pm-merges-on-machine-checked-conditions.md)).
- Looks for what scanners usually miss: missing authorization checks, one user reaching another user's data, insecure handling of tokens and sessions, and abuse of business logic.
- Triages scan results from the gate. A finding can only be marked as a false positive by the security role, with a recorded reason; the developer cannot dismiss findings.
- Reports findings with a severity. High-severity findings block delivery like a failing gate.

## Standards

The standards role defines the coding conventions for a project and makes them checkable.

- Starts from the stack profile's defaults and adapts them to the project's design and size.
- **Anything that can be checked mechanically becomes a tool rule**: formatter, linter settings, complexity and function-length limits, dependency boundaries between modules, and custom static-analysis rules (e.g., Semgrep) for project-specific patterns. These run in the gate.
- Only what cannot be checked mechanically (naming quality, whether a comment explains why, whether the structure matches the design) goes into `conventions.md` as a checklist for the reviewer.
- Conventions change only through a recorded decision. The developer cannot change them.

## Requirements must cover misuse

The PM and the architect must consider how a deliverable could be misused, not only how it should be used. This matters especially for security tools: a vulnerability scanner must only scan targets the user is authorized to test (e.g., by verifying domain ownership), and this must appear in the requirements.

## Later roles

- Onboarder: reads an existing repository and documents it (existing-repository mode)
- Operations: dependency vulnerability monitoring after release, opening fix issues

## Roles are usable on their own

Each role works as part of the full pipeline and on its own (e.g., the human writes the code by hand and only asks for a review, a design, or a security check).

- Roles depend on **artifacts** (documents, git diff, repository), not on each other.
- Each skill defines what to do when its input documents are missing (e.g., review compares against the design document if one exists, otherwise reviews the diff only).
- When QA runs without a specification, the report must state that the tests treat the current behavior as correct.
- A role may work from input that is not approved (for example, requirements the client has not approved, or a request given in another form) only when a person uses it on its own and declines to have requirements written and approved with `spec`. Its outputs then say that they are not based on approved requirements. `deliver` never takes in an output that says so: inside `deliver`, every role works only from approved input.
