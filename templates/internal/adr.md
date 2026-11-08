<!--
Template: architecture decision record (internal). Filled in by the role that makes the decision, usually the architect.

- Always written in English.
- One decision per file: internal/adr/NNNN-short-title.md, numbered in order.
- Search the existing ADRs first. If an accepted ADR already covers the question, follow it instead of writing a new one.
- Never edit an accepted ADR, except to mark it superseded. To change a decision, write a new ADR that supersedes it.
- If the decision needs the client's agreement (cost, scope, how the client works, or a change that always needs approval), summarize it in design-summary.md.
  It stays "proposed" until the client agrees there; nothing that depends on it starts before that.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# <NNNN>. <Title of the decision>

- Status: <proposed | accepted | superseded by [NNNN](NNNN-short-title.md)>
- Date: <YYYY-MM-DD>
- Supersedes: <[NNNN](NNNN-short-title.md)> <!-- Delete this line if it does not apply. -->
- Serves: R-<n>
- Needs client agreement: <yes | no>

## Context

<!-- What problem or question needs a decision, and what constrains the answer (requirements, scale, existing decisions). -->

<context>

## Options considered

<!-- The realistic options only, with their main pros and cons. -->

1. **<option A>**: <what it is, and its main pros and cons>
2. **<option B>**: <what it is, and its main pros and cons>

## Decision

<!-- The option chosen, in one or two sentences. -->

<decision>

## Reasons

<!-- Why this option fits the requirements and the scale of the work better than the others. -->

<reasons>

## Consequences

<!-- What becomes easier, what becomes harder, and what follow-up work this creates. -->

<consequences>
