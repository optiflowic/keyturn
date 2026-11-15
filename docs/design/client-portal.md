# Client Portal (planned)

A GUI for the client side of keyturn. keyturn produces many documents, so the client needs one place to see and act on them across repositories:

- Requirements waiting for approval, and approving them
- Answering questions from agents
- Acceptance guides as checklists, recording the result of each check
- Delivery reports and task progress
- Cost per task and per role (token usage, rework count)

The portal is not a second source of truth. Documents stay in the repositories and tasks stay on GitHub; the portal reads and writes through GitHub (e.g., approval applies a label, an answer posts a comment). It is built with keyturn itself, after the GitHub integration.
