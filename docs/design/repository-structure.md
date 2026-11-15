# Repository Structure

keyturn supports both single-repository and multi-repository projects. Which one to use is a design decision based on the size and nature of the project, not a fixed rule.

## Flow

1. The PM gathers requirements from the client, including the expected size and how the project may grow.
2. The architect decides the repository structure (one repository, a monorepo, or several repositories) and records it as an ADR, with the reasons and the alternatives.
3. keyturn gives the client a short setup guide: the repositories to create, their names, visibility, and the required settings (e.g., branch protection, labels).
4. **The client creates the repositories.** Agents do not create repositories, in line with least privilege.
5. keyturn verifies the setup (access, settings, labels) and reports anything missing before starting work.

## Multi-repository projects

- **One home repository** holds the project-wide documents: requirements, ADRs, the project-wide design, task state, and client-facing reports. It can be the main application repository or a dedicated repository, decided by the architect.
- Each repository holds its own code, its own internal documents, and its own gate.
- **Contracts between repositories** (e.g., API schemas, message formats) are defined in the home repository and versioned. Each repository tests against the contract.
- A task that spans repositories has one issue in the home repository and one pull request per affected repository, linked together. It is delivered only when every pull request passes its gate and the contract tests pass.
- Resuming, cost tracking, and the client portal treat the project as a whole, using the home repository as the entry point.
