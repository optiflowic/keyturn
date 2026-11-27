# 0070. The client gets a test report with evidence for every criterion, the acceptance guide asks only for what QA could not check, and a delivery is limited by its number of acceptance criteria

- Status: accepted
- Date: 2026-11-27
- Supersedes: in [0033](0033-delivery-documents-from-the-records.md), what `deliver`'s last step writes and may commit (also the client's test report), and what it does with more than about five "Must check" items; in [0046](0046-acceptance-record-conditions-check-and-merge-script.md), the documents the acceptance row covers (also the client's test report); in [0069](0069-qa-checks-the-screens-end-to-end-in-a-browser.md), "What the client gets": the screenshots are shown in the client's test report, not in the acceptance guide, and the client writes no result for them

## Context

The acceptance guide has "Must check" steps: the client runs, step by step, a check for every acceptance criterion of a Must requirement, and writes a result for each. In the acceptance of the MVP rehearsal, this asked the client to do the checks the team building the software should run itself. In contract development, the vendor tests the deliverable, operating its screens included, and hands over a test report with it; the client reads the report, tries what they care about, and accepts. keyturn's QA already tests every criterion, but its report is internal (English, test names, files), and its web tests, run in a simulated browser, do not operate the pages as a person does, so the guide sent the client to check them by hand.

[ADR 0069](0069-qa-checks-the-screens-end-to-end-in-a-browser.md) fixed the way of working for the look's criteria: QA operates the deliverable's screens in a real browser, with the E2E tool the stack profile or the design names, and keeps screenshots in `keyturn/client/evidence/<task>/` as the client's evidence. It said that #200 applies the same to every criterion checked by operating the screens, and that the screenshots go where this decision puts them.

What constrains the answer:

- The client's attention is limited ("Client attention budget" in [Documents](../design/documents.md)), and the rule that kept a delivery small was "about five Must check items". Without "Must check", something else has to limit the size of a delivery, and it must be known when the requirements are written, where a delivery is split.
- The delivery documents are written from the committed records, in a context of their own ([ADR 0033](0033-delivery-documents-from-the-records.md)), and what the client accepts is recorded by hash, with the translation they read kept ([ADR 0046](0046-acceptance-record-conditions-check-and-merge-script.md)). A new document the client reads before accepting must be covered the same way.
- keyturn fixes the way of working, not the tools: the tools are the stack profile's, or the design's.
- QA never reads the implementation, and only QA runs the end-to-end tests; the gate does not ([ADR 0069](0069-qa-checks-the-screens-end-to-end-in-a-browser.md)).

## Options considered

Where QA's results reach the client:

1. **Keep the acceptance guide's "Must check" steps.** Nothing new, but the client keeps doing the builder's checks, and nothing shows what was checked or how.
2. **Put QA's results into the delivery report.** One document fewer, but the delivery report is already long (what was delivered, verified, not verified, risks, guardrails, tools), and a section per criterion with screenshots would bury it.
3. **A client-facing test report of its own, `keyturn/client/test-report.md`, written at the last step from QA's report and the gate's log.** Per criterion: how it was checked, in steps the client can read; the result; and the evidence (QA's screenshots, and what was observed where a screen does not show it). The acceptance guide points to it and asks only for what QA could not check.

What limits the size of a delivery:

1. **The number of requirements.** Known when the requirements are written, but a requirement can have one criterion or six; it does not measure what the client reads.
2. **The number of acceptance criteria.** Known when the requirements are written; each criterion is one entry the client reads in the test report, with its evidence, and one thing the developer builds and QA tests.
3. **The checks asked of the client.** Only known after QA ran, too late to split the delivery, and small when QA can test everything, however big the delivery.
4. **An estimate of the client's reading time.** Closest to the attention budget, but nobody can check an estimate.

## Decision

Option 3 for the results, and option 2 for the size.

**QA checks every criterion, operating the screens included.** The way of working of ADR 0069 applies to every acceptance criterion whose "When" is something a person does on the deliverable's screens: QA operates the pages end to end in a real browser, through the running deliverable, with the E2E tool the design lists, as a person does, and checks the whole expected result there. Tests through another interface (for example, HTTP, with a clock a design answer gives) still check what the screens cannot show quickly or at all, such as a block that ends after 15 minutes. Each such browser test takes a screenshot of what the criterion's expected result says a person sees, at the design's desktop width, and QA commits it with the look's screenshots in `keyturn/client/evidence/<task>/`, named after the criterion. For each criterion it tested, QA's internal report says how it was checked, as steps a person can follow (never the test's code), what was observed (the text a page showed, what the server answered, where no screen shows it), and which screenshots show it. A criterion that needs a screen QA could not operate (no E2E tool, no browser) is `partly tested` or `not tested`, never `pass` from another interface alone. Nothing else is committed as evidence: what was observed is written in the report, and the gate still allows a `qa` commit only images in its task's folder.

**The client's test report.** `deliver`'s last step writes `keyturn/client/test-report.md` with the acceptance guide and the delivery report, in the same context of their own, from the same records (QA's internal test report, the screenshots it names, and the gate's log), in the client's language. It says who tested and how (an independent tester who did not see the code, the version tested, the browser), then, per requirement and criterion, how it was checked, the result, and the evidence, with the screenshots as images, and the look's screenshots by page; then what was not checked, with why, and where the client is asked to check it, or what they can do when it needs what comes after the delivery (their own server, for example). It reports only what the records show. The client writes nothing in it.

**The acceptance guide.** No "Must check" or "Optional" checks of what QA checked. The guide points to the test report, says how to open the deliverable and what the client may want to try on their own (the main screens and how to reach them, free and optional, with nothing to record), and asks whether they accept. It has checks only for the criteria the test report marks `not checked` or `partly checked`, when the client can check them before accepting: one check per criterion (or per criteria the same steps check), with why QA could not check it, the requirement's priority, steps, the expected result, and a line for the client's result. A Nice to have one may be skipped. When none is left, the guide says so.

**The acceptance row.** The client accepts the three documents: the acceptance guide, the test report, and the delivery report. The row's fixed first cell becomes `acceptance-guide.md, test-report.md, delivery-report.md`, and the row has the SHA-256 of each of the three and of each translation the client read, in that order. `approval.py` keeps the three translations, and the conditions check compares the three hashes at the head. `deliver` may commit `keyturn/client/test-report.md` with the other two, and its documents commit is the newest commit that changes any of the three.

**The size of a delivery.** A delivery covers about ten acceptance criteria at most, removed ones not counted. When the requirements need more, the work is split into deliveries when the requirements are written, never by lowering a requirement's priority or merging criteria. At the last step, a delivery that is bigger anyway is reported, as ADR 0033 reports too many checks: the documents cover every criterion, and the delivery report and the report to the maintainer say that the delivery is bigger than one should be, so that the next request is split. The checks asked of the client have no count of their own: each is something nobody else could check, and the delivery report lists every one under "What was not verified".

## Reasons

- The team that builds the deliverable tests it, and the client judges from evidence: the steps in plain words, the result, and the screenshot of what a person sees. The client no longer repeats checks that QA ran, and can still try anything they want.
- A document of its own keeps the delivery report short, and lets the test report be read on its own, as a vendor's test report is. Writing it in the last step's context, from QA's report and the gate's log, keeps it to what the records show, as the other two documents are ([ADR 0033](0033-delivery-documents-from-the-records.md)), and lets it change round by round with QA's report.
- Covering it with the acceptance row, as the other two are, keeps what the client accepted provable: a test report changed after sending makes the acceptance stale, and the translation they read is kept.
- The number of acceptance criteria is what the client reads, what the developer builds, and what QA tests, and it is known when the requirements are written, where splitting belongs. About ten keeps the test report to a reading of about half an hour with its screenshots; the worked example's first delivery has ten.
- Writing what was observed into the report, instead of committing output files, keeps the evidence folder to images, which the gate already checks, and keeps the report readable.

## Consequences

- `templates/client/test-report.md` is new; `templates/client/acceptance-guide.md` has no "Must check" or "Optional" sections, and checks only what QA could not; the screens move from it to the test report. `templates/client/delivery-report.md`, `templates/client/requirements.md`, and `templates/client/approvals.md` follow; `templates/internal/test-report.md` has a "Checks" section with the steps, what was observed, and the screenshots of each criterion tested.
- `skills/qa/SKILL.md` operates the screens for every criterion done on them, takes a screenshot of each expected result, and fills in "Checks".
- `skills/deliver/SKILL.md` writes and commits the test report with the other two documents, and tells the person how many checks the guide asks of the client and whether the delivery has more than about ten criteria. `skills/spec/SKILL.md` translates, checks, and sends the three documents, and asks the client to read the test report and do only the checks the guide asks.
- `skills/spec/scripts/approval.py` and `gates/conditions.py` read the acceptance row with three documents; `gates/gate.py` lets a `deliver` commit change `keyturn/client/test-report.md`; `github/scripts/task_branch.py` links the test report in the pull request's description. An acceptance row written before this change, with two documents, is not read as a row of the task: it is sent again.
- "Client attention budget" in [Documents](../design/documents.md) limits a delivery by its acceptance criteria instead of its "Must check" items, and "Who checks what" in [Roles](../design/roles.md) has QA operate the screens for every criterion done on them.
- The worked example has the client's test report, with screenshots of what each criterion's expected result shows; its acceptance guide asks no check, since QA checked every criterion of delivery 1.
- Not checked: that the steps in the test report are what the tests do (QA writes both, and nobody else reads the tests); and the size of a delivery before the requirements are approved, which nothing counts mechanically.
