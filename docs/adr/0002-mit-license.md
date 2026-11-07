# 0002. MIT license

- Status: accepted
- Date: 2026-11-07

## Context

keyturn is public ([ADR 0001](0001-public-repository-from-the-start.md)) and is meant to be used in other people's projects, including commercial ones. It needs a license that states clearly what others may do with it.

## Options considered

1. **MIT**: short, widely understood permissive license. Allows any use, including in closed-source projects, with attribution.
2. **Apache-2.0**: permissive, with an explicit patent grant, but longer and with more conditions (stating changes, the NOTICE file).
3. **GPL-3.0 or another copyleft license**: keeps derivatives open, but discourages adoption in companies and in closed-source projects.

## Decision

keyturn is released under the MIT license.

## Reasons

- keyturn's skills, templates, and profiles are meant to be copied into and adapted for many projects. The fewer conditions on that, the better.
- MIT is the most common license in the AI agent tooling ecosystem that keyturn builds on, so it causes no friction for users or contributors.
- keyturn has no patented technology for which Apache-2.0's patent grant would make a practical difference.

## Consequences

- A `LICENSE` file with the MIT text sits at the repository root.
- Others can use and modify keyturn freely, including in closed-source work, as long as the license notice is kept.
- Dependencies and copied content must be compatible with MIT.
