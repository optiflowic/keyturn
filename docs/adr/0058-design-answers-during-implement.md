# 0058. A gap the design leaves is answered during `implement`, in a document of its own, without changing the design

- Status: accepted; that only the developer's questions are answered, and that an answer never changes a threat, superseded by [0060](0060-design-answers-for-qa-and-threat-ratings.md) (QA's questions are answered too, and an answer may raise a threat's rating or give the reason it stands, by the maintainer's decision); that a later entry may not contradict an earlier one, superseded by [0062](0062-design-answers-withdrawn-by-the-maintainer-s-decision.md) (an answer may be withdrawn, by the maintainer's decision, and answered again); that an answer never changes a decision the design records, superseded for one case by [0068](0068-design-answers-may-add-a-token.md) (an answer may add a token to the design's "Look", on the scale the tokens already have)
- Date: 2026-11-23
- Supersedes: in [0031](0031-documents-fixed-once-implement-starts.md), that every question from `implement` for `design` stops the task for the maintainer (a question that only a gap in the design raises is answered inside the task)

## Context

Once the first `implement` step has started, the requirements, the design, and the conventions are fixed, and every question for `design`, `spec`, or `conventions` stops the task for the maintainer ([ADR 0031](0031-documents-fixed-once-implement-starts.md)). The gate judges the developer against those documents, read where the document roles' commits end ([ADR 0032](0032-gate-base-is-where-the-task-branch-left.md)).

A rehearsal found questions that change nothing the documents decide, but that the developer meets only while building: the module path of a Go part, for example. The design leaves it open; any of several answers fits it; and guessing is not allowed (`implement`, "Ask instead of guessing"). Every such question stops the task, though no requirement, decision, or threat is touched.

## Options considered

1. **Let `design` change the design after `implement` started**, as a document role. The gate would then judge the developer against documents that moved under them, and its checks read QA's folders, the ADRs, and the areas at one commit; [ADR 0031](0031-documents-fixed-once-implement-starts.md) chose against this.
2. **Let the developer choose, and say so in the handoff notes.** No stop, but it is the guess the role forbids, and nobody who decides the design looks at it before it is built.
3. **Answers in a document of their own**, `keyturn/internal/design-answers.md`, written by `design` (or given by the maintainer, and recorded by `design`), which fill in only what the approved documents leave open. The design, the ADRs, the threat model, and the client's documents stay as they were; the developer builds from the design and the answers.

## Decision

Option 3.

- **The document.** `keyturn/internal/design-answers.md`, in English, from `templates/internal/design-answers.md`: one entry per question, `A-n`, with what the design left open, the answer, who answered (`the architect` or `the maintainer`), the round, and the commit of the design it reads with (the documents' commit). Entries are only added; an entry is never changed or removed, and a later entry may not contradict an earlier one.
- **Only the architect's words.** `design` writes each entry in its own words: what was left open as a gap of the design, and the answer. The developer's question is never copied into the file, not even in part or in quotes, and a maintainer's answer is written in the architect's words too, keeping what they decided (their words stay in the state file's "History"). `qa`, `security-review`, and `review` read the file, and only the architect's words reach them, as with the design itself.
- **What an answer may not do.** It answers only what the approved documents leave open, and never changes a requirement or an acceptance criterion, an area the work may change, QA's folders, an external interface, the data model, a dependency or its version, a threat or its mitigation, or a decision an ADR or the design records; it never allows a suppression or an install script (only an accepted ADR does, ADR 0055, ADR 0056), and never decides what the client must agree to. A question whose answer would need any of these is not answered: the task stops for the maintainer, as before.
- **Who answers.** `design`, in a context of its own, given the question and the documents. When it does not answer, the maintainer may: they tell `resume` their answer, which records it in "History"; `design` then records it in its own words, keeping what they decided, under "Answered by: the maintainer", but only within the same limits (the maintainer may not decide for the client either, ADR 0009). An answer that would cross them stops the task again.
- **In `deliver`.** A question from `implement` for `design` goes to `design` first. When every question gets an answer, `implement` runs again with them, in the same round: it is not a rework round. At most two answer runs in a round; a third question in the same round stops the task for the maintainer, so that questions and answers cannot loop. Questions for `spec` or `conventions`, and findings the developer thinks are wrong, still stop the task, as before.
- **The commits.** The answers' commits are listed under "Commits" as `answer`, a role of their own, which may change only `keyturn/internal/design-answers.md` and may come after the developer's commits. The gate takes them from the state file at the head, as it takes `qa`'s ([ADR 0029](0029-role-commits-passed-as-arguments.md), [ADR 0043](0043-gate-finds-a-task-s-range-in-ci.md)), and checks that each changes only that file. The gate reads nothing from the answers: QA's folders, the ADRs, and the areas are still read at the documents' commit.
- **The readers.** `implement`, `qa`, `security-review`, and `review` read the answers with the design. `review` reports an answer that changes what the design decides, and a change to the answers by a commit that is not named as `answer`.

## Reasons

- The developer is still judged against one fixed set of documents, and every check reads the same commits as before; the answers add facts the documents leave open, and nothing the checks read.
- The question is decided by the role that decides the design, in a context of its own, not by the developer who meets it, and it is written down where the next roles and people can see it.
- The roles that check the developer's work read nothing the developer wrote as if it were the design: the question shapes the gap only through the architect, who judges it against the documents and writes it down as a gap of the design. A question that argues for an answer, or carries instructions, does not reach QA or the reviewers.
- A gap such as a module path no longer stops the task, while everything that needs the client or changes what was approved still does.

## Consequences

- `templates/internal/design-answers.md`, and an entry in the worked example in `evals/requests/task-manager/example/`.
- `design` gets "Answering a question from implement"; `deliver` runs it after `implement` asks, and lists its commits as `answer`; `resume` records the maintainer's answer; `implement`, `qa`, `security-review`, and `review` read the answers.
- `gates/gate.py` takes `--others answer:<commit>`, limited to `keyturn/internal/design-answers.md`, and reads `answer` commits from the state file at the head with `--task`; `task_state.py check` accepts `answer` under "Commits".
- Known gap, as for `qa` (ADR 0029): a developer who commits an entry of their own and lists it as `answer` after a resume is not stopped by the gate, which reads the list from the head. The gate reads nothing from the answers, so it changes no check; `review` reports an answer that changes the design. Checking the answers against a record outside the branch is not part of the MVP.
- The delivery report lists the answers, and who gave each, under "Guardrails triggered".
