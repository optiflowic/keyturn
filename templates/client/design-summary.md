<!--
Template: design summary (client-facing). Filled in by the architect.

- Write for a client who does not read code: no code, no unexplained jargon.
- Write in the client's language, unless the project uses English-only mode.
- Keep every ID (R-n, decision numbers) exactly as it is, in every language.
- Only the main decisions go here. Every one of them has an ADR in internal/adr/; the details stay there.
- A decision's number is the number of its ADR. Call it a "decision" and its ADR a "decision record"; do not use the word "ADR" in the content.
- Delete these comments, and every placeholder in <angle brackets>, when you fill in the template.
-->

# Design summary: <name of what is being built>

Status: <draft | waiting for agreement | agreed>

Based on requirements version <n>.

## Summary

<!--
About three lines: the overall shape of the design, and how many decisions need the client's agreement.
Then one line on who we assumed maintains the app after delivery (your own team, another company, or nobody, from the requirements, or "you did not say"),
how much that counted in the choices, and that the client can tell us otherwise before the work starts, if someone else will maintain it or their team already works with other tools (keyturn's ADR 0073).
When the client has told us, say what they said and on which date: a rerun keeps it.
-->

<summary>

<who we assumed maintains it after delivery, and what that meant for the choices>

## What you need to do

<!--
Only what the client must do or decide now: usually, agreeing to the decisions in the next section.
Leave the list empty, with "Nothing right now.", when no decision needs agreement.
-->

> [!IMPORTANT]
> - <for example: read decisions 0002 and 0004 below, and agree to them, or tell us what to change>

## Must agree: decisions that need your agreement

<!--
One heading per decision that affects the client (cost, scope, or how the client works), and per decision that always needs the client's approval,
even when it changes none of those: a new dependency (other than a development tool approved by the stack profile, listed at the end), a new external service, a change to authentication, authorization, or data handling, or anything that deletes data.
Also one per decision the client asked to be consulted on, whatever its kind (keyturn's ADR 0074): give the recommendation and the reasons, and, when we do not take what the client named or suggested, say so and why.
When the client asked for the recommendation in a card's answer, say in "What we decided" that this is the recommendation they asked for on that card.
- Use the number and title of the decision's ADR. Link to the ADR as the decision record: from keyturn/client/, the path is ../internal/adr/<NNNN-short-title>.md.
- "Serves" lists the requirements the decision exists for. Every decision serves at least one requirement.
- Give the realistic options only, in a sentence each, with why each was not chosen.
- "For whoever maintains it" is only for a decision whose decision record has a "Maintainability after delivery" section (keyturn's ADR 0075); delete it otherwise.
  First line: how much this counted against how well each option fits (as much, more, or less), and why (who maintains the app, as "Summary" says).
  Then one line for what we chose and one for each option compared there (not one ruled out because it does not fit), in plain words: how widely it is used,
  whether the current documentation of what the app is built with still recommends it, and how easy it is to find people who know it;
  how good its documentation is and how often its updates break things only when that decided the choice. Last line: the date we checked, or that we could not check, and why.
- "What it means for you" is the part the client agrees to. Say it concretely: money, time, what is or is not included, what they have to do.
  When the decision chose an option that is less known than another one we considered (its decision record says "Less known choice: yes"), including code we write ourselves
  instead of a widely used component, say so here, and why: the client's people maintain it after delivery. This applies under "For information" too.
- When the client answers, set "Agreement" to agreed, or to not agreed with what they want changed.
- "If you do not answer" says which work waits until the client agrees. Nothing that depends on the decision starts before agreement; never use an option the client has not agreed to.
- When a new ADR supersedes one listed here, replace the entry with the new ADR and set "Agreement" back to waiting.
-->

### Decision <NNNN>: <short title>

- Agreement: <waiting | agreed | not agreed: what the client wants changed>
- Serves: R-<n>
- Decision record (the full details): <link to the ADR, with the text "decision record <NNNN>">

**What we decided**: <the decision, in one or two sentences>

**Why**: <the reason, tied to the requirements it serves>

**Other options we considered**:

- <option>: <why it was not chosen>

**For whoever maintains it**: <how much this counted against fit, and why>

- <what we chose>: <how widely used, whether still recommended, how easy to find people who know it>
- <option compared>: <the same>
- <checked on <date> | not checked: why>

**What it means for you**: <cost, scope, or how you work>

**If you do not answer**: <which work waits until you agree>

## For information: other main decisions

<!--
Decisions the client should know about but does not need to agree to. They are listed for information only.
Use the same fields as above, "For whoever maintains it" included, without "Agreement" and "If you do not answer". Leave "What it means for you" out when it means nothing for the client, never when the decision is a less known choice.
Leave the section with "None." when there are none.
-->

### Decision <NNNN>: <short title>

- Serves: R-<n>
- Decision record (the full details): <link to the ADR, with the text "decision record <NNNN>">

**What we decided**: <the decision, in one or two sentences>

**Why**: <the reason, tied to the requirements it serves>

**Other options we considered**:

- <option>: <why it was not chosen>

**For whoever maintains it**: <how much this counted against fit, and why>

- <what we chose>: <how widely used, whether still recommended, how easy to find people who know it>
- <option compared>: <the same>
- <checked on <date> | not checked: why>

## For information: development tools approved by the stack profile

<!--
The development tools the work adds that the stack profile names: tools that only check, format, or test the code and are not part of what is delivered.
The stack profile approves them, so the client does not need to agree to them; they are listed for information only. Each one was still checked like any other dependency.
Any other tool, and any tool added while no stack profile exists, needs the client's agreement and goes under "Must agree" instead.
- One line per tool: what it does, in plain words.
- Give the result of the check in plain words, for each tool, or once for all of them when it is the same.
Leave the section with "None." when there are none.
-->

<result of the check, when it is the same for every tool>

- <tool>: <what it does, in plain words>. <result of the check, when it differs from the others>
