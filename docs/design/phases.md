# Phases

keyturn is developed by using it. New-project mode is validated on real applications first (no throwaway sample apps), and existing-repository mode comes after that.

Stop at the end of each phase and report to the human whether the completion criteria are met.

1. **Foundation**: README, LICENSE (MIT), AGENTS.md, directory layout, and the `localize` skill
   - Done when: the first lines of the README explain the concept clearly, and `localize` can translate keyturn's own documents (and those of any existing repository) into the maintainer's language locally without committing anything.
2. **Document templates**: client-facing and internal templates
   - Done when: the templates can be filled in by hand for one evaluation request, and the client-facing ones make it obvious what the client needs to check.
3. **Phase 1 skills and the Claude Code adapter**: spec, design, conventions, implement, qa, security-review, review, deliver, resume, plus the recommended sandbox and permission settings
   - Done when: one small evaluation request runs from request to delivery inside the sandbox, and a run that is stopped in the middle can be finished with `resume` in a new session.
4. **Gate and the first two stack profiles**: gate.sh with one frontend and one backend profile (tests, linters, and the guardrail checks)
   - Done when: a failing test sends work back to the developer, the loop stops at the limit, and a developer change that deletes a test or adds a suppression is rejected.
   - Also: record the first evaluation baseline and make the eval suite runnable with one command.
5. **Security checks in the profiles**: add SAST, dependency scanning, and secret scanning
   - Done when: the vulnerabilities planted in the evaluation requests are caught by the gate.
6. **Validation on a real application**: validate new-project mode end to end on a real (not sample) application, using the first two stack profiles. Which application is used follows the maintainer's local plan (see [Maintainer Notes](maintainer-notes.md)).
   - Done when: the client can accept it using only the client-facing documents, without reading the code.
7. **GitHub integration**: issues, Project board, labels, Actions, PR-based delivery
   - Done when: a task moves from issue to merged PR with the client only approving requirements and doing the final check.
8. **Client portal**: build it with keyturn, on top of the GitHub integration
   - Done when: the client can approve requirements, answer questions, and do acceptance checks from the portal alone.
9. **More profiles**, one at a time
10. **Codex adapter**
    - Done when: the same evaluation requests run on Codex as on Claude Code.
11. **Existing-repository mode**: onboarding, then the first real issue on an existing repository
    - Done when: the delivery report and acceptance guide are good enough for the client to merge without reading the code.
12. Later: security and operations roles; DAST (OWASP ZAP); scheduled unattended runs
