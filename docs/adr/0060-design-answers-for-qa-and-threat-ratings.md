# 0060. The design answers also answer QA's questions, and correct a threat's rating by the maintainer's decision

- Status: accepted
- Date: 2026-11-24
- Supersedes: in [0058](0058-design-answers-during-implement.md), that only the developer's questions are answered, and that an answer never changes a threat (an answer may raise a threat's rating, or give the reason it stands, by the maintainer's decision)

## Context

[ADR 0058](0058-design-answers-during-implement.md) lets `design` answer, in `keyturn/internal/design-answers.md`, a gap that the approved documents leave open. The design itself stays fixed once `implement` starts ([ADR 0031](0031-documents-fixed-once-implement-starts.md)). Only the developer's questions are answered there, and an answer never changes a threat.

The second task of the rehearsal stopped before its second round for two reasons that this leaves out:

1. **QA's gaps.** The design did not say how a page test finds the web client's parts, or how a test moves time forward to the end of a 15-minute block. QA may not read the code to find out, so it rated all 9 criteria `partly tested`. The design leaves both open, so the architect can answer them. Leaving them to the client's acceptance guide, to be checked by hand, is not what QA is for.
2. **Threat ratings.** `security-review` rated seven threats higher than the threat model does, and reported each as a high finding located at the threat. The mitigations were implemented and verified. Only the architect may correct a rating, the threat model is fixed once `implement` starts, and a security finding is never accepted ([ADR 0042](0042-pm-merges-on-machine-checked-conditions.md)). The developer cannot fix such a finding either, so each round would end the same way until the rework limit.

The gate reads nothing from the answers, and accepts `answer` commits that change only them. The workflows of a running task name a keyturn commit that already has this. Changing the gate or the workflows during a task moves the default branch, and the task is then closed and started again ([ADR 0057](0057-documents-redone-before-implement-vouched-by-the-maintainer.md)).

## Options considered

1. **Widen the design answers**: QA asks for the gaps it meets, and, by the maintainer's decision, an answer may raise a threat's rating or give the reason it stands, never lower it. The gate and the workflows stay as they are. The threat model keeps the older rating until the next task's design.
2. **A new role that may change only the "Severity" lines of the threat model**, and only upwards, checked by the gate. The threat model then stays right, but the gate changes, and so does the keyturn commit the workflows name. A task that needs this has to be closed and started again.
3. **Keep stopping for the maintainer**: the client checks QA's gaps by hand, and the task closes on a rating finding. Every later task with such a gap or rating stops the same way.

## Decision

Option 1.

- **QA's questions.** Inside `deliver`, when QA cannot test part of a criterion because the design leaves open how a test reaches the deliverable (how a test finds a part of it, or controls time or data), it writes a line under "Untested areas" of the test report that starts with `Question for the design:`. The line is in QA's own words and says what the design leaves open, never how the code is built. After the round's checks, those lines send the work back, and the round counts toward the rework limit. It counts once, together with any other reason the work goes back. At the start of the next round, before `implement` runs, `deliver` has `design` answer them within ADR 0058's limits. The developer then builds what the answers name, and QA tests through it. A question `design` does not answer stops the task for the maintainer, as a developer's question does.
- **Rating findings.** `security-review` reports a threat it rates higher than the threat model as a high finding titled `T-<n> is rated lower than what it lets someone do`, located at that threat. Such a finding is the architect's, not the developer's. It never sends the work back, it is not given to `implement`, and it stops the task for the maintainer once the round's checks are recorded.
- **Ratings, only by the maintainer's decision.** The maintainer tells `resume` which threats `design` answers. `resume` records it in "History" as `questions for design, by the maintainer's decision: <what>`, and `deliver` then runs `design`, giving it the findings as `security-review` wrote them. For each threat, the answer says one of two things. It either raises the rating to the one the threat calls for, or keeps the rating and gives the reason it stands. It never lowers a rating, and never changes the threat's text, its mitigation, or what is left. This answer does not count as a rework round. When nothing else sends the work back, `security-review` runs again on the same developer head; otherwise, it runs in the next round.
- **Only `security-review` closes a rating finding.** It reads each threat at the higher of the threat model's rating and the newest answer's. It sets a rating finding to `fixed` only after its own check. For a raised rating, it confirms that the threat is checked at that rating. For a reason, it judges for itself whether the reason shows that the threat lets someone do no more than the rating says; if not, the finding stays open. `design` and `deliver` never close a finding: an answer is only an input to the security review, as the design is. A rating raised above low ends an acceptance that was based on the lower one ([ADR 0010](0010-accepting-the-risk-of-a-low-threat.md)). An answer that lowers a rating is not read as one, and it is a high finding.
- **The same mechanism otherwise.** It is the same file and the same `answer` commits, written in the architect's own words, with the same limit of two answer runs in a round. Runs the maintainer decided do not count toward that limit. The maintainer may also have `design` answer one of QA's gaps through the same line in "History", as for a task that stopped before QA could ask.
- **The threat model.** Inside the task, it keeps the older rating, and the answer is read with it. The delivery report lists every answer, a raised rating among them. The next task's `design`, when it changes the design, writes the raised ratings into the threat model.

## Reasons

- A gap QA meets is the same kind of gap the developer meets. The architect, who decides the design, answers it in their own words, and QA no longer leaves part of a criterion to the client's hands.
- Raising a rating, or giving the reason it stands, makes no check weaker. A forged answer can only make the security review stricter, so the known gap of ADR 0058 (the gate reads the `answer` commits from the head) gives the developer nothing here.
- Neither the architect nor the PM closes a security finding. Only the role that raised it does, after its own check, and the merge conditions still read only its report. Writing a reason is therefore never enough to make a high finding go away.
- No change to the gate or the workflows, so a task already running on a workflow from ADR 0058 on can go on after the plugin is updated, without being started again.

## Consequences

- `qa` writes `Question for the design:` lines inside `deliver`. `security-review` names rating findings in a fixed form, reads the answers' ratings, and alone decides whether a reason closes its finding. `design` answers QA's questions and the ratings, and folds raised ratings into the threat model in the next task. `deliver` sends QA's questions to `design` at the start of the next round, and stops for the maintainer on a rating finding. `resume` records the maintainer's decision. `review` does not report a rating answer that raises or keeps a rating.
- `templates/internal/design-answers.md` gets a form for a rating answer, and `templates/internal/test-report.md` the `Question for the design:` line.
- Inside a task, the threat model can show a lower rating than the one the checks used. Whoever reads the threat model alone does not see the raise until the next task's design. The delivery report and the answers say it.
- QA's questions cost a round, which counts toward the rework limit: the developer builds again, and every check runs again. A rating costs only another run of the security review.
- Nothing under `gates/` or `github/workflows/` changes.
