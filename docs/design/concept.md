# Concept

keyturn turns AI agents into a contractor team, with the human as the client.

- The client (human) does not read code. They review requirements, acceptance criteria, and reports, and do the final hands-on check themselves.
- The contractor (AI) is a team of role-based agents that handles everything from specification and design to implementation, verification, and delivery.
- Deliverables are not limited to applications. Anything that can be specified, built, and verified is in scope (apps, libraries, editor plugins, CLI tools, infrastructure, documentation, etc.).
- keyturn works on both new projects and existing repositories.
- The name comes from a turnkey contract: the client receives something that works as soon as they "turn the key".

Since the client never reads the code, the consequences of a serious problem in production fall directly on them. **Security and quality assurance are mandatory.** A deliverable ships because it passed mechanical checks, not because an AI said it was fine.

Absolute safety cannot be guaranteed. The goal is to always be able to explain **what was verified and what remains unverified**, and to hand that to the client in a report.
