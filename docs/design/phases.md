# Phases

keyturn is developed by using it. New-project mode is validated on real applications first (no throwaway sample apps), and existing-repository mode comes after that.

Stop at the end of each phase and report to the human whether the completion criteria are met.

## MVP

A minimum viable keyturn is built first, before the numbered phases are finished ([ADR 0025](../adr/0025-mvp-first.md)). It takes a request from requirements through design, implementation, tests, security review, code review, and a delivery report, on a real application, and the client decides from the requirements, the acceptance guide, and the delivery report. It takes these parts of the phases below:

- From phase 3: `deliver`, the Claude Code adapter's subagent definitions, and minimal permission settings that block direct pushes to the default branch and destructive commands. Not the sandbox or the translation subagent.
- From phase 4: a minimal gate and minimal `go` and `react-spa` profiles: build, tests, lint, no drop in the number of tests, protected paths, and new suppression comments. Not skipped tests, coverage, the evaluation baseline, or the eval suite.
- From phase 6: one run from request to delivery on a real application, including a stopped run finished with `resume`.
- From phase 7: delivery through a pull request on GitHub. Agents push the task branch and open the pull request, the review roles' findings are posted on it ([ADR 0045](../adr/0045-deliver-posts-the-review-reports-on-the-pull-request.md)), the gate runs in CI, and the PM merges when the gate passes, no high or medium finding is open, and the client's acceptance is recorded, with a workflow that detects, on any plan, a commit on the default branch that did not come from a task's pull request merged with those checks passing (it checks the records, not that the client really accepted), and branch protection requiring the same checks where the plan has it ([ADR 0041](../adr/0041-agents-push-task-branches-and-open-pull-requests.md), [ADR 0042](../adr/0042-pm-merges-on-machine-checked-conditions.md), [ADR 0048](../adr/0048-default-branch-guarded-in-three-layers.md)). Not issues, the Project board, labels, or a separate identity for agents. Other Git hosts are not in the MVP.

What the MVP runs without (the sandbox and the profiles' security checks) is listed in each delivery report under "What was not verified" ([Guardrails](guardrails.md) 4, [Stack Profiles](stack-profiles.md)).

- Done when: a real application runs from request to a merged pull request with `deliver`, a stopped run is finished with `resume` in a new session, and the client can decide from the client-facing documents without reading the code.

Everything else in the phases below is an enhancement after the MVP. The phases keep their numbers and order for it.

## Numbered phases

1. **Foundation**: README, LICENSE (MIT), AGENTS.md, directory layout, and the `localize` skill
   - Done when: the first lines of the README explain the concept clearly, and `localize` can translate keyturn's own documents (and those of any existing repository) into the maintainer's language locally without committing anything.
2. **Document templates**: client-facing and internal templates
   - Done when: the templates can be filled in by hand for one evaluation request, and the client-facing ones make it obvious what the client needs to check.
3. **Phase 1 skills and the Claude Code adapter**: spec, design, conventions, implement, qa, security-review, review, deliver, resume, plus the recommended sandbox and permission settings
   - Done when: one request runs from request to delivery, and a run that is stopped in the middle can be finished with `resume` in a new session. The MVP covers this on a real application; the sandbox and the translation subagent are enhancements after it.
4. **Gate and the first two stack profiles**: gate.sh with one frontend and one backend profile (tests, linters, and the guardrail checks)
   - Done when: a failing test sends work back to the developer, the loop stops at the limit, and a developer change that deletes a test or adds a suppression is rejected.
   - Also: record the first evaluation baseline and make the eval suite runnable with one command.
   - In the MVP: the gate, the two profiles, and the protected-path, test-count, and suppression checks. Skipped tests, coverage, the baseline, and the eval suite are enhancements after it.
5. **Security checks in the profiles**: add SAST, dependency scanning, and secret scanning
   - Done when: the vulnerabilities planted in the evaluation requests are caught by the gate.
6. **Validation on a real application**: validate new-project mode end to end on a real (not sample) application, using the first two stack profiles. Which application is used follows the maintainer's local plan (see [Maintainer Notes](maintainer-notes.md)).
   - Done when: the client can accept it using only the client-facing documents, without reading the code.
   - In the MVP: the first run, with the MVP gate and profiles and without the sandbox or the security checks of phase 5.
7. **GitHub integration**: issues, Project board, labels, Actions, PR-based delivery
   - Done when: a task moves from issue to merged PR with the client only approving requirements and doing the final check.
   - In the MVP: pushing the task branch, the pull request, the reviews on it, the gate in CI, and the PM's merge on machine-checked conditions. Issues, the Project board, labels, and a GitHub App for agents (so that the client's approval of the pull request can be a required review) are enhancements after it.
8. **Client portal**: build it with keyturn, on top of the GitHub integration
   - Done when: the client can approve requirements, answer questions, and do acceptance checks from the portal alone.
9. **More profiles**, one at a time
10. **Codex adapter**
    - Done when: the same evaluation requests run on Codex as on Claude Code.
11. **Existing-repository mode**: onboarding, then the first real issue on an existing repository
    - Done when: the delivery report and acceptance guide are good enough for the client to accept without reading the code.
12. Later: security and operations roles; DAST (OWASP ZAP); scheduled unattended runs
