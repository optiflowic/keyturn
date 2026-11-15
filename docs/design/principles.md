# Design Principles

1. **The client reviews specifications and evidence, not code**
   Review shifts from code to requirements, acceptance criteria, and reports.
2. **Always choose the best practice, and show why**
   For every meaningful decision (architecture, libraries, data model, security approach), consider the alternatives, pick the one that best fits the requirements and the scale of the project, and record the reasoning. "Best" depends on context: a small tool and a multi-tenant service need different designs. Over-engineering is as much a failure as under-engineering.
3. **Readable code is mandatory**
   All code follows the ideas of *The Art of Readable Code*: clear names, simple control flow, small focused functions, and comments that explain why. No unused abstractions or speculative extension points. This applies to keyturn itself and to everything it builds.
4. **Roles hand off work through documents**
   Not through conversation context. Each handoff uses a defined template, which keeps work traceable and limits what each agent needs to read.
5. **The developer and the judges run in separate contexts**
   QA and security run in separate contexts (subagents or separate processes) and never see the developer's reasoning. QA writes tests from the specification only.
6. **Ship/no-ship decisions are mechanical**
   Tests, static analysis, dependency scanning, and secret scanning act as gates. LLMs read the results and fix problems; they do not decide whether something passes.
7. **Rework loops have a limit**
   When the limit is reached, stop and report to the client what could not be resolved. This also keeps costs under control.
8. **Every stack has an explicit definition of "verified"**
   Stacks are supported through stack profiles (see [Stack Profiles](stack-profiles.md)). Work on a stack without a profile is still possible, but the delivery report must state that gate coverage is limited.
9. **No lock-in to a single AI tool**
   keyturn is meant to work with any AI coding agent. The shared parts follow open conventions (Agent Skills, `AGENTS.md`), and each tool gets a thin adapter. Claude Code and Codex are the first adapters; others can be added the same way.
10. **Autonomy never bypasses the gates**
    Agents may run unattended, but they cannot merge or release anything that has not passed the gates.
11. **Agents cannot change the rules they are judged by**
    The developer cannot weaken gates, conventions, or tests to make its own work pass. See [Guardrails](guardrails.md).
12. **Work can always be resumed**
    Whatever stops a task (usage limits, a crash, a question to the client, the rework limit), it can be resumed at any time from where it stopped. See [Resuming Work](resuming-work.md).
