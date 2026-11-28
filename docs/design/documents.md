# Documents

All specifications, designs, and reports are Markdown documents. There are two tiers with different goals.

## Client-facing documents

The client reads these to make decisions and to do the final check. They must be easy to read and make it obvious where to look.

| Document | Purpose |
|---|---|
| requirements.md | What will be built and how it will be judged. Each requirement has a priority, Must or Nice to have: the PM proposes it, and the client decides it. The client approves this before work starts. |
| design-summary.md | The main design decisions in plain language, with the reason for each, the alternatives considered, and how they compare for whoever maintains the deliverable. |
| test-report.md | How every acceptance criterion was checked, in steps the client can read, the result, and the evidence: the screenshots QA took of the pages, and what it observed where no screen shows it ([ADR 0069](../adr/0069-qa-checks-the-screens-end-to-end-in-a-browser.md), [ADR 0070](../adr/0070-client-test-report-and-acceptance-without-required-checks.md)). |
| acceptance-guide.md | How to open the deliverable and what the client may try on their own, the checks only the client can do (the criteria QA could not check), and the question whether they accept ([ADR 0070](../adr/0070-client-test-report-and-acceptance-without-required-checks.md)). |
| delivery-report.md | What was delivered, what was verified, what was not, and the remaining risks. |
| approvals.md | Which version of the requirements the client approved, in which language, identified by the source hash. |
| decision-card.md | One question to the client: the context, the options, a recommendation, and what happens if the client does not answer. |

Writing rules:

- Start with a short summary (3 lines or so) that states the conclusion.
- Put what the client needs to do or decide first, and mark it clearly.
- Mark priority explicitly (e.g., a requirement's "Must" or "Nice to have", or a check the client may skip).
- No code and no unexplained jargon. Write for someone who will not read the code.
- Keep it short. Move details into internal documents and link to them if needed.

## Client attention budget

If the client is asked too often, or given too much at once, they stop reading and start approving blindly, and the whole model fails. Both the number of requests and the size of each request are limited.

- **Batch requests.** Questions and approvals are collected and sent together, not one by one.
- **Keep each request small.** One request should take a few minutes to read. Each question is a short "decision card": the context, the options, a recommendation, and what happens if the client does not answer.
- **Test, then report with evidence.** The team that builds the deliverable checks every acceptance criterion and hands over a test report with evidence; the client reads it and tries what they want. The acceptance guide asks the client to check only what QA could not ([ADR 0070](../adr/0070-client-test-report-and-acceptance-without-required-checks.md)).
- **Limit the size of a delivery.** A delivery covers about ten acceptance criteria at most. If the requirements need more, they are split into deliveries, never by lowering a requirement's priority or merging criteria; `deliver` stops before the design for the maintainer to decide ([ADR 0070](../adr/0070-client-test-report-and-acceptance-without-required-checks.md)).
- **Ask only when it matters.** Low-risk changes that stay within approved requirements do not need extra approval. The changes listed in [Guardrails](guardrails.md) always do.
- **No answer is not consent.** An unanswered card is never decided on the client's behalf, not even with its recommendation. Work that depends on the answer waits and everything else goes on; if nothing else can be done, the task stops with the card as an open question (see [Resuming Work](resuming-work.md)). See [ADR 0009](../adr/0009-no-answer-is-not-consent.md). During the MVP, the `implement` step of a task waits for every answer its design asked for, since the task's documents are fixed once it starts ([ADR 0031](../adr/0031-documents-fixed-once-implement-starts.md)).
- Track how many requests the client receives and how long they wait, as part of the cost data.

## Internal documents

Agents use these to hand off work. They can be as detailed as needed.

- Design document and threat model
- Design answers: what the design left open, answered for the developer or QA after the developer's work started, without changing the design, threat ratings raised or explained by the maintainer's decision, and earlier answers withdrawn by the maintainer's decision, with a new entry that keeps every earlier one ([ADR 0058](../adr/0058-design-answers-during-implement.md), [ADR 0060](../adr/0060-design-answers-for-qa-and-threat-ratings.md), [ADR 0062](../adr/0062-design-answers-withdrawn-by-the-maintainer-s-decision.md))
- Architecture decision records (see below)
- Onboarding notes (existing repositories)
- Handoff notes between roles
- Detailed test report (results per acceptance criterion, untested areas)
- Review findings
- Gate logs (raw tool output and summaries)

## Where documents live in a project

Separate the two tiers so the client knows which folder is theirs.

```
keyturn/
  config.json # project configuration (language settings, and the stack profile of each part)
  client/     # client-facing documents
    evidence/ # the screenshots QA takes of the pages, one folder per task, shown in the test report (ADR 0069, ADR 0070)
  internal/   # agent-to-agent documents
    adr/      # architecture decision records
    state/    # one state file per task (see Resuming Work)
```

When GitHub integration is used, client-facing content also appears in issues and pull requests (see [GitHub Integration](github-integration.md)). The files in the repository remain the source of truth. In a multi-repository project, the project-wide documents live in the home repository (see [Repository Structure](repository-structure.md)).

## Architecture decision records

Every meaningful decision is recorded as an ADR, so that the same question is not discussed again and again.

- One decision per file: `adr/NNNN-short-title.md`, with the context, the options considered, the decision, the reasons, and the consequences.
- Each ADR has a status: proposed, accepted, or superseded.
- **Check before deciding.** Before making a decision, every role searches the existing ADRs. If an accepted ADR already covers the question, follow it instead of reconsidering.
- **Change by superseding.** An accepted decision is changed only by a new ADR that explains what changed and links to the one it replaces. ADRs are never edited after acceptance, except to mark them superseded.
- ADRs that need the client's agreement (e.g., a choice that affects cost, scope, or how the client works) are summarized in plain language in `design-summary.md`.
- The reviewer flags changes that contradict an accepted ADR.
- keyturn's own development follows the same rule: its decisions are recorded as ADRs in `docs/adr/`.
