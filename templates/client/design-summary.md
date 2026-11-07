<!--
Template: design summary (client-facing). Filled in by the architect.

- Write for a client who does not read code: no code, no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, ADR numbers) exactly as it is, in every language.
- Only the main decisions go here. Every one of them has an ADR in internal/adr/; the details stay there.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Design summary: <name of what is being built>

Status: <draft | waiting for agreement | agreed>

Based on requirements version <n>.

## Summary

<!-- About three lines: the overall shape of the design, and how many decisions need the client's agreement. -->

<summary>

## What you need to do

<!--
Only what the client must do or decide now: usually, agreeing to the decisions in the next section.
Leave the list empty, with "Nothing right now.", when no decision needs agreement.
-->

> [!IMPORTANT]
> - <for example: read ADR 0002 and ADR 0004 below, and agree to them, or tell us what to change>

## Decisions that need your agreement

<!--
One heading per decision that affects the client: cost, scope, or how the client works.
- Use the number and title of the decision's ADR, and link to it.
- "Serves" lists the requirements the decision exists for. Every decision serves at least one requirement.
- Give the realistic options only, in a sentence each, with why each was not chosen.
- "What it means for you" is the part the client agrees to. Say it concretely: money, time, what is or is not included, what they have to do.
- When the client answers, set "Agreement" to agreed, or to not agreed with what they want changed.
- When a new ADR supersedes one listed here, replace the entry with the new ADR and set "Agreement" back to waiting.
-->

### ADR <NNNN>: <short title>

- Agreement: <waiting | agreed | not agreed: what the client wants changed>
- Serves: R-<n>
- Decision record: [ADR <NNNN>](../internal/adr/<NNNN-short-title>.md)

**What we decided**: <the decision, in one or two sentences>

**Why**: <the reason, tied to the requirements it serves>

**Other options we considered**:

- <option>: <why it was not chosen>

**What it means for you**: <cost, scope, or how you work>

## Other main decisions

<!--
Decisions the client should know about but does not need to agree to. They are listed for information only.
Use the same fields as above, without "Agreement". Leave "What it means for you" out when it means nothing for the client.
Leave the section with "None." when there are none.
-->

### ADR <NNNN>: <short title>

- Serves: R-<n>
- Decision record: [ADR <NNNN>](../internal/adr/<NNNN-short-title>.md)

**What we decided**: <the decision, in one or two sentences>

**Why**: <the reason, tied to the requirements it serves>

**Other options we considered**:

- <option>: <why it was not chosen>
