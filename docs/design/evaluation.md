# Evaluation

keyturn is also built by AI, so keyturn itself needs regression testing: a change to a skill, gate, profile, or template must not make results worse.

- Keep evaluation requests in `evals/requests/` and run them end to end after changes.
- Keep a **baseline** of results and compare every run against it. Metrics include: gate pass rate, planted vulnerabilities caught, acceptance criteria met, rework count, tokens, client requests per task, and the readability of client-facing documents (judged by a higher-tier model against the writing rules).
- Run the full suite when skills, gates, profiles, or templates change, and when the model or tool version changes.
- A change that makes any metric clearly worse is not merged until the reason is understood.
- Changes to requirements during a task are part of the evaluation too: include at least one request with a mid-task change.
- Include requirements that commonly lead to vulnerabilities (per-user data isolation, role-based permissions, file uploads).
- Include requests of different sizes, to check that the architect scales the design instead of always choosing the same structure.
- Include at least one request that is not an application.
- Record token usage, time, and rework count per role and per task, to see where the cost goes and to build estimation data for the future.
