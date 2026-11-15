# Future Vision (not in scope yet)

These are enhancements for later. They are written down so that current decisions do not block them, not to be built now.

- **Fully autonomous operation**: keyturn works on its own, and the client only reviews what has piled up (approvals, questions, acceptance checks), for example once every morning in the client portal.
- **Deadline-driven planning**: the client says what they want and by when. keyturn interviews the client for the information it needs, breaks the work into tasks, builds a schedule, and runs the work automatically based on the schedule and the available usage (rate limits, budget), so that deliverables are ready on time.

What to do now to keep this possible:

- Keep all task state on GitHub and in repository documents, never only in a session.
- Record actual results for every task (tokens, wall-clock time, rework count, number of client questions). Future scheduling needs this data to estimate realistically.
- Keep the escalation rules strict. Autonomy is only safe if agents reliably stop and ask.
